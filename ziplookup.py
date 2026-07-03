"""
ziplookup.py
------------
Best-effort ZIP lookup/validation via Zippopotam.us (free, no API key).

Scope (see PROJECT discussion — we do NOT geocode arbitrary street
addresses to a ZIP; that's unreliable and this module doesn't attempt it):

  - validate_city_state_zip(city, state, zip_code): confirms a client-given
    city/state/zip combination is internally consistent (the ZIP really
    does belong to that city/state per Zippopotam.us). Returns "valid",
    "mismatch", or "unknown" (lookup failed / inconclusive — never treated
    as an error, never blocks the pipeline).

  - lookup_zip_for_city(city, state): looks up all ZIP codes Zippopotam.us
    has for a given city/state. Returns a dict:
        {"status": "unique", "zip": "33020"}                — exactly one
        {"status": "multiple", "zips": ["33125", "33126"]}   — ambiguous
        {"status": "not_found"}                               — no match
        {"status": "unknown"}                                 — lookup failed
    Callers should ONLY auto-fill on "unique". Everything else means
    "keep current behavior" (ask the client).

Network failures, timeouts, malformed responses, or anything unexpected
NEVER raise — they degrade to "unknown" so this module can never block or
crash the pipeline. All lookups are cached in-process (per client+state key)
since the same city/state combo recurs often within a session/day.
"""

import requests

TIMEOUT_SECONDS = 10
BASE_URL = "http://api.zippopotam.us/us"

# In-process cache: {(city_lower, state_upper): result_dict_or_None}
# None means "looked up, no usable result" (not_found/unknown) — still
# cached so we don't hammer the API on repeat failures within a run.
_cache = {}


def _cache_key(city, state):
    return ((city or "").strip().lower(), (state or "").strip().upper())


def _fetch_places_for_city(city, state):
    """Query Zippopotam.us for a city/state. Returns a tuple:
        (places_or_None, failed_bool)
    places_or_None is a list of place dicts (each with 'post code',
    'place name', 'state abbreviation'), or None when the city/state has no
    match (confirmed 404 / empty result). failed_bool is True when the
    lookup itself could not be completed (network error, timeout, non-200
    other than 404, malformed JSON) — as opposed to a confirmed "no such
    city", which is failed_bool=False, places=None."""
    if not city or not state:
        return None, True

    key = _cache_key(city, state)
    if key in _cache:
        return _cache[key]

    result = (None, True)
    try:
        url = f"{BASE_URL}/{state.strip()}/{city.strip()}"
        resp = requests.get(url, timeout=TIMEOUT_SECONDS)
        if resp.status_code == 200:
            body = resp.json()
            places = body.get("places")
            if isinstance(places, list) and places:
                result = (places, False)
            else:
                result = (None, False)  # 200 but no places — confirmed empty
        elif resp.status_code == 404:
            result = (None, False)  # confirmed no such city/state
        # any other status code -> leave as failed
    except Exception:
        # Any failure (timeout, connection error, bad JSON, etc.) — degrade
        # to "failed". Never raise, never block the pipeline.
        result = (None, True)

    _cache[key] = result
    return result


def lookup_zip_for_city(city, state):
    """Look up ZIP code(s) for a given city + state.

    Returns one of:
        {"status": "unique", "zip": "<zip>"}
        {"status": "multiple", "zips": [...]}
        {"status": "not_found"}   -- confirmed no such city/state
        {"status": "unknown"}     -- lookup failed (network/timeout/etc.),
                                      never autofill on "unknown"
    """
    if not city or not state:
        return {"status": "unknown"}

    places, failed = _fetch_places_for_city(city, state)
    if failed:
        return {"status": "unknown"}
    if not places:
        return {"status": "not_found"}

    zips = sorted({p.get("post code") for p in places if p.get("post code")})
    if not zips:
        return {"status": "not_found"}
    if len(zips) == 1:
        return {"status": "unique", "zip": zips[0]}
    return {"status": "multiple", "zips": zips}


def validate_city_state_zip(city, state, zip_code):
    """Validate that a client-provided ZIP is consistent with the given
    city/state. Returns "valid", "mismatch", or "unknown".

    "unknown" covers lookup failure AND inconclusive results — callers
    should treat "unknown" as "can't confirm, don't block on it."
    """
    if not city or not state or not zip_code:
        return "unknown"

    places, failed = _fetch_places_for_city(city, state)
    if failed:
        return "unknown"
    if not places:
        return "mismatch"  # confirmed no such city/state -> given ZIP can't be right

    zip_clean = zip_code.strip().split("-")[0]  # tolerate ZIP+4
    known_zips = {p.get("post code") for p in places if p.get("post code")}
    if not known_zips:
        return "unknown"

    return "valid" if zip_clean in known_zips else "mismatch"
