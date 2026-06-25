import os
import json
import threading

_FLIGHT_CACHE_NAME = "flight_search_cache.json"
_lock = threading.Lock()

def get_cache_path(filename: str) -> str:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    cache_dir = os.path.join(project_root, "cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, filename)

def _load_cache() -> dict:
    """Loads flight queries cache from disk."""
    cache_file = get_cache_path(_FLIGHT_CACHE_NAME)
    with _lock:
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

def _save_cache(cache: dict):
    """Saves flight queries cache to disk."""
    cache_file = get_cache_path(_FLIGHT_CACHE_NAME)
    with _lock:
        try:
            with open(cache_file, "w") as f:
                json.dump(cache, f, indent=2)
        except Exception:
            pass
