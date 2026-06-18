"""
beatport_scraper.py
-------------------
Scrapes the Beatport Global Top 100 AND the Top 100 for every genre/sub-genre.

Output layout:
  charts/
    top100_latest.json
    top100_YYYY-MM-DD.json
    genres/
      techno_latest.json
      house_latest.json
      ...
    genres_latest.json   <- index of all genres scraped
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BEATPORT_BASE = "https://www.beatport.com"
BEATPORT_GLOBAL_TOP100 = f"{BEATPORT_BASE}/top-100"
BEATPORT_CHARTS_PAGE = f"{BEATPORT_BASE}/charts"
OUTPUT_DIR = Path("charts")
GENRES_DIR = OUTPUT_DIR / "genres"
REQUEST_DELAY = 2.0  # seconds between requests
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

GENRE_URL_RE = re.compile(r"^/genre/([^/]+)/(\d+)")


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
def parse_tracks(results: list) -> list[dict]:
    tracks = []
    for i, track in enumerate(results, start=1):
        try:
            release = track.get("release") or {}
            tracks.append({
                "position": i,
                "id": track.get("id"),
                "name": track.get("name"),
                "mix_name": track.get("mix_name"),
                "artists": [a["name"] for a in track.get("artists", [])],
                "remixers": [r["name"] for r in track.get("remixers", [])],
                "release": release.get("name"),
                "label": (release.get("label") or {}).get("name"),
                "genre": (track.get("genre") or {}).get("name"),
                "bpm": track.get("bpm"),
                "key": (track.get("key") or {}).get("name"),
                "duration_ms": track.get("length_ms"),
                "publish_date": track.get("publish_date"),
                "image_url": (release.get("image") or {}).get("uri"),
            })
        except Exception as exc:
            log.warning(f"Skipping track at position {i}: {exc}")
    return tracks


def _results_from_next_data(next_data: dict) -> list:
    queries = (
        next_data
        .get("props", {})
        .get("pageProps", {})
        .get("dehydratedState", {})
        .get("queries", [])
    )
    for query in queries:
        results = query.get("state", {}).get("data", {}).get("results", [])
        if results:
            return results
    return []


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def save_chart(tracks: list, stem: str, subdir: Path = OUTPUT_DIR) -> Path:
    subdir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    payload = {
        "fetched_at": datetime.now().isoformat(),
        "count": len(tracks),
        "tracks": tracks,
    }
    serialized = json.dumps(payload, indent=2, ensure_ascii=False)
    for path in (subdir / f"{stem}_{today}.json", subdir / f"{stem}_latest.json"):
        path.write_text(serialized, encoding="utf-8")
    log.info(f"  Saved {len(tracks)} tracks -> {subdir}/{stem}_latest.json")
    return subdir / f"{stem}_latest.json"


# ---------------------------------------------------------------------------
# Core scrape (single page)
# ---------------------------------------------------------------------------
async def _scrape_top100_page(page, url: str) -> list:
    """
    Load url and return raw results list.
    Tries API intercept first, then __NEXT_DATA__ fallback.
    """
    api_results: list = []

    async def on_response(response):
        if api_results:
            return
        if "api-internal.beatportprod.com" in response.url and "top-100" in response.url:
            try:
                data = await response.json()
                items = data.get("results", [])
                if items:
                    api_results.extend(items)
            except Exception:
                pass

    page.on("response", on_response)
    try:
        await page.goto(url, wait_until="networkidle", timeout=30_000)
    except PlaywrightTimeout:
        log.warning(f"Timeout on {url}, waiting extra 5s")
        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(5_000)
    page.remove_listener("response", on_response)

    if api_results:
        return api_results

    # Fallback: __NEXT_DATA__
    try:
        js = "() => { const el = document.getElementById('__NEXT_DATA__'); return el ? JSON.parse(el.textContent) : null; }"
        next_data = await page.evaluate(js)
        if next_data:
            results = _results_from_next_data(next_data)
            if results:
                return results
    except Exception as exc:
        log.warning(f"__NEXT_DATA__ failed for {url}: {exc}")

    return []


# ---------------------------------------------------------------------------
# Genre discovery
# ---------------------------------------------------------------------------
async def discover_genres(page) -> list[dict]:
    """Collect all genre/sub-genre top-100 URLs from the Beatport charts page."""
    log.info(f"Discovering genres from {BEATPORT_CHARTS_PAGE} ...")
    try:
        await page.goto(BEATPORT_CHARTS_PAGE, wait_until="networkidle", timeout=30_000)
    except PlaywrightTimeout:
        await page.goto(BEATPORT_CHARTS_PAGE, wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(5_000)

    anchors = await page.query_selector_all("a[href]")
    seen: set = set()
    genres: list = []

    for anchor in anchors:
        href = await anchor.get_attribute("href") or ""
        m = GENRE_URL_RE.match(href)
        if not m:
            continue
        slug, genre_id = m.group(1), m.group(2)
        key = f"{slug}/{genre_id}"
        if key in seen:
            continue
        seen.add(key)
        name_raw = (await anchor.inner_text()).strip()
        name = name_raw if name_raw else slug.replace("-", " ").title()
        genres.append({
            "name": name,
            "slug": slug,
            "id": genre_id,
            "url": f"{BEATPORT_BASE}/genre/{slug}/{genre_id}/top-100",
        })

    log.info(f"Found {len(genres)} genres/sub-genres")
    return genres


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main():
    log.info("=== Beatport Top 100 Scraper (global + all genres) ===")
    genre_index: list = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT, locale="en-US")
        page = await context.new_page()

        # Global Top 100
        log.info("Scraping global Top 100 ...")
        global_results = await _scrape_top100_page(page, BEATPORT_GLOBAL_TOP100)
        if not global_results:
            raise RuntimeError(
                "Global Top 100 extraction failed. "
                "Beatport may have updated its structure."
            )
        global_tracks = parse_tracks(global_results)
        save_chart(global_tracks, "top100", OUTPUT_DIR)

        # Discover genres
        genres = await discover_genres(page)

        # Top 100 per genre
        for genre in genres:
            await asyncio.sleep(REQUEST_DELAY)
            log.info(f"Scraping [{genre['name']}] {genre['url']}")
            results = await _scrape_top100_page(page, genre["url"])
            if not results:
                log.warning(f"  No tracks for [{genre['name']}] — skipping")
                continue
            tracks = parse_tracks(results)
            stem = re.sub(r"[^\w-]", "_", genre["slug"])
            save_chart(tracks, stem, GENRES_DIR)
            genre_index.append({
                "name": genre["name"],
                "slug": genre["slug"],
                "id": genre["id"],
                "url": genre["url"],
                "track_count": len(tracks),
                "file": f"genres/{stem}_latest.json",
            })

        await browser.close()

    # Write genre index
    if genre_index:
        OUTPUT_DIR.mkdir(exist_ok=True)
        index_payload = {
            "fetched_at": datetime.now().isoformat(),
            "genre_count": len(genre_index),
            "genres": genre_index,
        }
        (OUTPUT_DIR / "genres_latest.json").write_text(
            json.dumps(index_payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        log.info(f"Genre index -> {OUTPUT_DIR}/genres_latest.json")

    log.info(f"Done - global={len(global_tracks)}, genres={len(genre_index)}")


if __name__ == "__main__":
    asyncio.run(main())
