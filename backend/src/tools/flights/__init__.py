import os
from typing import List
from datetime import datetime, timedelta
from src.graph.state import TransitOption, TravelMode

# Re-expose location and airport mapping helpers from sub-module
from src.tools.flights.airport_resolver import (
    get_airport_code,
    resolve_nearest_airport,
    resolve_nearest_airports,
    select_best_airport,
)

# Import caches and providers
from src.tools.flights.cache import _load_cache, _save_cache
from src.tools.flights.serpapi import SerpApiFlightProvider
from src.tools.flights.skyscanner import SkyscannerFlightProvider

def search_transit(origin: str, destination: str, start_date: str) -> List[TransitOption]:
    """
    Unified entry point for flight searches. 
    Selects provider from FLIGHT_PROVIDER env variable ('serpapi' or 'skyscanner'),
    caches query responses to prevent credit wastage, and provides mock fallback on errors.
    """
    origin_clean = origin.strip().lower()
    dest_clean = destination.strip().lower()
    
    if not start_date or len(start_date.strip()) < 10:
        date_str = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    else:
        date_str = start_date.strip()[:10]
        
    provider_name = os.getenv("FLIGHT_PROVIDER", "serpapi").lower().strip()
    
    # 1. Check persistent disk cache first
    cache_key = f"{provider_name}_{origin_clean}_{dest_clean}_{date_str}"
    cache = _load_cache()
    if cache_key in cache:
        print(f"[Flight Cache] Loading cached flights for {cache_key}...")
        return [TransitOption(**opt) for opt in cache[cache_key]]
        
    # 2. Setup chosen provider
    if provider_name == "skyscanner":
        token = os.getenv("APIFY_API_TOKEN", os.getenv("APIFY_TOKEN", "")).strip('"').strip("'")
        provider = SkyscannerFlightProvider(token=token)
    else:
        provider = SerpApiFlightProvider()
        
    # 3. Query flights
    options = provider.search_flights(origin, destination, date_str)
    
    # 4. Save successful queries to disk cache
    if options:
        cache[cache_key] = [opt.model_dump() for opt in options]
        _save_cache(cache)
        return options
        
    print(f"[Flight Helper] No flights found via {provider_name} for {origin} ➔ {destination}.")
    return []
