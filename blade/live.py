"""Optional live layer. Off by default; the caller must opt in.

Sends your location, rounded to ~1 km, to three free, keyless open-data services:
Open-Meteo (weather), OpenStreetMap Nominatim (place name), iNaturalist (recent sightings).
Everything fails soft: with no network you simply get the offline Blade. Results are cached on disk.
"""
import json
import os
import threading
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

URLS = {
    "weather": "https://api.open-meteo.com/v1/forecast",
    "place": "https://nominatim.openstreetmap.org/reverse",
    "species": "https://api.inaturalist.org/v1/observations/species_counts",
}
UA = "Blade/0.1 (open-source touch-grass demo)"
_lock = threading.Lock()
TTL = 12 * 3600
RADIUS_KM = 5

WMO = {0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "freezing fog",
       51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
       71: "light snow", 73: "snow", 75: "heavy snow", 80: "rain showers", 81: "rain showers",
       82: "violent showers", 95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with hail"}
GROUPS = {"Aves": "birds", "Plantae": "plants", "Insecta": "insects", "Fungi": "fungi",
          "Mammalia": "mammals", "Reptilia": "reptiles", "Amphibia": "amphibians", "Arachnida": "spiders"}


def coarse(lat, lon):
    """Round to 2 decimals (~1.1 km). This is all that ever leaves the machine."""
    return round(float(lat), 2), round(float(lon), 2)


def _get(url, params, timeout=6):
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _cache_path():
    home = Path(os.environ.get("BLADE_HOME", Path.home() / ".blade"))
    home.mkdir(parents=True, exist_ok=True)
    return home / "cache.json"


def _read_cache():
    try:
        return json.loads(_cache_path().read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _cached(kind, lat, lon, fetch):
    key = f"{kind}:{lat},{lon}"
    with _lock:
        hit = _read_cache().get(key)
    if hit and time.time() - hit["t"] < TTL:
        return hit["v"]
    try:
        value = fetch()  # network call happens outside the lock so the three lookups stay parallel
    except Exception:  # any network or parse failure: fall back to stale cache, else nothing
        return hit["v"] if hit else None
    with _lock:  # re-read inside the lock so parallel lookups don't overwrite each other's entries
        cache = _read_cache()
        cache[key] = {"t": time.time(), "v": value}
        try:
            _cache_path().write_text(json.dumps(cache))
        except OSError:
            pass
    return value


def weather(lat, lon):
    def fetch():
        d = _get(URLS["weather"], {"latitude": lat, "longitude": lon,
                                   "current": "temperature_2m,weather_code"})["current"]
        return f"{WMO.get(d['weather_code'], 'unsettled')}, {round(d['temperature_2m'])}C"
    return _cached("weather", lat, lon, fetch)


def place_name(lat, lon):
    def fetch():
        a = _get(URLS["place"], {"format": "jsonv2", "lat": lat, "lon": lon, "zoom": 14})["address"]
        for k in ("suburb", "neighbourhood", "village", "town", "city", "county"):
            if a.get(k):
                return a[k]
        raise KeyError("no name")
    return _cached("place", lat, lon, fetch)


def sightings(lat, lon, today=None, per_group=3):
    """Species other people recorded within RADIUS_KM in the last 14 days, grouped. Research-grade only."""
    today = today or date.today()

    def fetch():
        res = _get(URLS["species"], {
            "lat": lat, "lng": lon, "radius": RADIUS_KM, "quality_grade": "research", "per_page": 60,
            "d1": (today - timedelta(days=14)).isoformat(), "d2": today.isoformat(), "locale": "en"})
        out, seen = [], {}
        for r in res.get("results", []):
            t = r.get("taxon", {})
            group = GROUPS.get(t.get("iconic_taxon_name"))
            common = t.get("preferred_common_name")
            if not group or not common or seen.get(group, 0) >= per_group:
                continue
            seen[group] = seen.get(group, 0) + 1
            out.append({"common": common, "sci": t.get("name", ""), "group": group})
        return out
    return _cached("species", lat, lon, fetch) or []


def gather(lat, lon):
    """Fetch all three in parallel. Returns {weather, place, sightings}; missing pieces are None/[]."""
    lat, lon = coarse(lat, lon)
    out = {"weather": None, "place": None, "sightings": []}
    jobs = {"weather": weather, "place": place_name, "sightings": sightings}

    def run(k, fn):
        out[k] = fn(lat, lon) or out[k]

    threads = [threading.Thread(target=run, args=(k, f)) for k, f in jobs.items()]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return out
