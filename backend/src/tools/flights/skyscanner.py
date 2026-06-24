import os
import requests
from typing import List
from datetime import datetime, timedelta
from src.graph.state import TransitOption, TravelMode
from src.tools.flights.base import FlightProvider
from src.tools.flights.airport_resolver import get_airport_code

import json

import threading

_SKYSCANNER_LOCATION_FILE = "skyscanner_location_cache.json"
_location_cache_lock = threading.Lock()

def _load_skyscanner_location_cache() -> dict:
    """Loads Skyscanner location cache from disk."""
    with _location_cache_lock:
        if os.path.exists(_SKYSCANNER_LOCATION_FILE):
            try:
                with open(_SKYSCANNER_LOCATION_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

def _save_skyscanner_location_cache(cache: dict):
    """Saves Skyscanner location cache from disk."""
    with _location_cache_lock:
        try:
            with open(_SKYSCANNER_LOCATION_FILE, "w") as f:
                json.dump(cache, f, indent=2)
        except Exception:
            pass

def resolve_skyscanner_location(city_name: str, token: str) -> tuple:
    """
    Resolves Skyscanner SkyId and EntityId for a city.
    Uses IATA codes directly for both to bypass searchAirport Apify calls.
    """
    # 1. Try static DB lookup first (Fast, O(1))
    from src.tools.flights.airport_resolver import _lookup_static_india_airports
    static_matches = _lookup_static_india_airports(city_name)
    if static_matches:
        code = static_matches[0].iata_code.upper()
        return (code, code)
        
    # 2. Use airport resolver (Geocoding / Google Search / LLM)
    code = get_airport_code(city_name)
    return (code, code)


class SkyscannerFlightProvider(FlightProvider):
    """
    Flight provider that runs Skyscanner flight searches synchronously using Apify actor 9Fn6MQ3FlBxgimMwW.
    """
    def __init__(self, token: str):
        self.token = token
        
    def search_flights(self, origin: str, destination: str, start_date: str) -> List[TransitOption]:
        if not self.token:
            print("[Skyscanner] Warning: API_TOKEN is missing. Returning empty flight list.")
            return []
            
        origin_sky, origin_entity = resolve_skyscanner_location(origin, self.token)
        dest_sky, dest_entity = resolve_skyscanner_location(destination, self.token)
        
        url = f"https://api.apify.com/v2/actors/9Fn6MQ3FlBxgimMwW/run-sync-get-dataset-items?token={self.token}"
        
        request_params = {
            "endpoint": "searchFlights",
            "originSkyId": origin_sky,
            "destinationSkyId": dest_sky,
            "originEntityId": origin_entity if origin_entity else "95673323",
            "destinationEntityId": dest_entity if dest_entity else "95673323",
            "date": start_date,
            "currency": "INR",
            "market": "IN"
        }
        
        payload = {
            "requests": [request_params]
        }
        
        try:
            print(f"[Skyscanner] Searching flights from {origin} ({origin_sky}) to {destination} ({dest_sky}) on {start_date}...")
            response = requests.post(url, json=payload, timeout=45)
            response.raise_for_status()
            items = response.json()
            
            def extract_results(items_list) -> list:
                if not items_list:
                    return []
                
                # If it's a dict, convert to list
                if isinstance(items_list, dict):
                    items_list = [items_list]
                    
                if not isinstance(items_list, list):
                    return []
                    
                # Safe recursive list unpacking for nested arrays (e.g. [[{...}]])
                first = items_list[0]
                while isinstance(first, list) and len(first) > 0:
                    first = first[0]
                    
                if not isinstance(first, dict):
                    return []
                    
                # A: Check if itineraries is a list or dict under data
                data = first.get("data", {})
                if isinstance(data, dict):
                    itineraries = data.get("itineraries")
                    if isinstance(itineraries, list):
                        return itineraries
                    if isinstance(itineraries, dict):
                        res = itineraries.get("results", [])
                        if isinstance(res, list):
                            return res
                            
                # B: Check if itineraries is a list or dict directly under first
                itineraries = first.get("itineraries")
                if isinstance(itineraries, list):
                    return itineraries
                if isinstance(itineraries, dict):
                    res = itineraries.get("results", [])
                    if isinstance(res, list):
                        return res
                        
                # C: Direct results list key
                res = first.get("results")
                if isinstance(res, list):
                    return res
                    
                # D: The items list itself is the list of itineraries
                if "id" in first or "legs" in first:
                    return [x for x in items_list if isinstance(x, dict) and ("id" in x or "legs" in x)]
                    
                return []

            results = extract_results(items)
            
            # If no results found, let's log the raw response structure for debugging
            if not results and items:
                print(f"[Skyscanner] Debug info - raw items type: {type(items)}")
                print(f"[Skyscanner] First element type: {type(items[0]) if isinstance(items, list) and len(items) > 0 else 'N/A'}")
                print(f"[Skyscanner] Preview: {str(items)[:600]}")

            transit_options = []

            for idx, result in enumerate(results[:2]):
                price_info = result.get("price", {})
                amount = price_info.get("raw") or price_info.get("amount")
                if amount is None:
                    formatted = price_info.get("formatted", "")
                    if formatted:
                        import re
                        nums = re.findall(r'\d+', formatted.replace(',', '').replace('.', ''))
                        if nums:
                            amount = float(nums[0])
                            
                legs = result.get("legs", [])
                if not legs:
                    continue
                    
                leg = legs[0]
                if isinstance(leg, dict):
                    origin_val = leg.get("origin")
                    dest_val = leg.get("destination")
                    
                    if isinstance(origin_val, dict):
                        origin_code = origin_val.get("displayCode") or origin_val.get("id") or origin_sky
                        origin_name = origin_val.get("name", origin)
                    else:
                        origin_code = str(origin_val) if origin_val else origin_sky
                        origin_name = origin
                        
                    if isinstance(dest_val, dict):
                        dest_code = dest_val.get("displayCode") or dest_val.get("id") or dest_sky
                        dest_name = dest_val.get("name", destination)
                    else:
                        dest_code = str(dest_val) if dest_val else dest_sky
                        dest_name = destination
                        
                    departure_time = leg.get("departure", "12:00")
                    arrival_time = leg.get("arrival", "18:00")
                    
                    if departure_time and "T" in departure_time:
                        departure_time = departure_time.replace("T", " ")
                        if len(departure_time) > 16:
                            departure_time = departure_time[:16]
                            
                    if arrival_time and "T" in arrival_time:
                        arrival_time = arrival_time.replace("T", " ")
                        if len(arrival_time) > 16:
                            arrival_time = arrival_time[:16]
                            
                    duration = leg.get("durationMinutes") or leg.get("durationInMinutes") or leg.get("duration", 0)
                    
                    carriers_info = leg.get("carriers", {})
                    carrier_name = "Airline"
                    if isinstance(carriers_info, dict):
                        marketing_carriers = carriers_info.get("marketing", [])
                        if marketing_carriers and isinstance(marketing_carriers, list) and len(marketing_carriers) > 0:
                            carrier_name = marketing_carriers[0].get("name", "Airline")
                    elif isinstance(carriers_info, list) and len(carriers_info) > 0:
                        if isinstance(carriers_info[0], dict):
                            carrier_name = carriers_info[0].get("name", "Airline")
                        else:
                            carrier_name = str(carriers_info[0])
                            
                    transit_options.append(
                        TransitOption(
                            id=f"flight_skyscanner_{idx+1}",
                            origin=f"{origin_name} ({origin_code})",
                            destination=f"{dest_name} ({dest_code})",
                            departure_time=departure_time,
                            arrival_time=arrival_time,
                            mode=TravelMode.FLIGHT,
                            duration_minutes=duration,
                            estimated_price=int(round(float(amount))) if amount else None,
                            carrier=carrier_name
                        )
                    )

            return transit_options
        except Exception as e:
            print(f"[Skyscanner] Flight search query failed: {e}")
            return []
