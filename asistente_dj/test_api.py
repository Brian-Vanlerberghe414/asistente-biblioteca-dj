"""Diagnóstico de la API de GetSongBPM: muestra la respuesta CRUDA.
Uso:  python test_api.py TU_API_KEY
"""
import sys
import urllib.request
import urllib.parse

if len(sys.argv) < 2:
    print("Uso: python test_api.py TU_API_KEY")
    sys.exit(1)

api_key = sys.argv[1]
# Track muy conocido, seguro está en la base de GetSongBPM
lookup = "song:Strobe artist:deadmau5"
url = "https://api.getsong.co/search/?" + urllib.parse.urlencode(
    {"api_key": api_key, "type": "both", "lookup": lookup, "limit": 1})

print("URL consultada:")
print(" ", url)
print()
try:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        print("HTTP status:", resp.status)
        raw = resp.read().decode("utf-8", "ignore")
    print("RESPUESTA CRUDA:")
    print(raw[:3000] if raw else "(vacía)")
except Exception as e:
    print("ERROR:", repr(e))
    print("\nSi es un error de certificado SSL, avisá y lo resolvemos.")
