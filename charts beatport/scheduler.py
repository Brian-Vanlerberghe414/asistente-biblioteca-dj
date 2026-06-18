"""
scheduler.py
------------
Runs the Beatport Top 100 scraper once on startup,
then repeats every 24 hours at the configured time.

Usage:
    python scheduler.py

To run in the background (Linux/macOS):
    nohup python scheduler.py &> scheduler.log &

To run as a Windows service or Task Scheduler job, point the trigger
at `beatport_scraper.py` directly instead of using this file.
"""

import asyncio
import logging
import time

import schedule

from beatport_scraper import main as run_scraper

# ---------------------------------------------------------------------------
# Config — change this to whatever time suits your app
# ---------------------------------------------------------------------------
DAILY_RUN_AT = "03:00"   # 24-hour format, server local time

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------
def job():
    log.info("▶  Starting scheduled Beatport scrape …")
    try:
        asyncio.run(run_scraper())
        log.info("✓  Scrape completed successfully")
    except Exception as exc:
        log.error(f"✗  Scrape failed: {exc}", exc_info=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    log.info(f"Scheduler started — running now, then daily at {DAILY_RUN_AT}")

    # Run once immediately so the charts are available right away
    job()

    # Schedule daily repeat
    schedule.every().day.at(DAILY_RUN_AT).do(job)

    while True:
        schedule.run_pending()
        time.sleep(60)   # check every minute
