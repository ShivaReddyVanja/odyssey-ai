import os
import json
import threading

_FLIGHT_CACHE_FILE = "flight_search_cache.json"
_lock = threading.Lock()

def _load_cache() -> dict:
    """Loads flight queries cache from disk."""
    with _lock:
        if os.path.exists(_FLIGHT_CACHE_FILE):
            try:
                with open(_FLIGHT_CACHE_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

def _save_cache(cache: dict):
    """Saves flight queries cache to disk."""
    with _lock:
        try:
            with open(_FLIGHT_CACHE_FILE, "w") as f:
                json.dump(cache, f, indent=2)
        except Exception:
            pass
