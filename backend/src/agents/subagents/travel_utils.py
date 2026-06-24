import os
import time
import json
import math
import requests
import threading
from typing import List
from datetime import datetime, timedelta
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from src.graph.state import TravelMode, TransitOption
from src.tools.flights import search_transit, get_airport_code, resolve_nearest_airports, select_best_airport
from src.tools.routes import get_route_directions
from src.utils.logger import log_agent, log_dev

class CityCountryDetails(BaseModel):
    country: str = Field(..., description="The name of the country the city is located in.")

def get_city_country(city: str) -> str:
    """Resolves the country name for a city using local checks, Google Geocoding API, or SerpAPI."""
    c_lower = city.lower().strip()
    if c_lower.endswith(", india") or c_lower.endswith(", in") or "india" in c_lower:
        return "India"
        
    # Check against static Indian DB
    from src.tools.flights.airport_resolver import _lookup_static_india_airports
    if _lookup_static_india_airports(city):
        return "India"
        
    # 1. Try Google Geocoding API first (uses Google Maps key)
    import requests
    maps_key = os.getenv("GOOGLE_MAPS", "").strip('"').strip("'")
    if maps_key:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": city,
            "key": maps_key
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "OK" and data.get("results"):
                result = data["results"][0]
                for component in result.get("address_components", []):
                    if "country" in component.get("types", []):
                        country = component.get("long_name", "").strip()
                        if country:
                            print(f"[Geography Helper] Geocoded country for '{city}' -> '{country}'")
                            return country
        except Exception as e:
            print(f"[Geography Helper] Google Geocoding failed for '{city}': {e}")

    # 2. Fall back to SerpAPI / Google Search
    from src.tools.search_helper import search_and_extract_fact
    try:
        query = f"what country is {city} in"
        system_prompt = (
            "You are a geography helper. Identify the country in which the given city is located."
        )
        extraction_prompt = f"Identify the country for: '{city}'"
        result = search_and_extract_fact(
            query=query,
            system_prompt=system_prompt,
            extraction_prompt=extraction_prompt,
            output_schema=CityCountryDetails
        )
        country = result.country.strip()
        print(f"[Geography Helper] Google Search resolved country for {city} -> {country}")
        return country
    except Exception as e:
        print(f"[Geography Helper] Google Search failed to find country for {city}: {e}")
        
    return "India"

def is_international_travel(start_city: str, end_city: str) -> bool:
    """Checks if travel between start_city and end_city is international."""
    start_country = get_city_country(start_city)
    end_country = get_city_country(end_city)
    is_inter = start_country.lower() != end_country.lower()
    print(f"[International Check] {start_city} ({start_country}) to {end_city} ({end_country}) -> International: {is_inter}")
    return is_inter

def get_next_date(date_str: str, days: int) -> str:
    """
    Safely adds days to a YYYY-MM-DD date string. Falls back to original string on error.
    """
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        next_dt = dt + timedelta(days=days)
        return next_dt.strftime("%Y-%m-%d")
    except Exception:
        return date_str

_coord_lock = threading.Lock()
_COORDINATES_CACHE_FILE = "city_coordinates_cache.json"

def _load_coordinates_cache() -> dict:
    with _coord_lock:
        if os.path.exists(_COORDINATES_CACHE_FILE):
            try:
                with open(_COORDINATES_CACHE_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

def _save_coordinates_cache(cache: dict):
    with _coord_lock:
        try:
            with open(_COORDINATES_CACHE_FILE, "w") as f:
                json.dump(cache, f, indent=2)
        except Exception:
            pass

def get_city_coordinates(city: str) -> tuple:
    """Resolves (latitude, longitude) for a city/location and caches it."""
    c_key = city.lower().strip()
    cache = _load_coordinates_cache()
    if c_key in cache:
        return tuple(cache[c_key])
        
    maps_key = os.getenv("GOOGLE_MAPS", "").strip('"').strip("'")
    if maps_key:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": city, "key": maps_key}
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "OK" and data.get("results"):
                loc = data["results"][0]["geometry"]["location"]
                lat, lng = loc["lat"], loc["lng"]
                cache[c_key] = [lat, lng]
                _save_coordinates_cache(cache)
                return lat, lng
        except Exception as e:
            print(f"[Geography Helper] Geocoding coordinates failed for '{city}': {e}")
            
    return 20.5937, 78.9629

class FlightVerification(BaseModel):
    has_active_flights: bool = Field(..., description="True if there are active commercial passenger flights between these airports, False otherwise.")
    reasoning: str = Field(..., description="Brief explanation of why flights exist or do not exist based on search results.")

def verify_active_flights(start_iata: str, end_iata: str, start_city: str, end_city: str) -> bool:
    """Uses Google Search (SerpAPI) and Gemini to verify if commercial passenger flights exist between two airports."""
    from src.tools.search_helper import search_and_extract_fact
    
    query = f"commercial passenger flights between {start_iata} and {end_iata}"
    system_prompt = (
        "You are a travel assistant. Your job is to verify if there are any active commercial passenger flights "
        "operating between the two given airports (either direct or with connections). "
        "Focus on commercial passenger services, not charter or cargo flights."
    )
    extraction_prompt = (
        f"Based on the Google search results, are there active passenger flights between "
        f"'{start_city} ({start_iata})' and '{end_city} ({end_iata})'? "
        "Return True if flights exist, and False if there is no commercial flight connection between them."
    )
    
    try:
        result = search_and_extract_fact(
            query=query,
            system_prompt=system_prompt,
            extraction_prompt=extraction_prompt,
            output_schema=FlightVerification
        )
        print(f"[Flight Verification] {start_iata} ➔ {end_iata} active flights: {result.has_active_flights} | Reasoning: {result.reasoning}")
        return result.has_active_flights
    except Exception as e:
        print(f"[Flight Verification] Verification failed for {start_iata} ➔ {end_iata}: {e}")
        return False

def estimate_flight_details(start_city: str, end_city: str) -> tuple:
    """Estimates flight duration (minutes) and price (INR) based on geocoded distance."""
    lat1, lon1 = get_city_coordinates(start_city)
    lat2, lon2 = get_city_coordinates(end_city)
    
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_km = R * c
    
    duration_minutes = int(30 + (distance_km / 800.0) * 60)
    duration_minutes = max(45, duration_minutes)
    
    estimated_price = int(3000 + distance_km * 4.5)
    estimated_price = max(3500, estimated_price)
    
    print(f"[Flight Estimator] Distance: {distance_km:.1f} km | Estimated Duration: {duration_minutes} mins | Estimated Price: INR {estimated_price}")
    return duration_minutes, estimated_price

def resolve_hop_segments(
    start_city: str, 
    end_city: str, 
    date: str, 
    styles: List[str], 
    config: RunnableConfig,
    force_driving: bool = False
) -> List[TransitOption]:
    """
    Resolves the transit segments for a travel leg between start_city and end_city.
    Compares direct driving time with multi-hop flight path duration (including airport wait buffer)
    and selects the optimal route.
    """
    no_road_route = False
    
    # 1. Local helper to get road transit segment (defined first so we can check driving time)
    def get_road_transit_option(start: str, end: str, idx: int = 0) -> TransitOption:
        nonlocal no_road_route
        route_data = get_route_directions(start, end, "driving")
        
        if route_data.get("no_route"):
            if start == start_city and end == end_city:
                no_road_route = True
                dur_mins = -1
            else:
                dur_mins = 30
        else:
            dur_mins = route_data.get("duration_minutes", 120)
            
        dist_meters = route_data.get("distance_meters", 100000.0)
        est_price = max(500, int((dist_meters / 1000.0) * 15.0))
        
        dep_str = "09:00"
        try:
            dep_dt = datetime.strptime("09:00", "%H:%M")
            arr_dt = dep_dt + timedelta(minutes=dur_mins if dur_mins > 0 else 0)
            arr_str = arr_dt.strftime("%H:%M")
        except Exception:
            arr_str = "12:00"
            
        return TransitOption(
            id=f"road_{start.lower().replace(' ', '_')}_{end.lower().replace(' ', '_')}_{idx}",
            origin=start,
            destination=end,
            departure_time=dep_str,
            arrival_time=arr_str,
            mode=TravelMode.DRIVING,
            duration_minutes=dur_mins,
            estimated_price=est_price,
            carrier="Self-Drive / Ride"
        )

    # 2. Check direct driving suitability first to avoid unnecessary airport resolution / SerpAPI calls
    direct_road = get_road_transit_option(start_city, end_city)
    road_duration = direct_road.duration_minutes
    
    has_road_style = any(s.lower() in ["motorcycle riding", "motorcycle", "riding", "road trip", "driving", "car", "roadtrip"] for s in styles)
    
    is_inter = is_international_travel(start_city, end_city)
    
    # We should search for flights if:
    # - International travel
    # - No road route exists
    # - Road travel time is > 15 hours (900 minutes) and driving is not forced
    needs_flight_search = False
    if is_inter:
        log_agent(config, f"I've detected a cross-border leg from {start_city} to {end_city} — searching for the best flight connection.")
        needs_flight_search = True
    elif no_road_route:
        log_agent(config, f"I've found no road access between {start_city} and {end_city} — I'll search for a flight instead.")
        needs_flight_search = True
    elif road_duration > 900:
        if force_driving or (has_road_style and force_driving):
            log_agent(config, f"Road trip style is set — I'll route {start_city} to {end_city} by road.")
        else:
            log_agent(config, f"The road distance from {start_city} to {end_city} exceeds 15 hours — I'll look for a flight instead.")
            needs_flight_search = True
            
    if not needs_flight_search:
        log_agent(config, f"{start_city} to {end_city} is a reasonable drive — I'll route by road.")
        return [direct_road]

    # 3. Resolve nearest airports and select best start/end airports using Gemini (only for long/inter trips)
    try:
        start_candidates = resolve_nearest_airports(start_city)
        start_airport_info = select_best_airport(
            origin_city=start_city,
            destination_city=end_city,
            candidates=start_candidates,
            is_departure=True
        )
        start_airport_city = start_airport_info.airport_city
        start_iata = start_airport_info.iata_code
    except Exception as e:
        log_dev(config, f"[Travel Agent] Error resolving start airport for start city {start_city}: {e}. Fallback to direct name.")
        start_airport_city = start_city
        start_iata = get_airport_code(start_city)
        
    try:
        end_candidates = resolve_nearest_airports(end_city)
        end_airport_info = select_best_airport(
            origin_city=start_city,
            destination_city=end_city,
            candidates=end_candidates,
            is_departure=False
        )
        end_airport_city = end_airport_info.airport_city
        end_iata = end_airport_info.iata_code
    except Exception as e:
        log_dev(config, f"[Travel Agent] Error resolving end airport for end city {end_city}: {e}. Fallback to direct name.")
        end_airport_city = end_city
        end_iata = get_airport_code(end_city)

    needs_start_road = start_airport_city.lower().strip() != start_city.lower().strip()
    needs_end_road = end_airport_city.lower().strip() != end_city.lower().strip()
    needs_flight = start_airport_city.lower().strip() != end_airport_city.lower().strip()
    flight_options_found = False
    flight_candidates = []
    
    if needs_flight:
        log_agent(config, f"I'm checking available flights from {start_airport_city} to {end_airport_city}...")
        start_time = time.perf_counter()
        flight_candidates = search_transit(start_airport_city, end_airport_city, date)
        dur = time.perf_counter() - start_time
        log_dev(config, f"[Latency Metric] Flight search ({start_airport_city} -> {end_airport_city}): {dur:.2f}s")
        
        # If the first choice fails, try other resolved candidate airports in the list
        if not flight_candidates:
            log_agent(config, f"I found no direct connection from {start_airport_city} to {end_airport_city} — exploring nearby airport alternatives.")
            for alt in end_candidates:
                alt_city = alt.airport_city
                alt_iata = alt.iata_code
                if alt_city.lower().strip() != end_airport_city.lower().strip() and alt_city.lower().strip() != start_airport_city.lower().strip():
                    log_agent(config, f"I'm checking a connection via {alt_city} instead...")
                    start_time = time.perf_counter()
                    alt_candidates = search_transit(start_airport_city, alt_city, date)
                    dur = time.perf_counter() - start_time
                    log_dev(config, f"[Latency Metric] Flight search ({start_airport_city} -> {alt_city}): {dur:.2f}s")
                    
                    if alt_candidates:
                        flight_candidates = alt_candidates
                        end_airport_city = alt_city
                        end_iata = alt_iata
                        needs_end_road = end_airport_city.lower().strip() != end_city.lower().strip()
                        break
                        
        if not flight_candidates:
            log_agent(config, f"I'm verifying scheduled airline services between {start_city} and {end_city}...")
            if verify_active_flights(start_iata, end_iata, start_city, end_city):
                est_dur, est_price = estimate_flight_details(start_city, end_city)
                fallback_flight = TransitOption(
                    id=f"flight_fallback_{start_iata.lower()}_{end_iata.lower()}",
                    origin=f"{start_airport_city} ({start_iata})",
                    destination=f"{end_airport_city} ({end_iata})",
                    departure_time="12:00",
                    arrival_time="15:00",
                    mode=TravelMode.FLIGHT,
                    duration_minutes=est_dur,
                    estimated_price=est_price,
                    carrier="Scheduled Airline"
                )
                flight_candidates = [fallback_flight]
                log_agent(config, f"I've confirmed a scheduled service between {start_city} and {end_city} — estimated {est_dur}-minute flight at approximately INR {est_price:,}.")

        # If still no flight candidates found but no road access exists (or international), set sensible default flight fallback
        if not flight_candidates and (no_road_route or is_inter):
            fallback_flight = TransitOption(
                id=f"flight_fallback_{start_iata.lower()}_{end_iata.lower()}",
                origin=f"{start_airport_city} ({start_iata})",
                destination=f"{end_airport_city} ({end_iata})",
                departure_time="12:00",
                arrival_time="15:00",
                mode=TravelMode.FLIGHT,
                duration_minutes=180,
                estimated_price=7500,
                carrier="Scheduled Airline"
            )
            flight_candidates = [fallback_flight]
            log_agent(config, f"No commercial flight connections found between {start_city} and {end_city} — routing via Scheduled Airline fallback (180 mins, INR 7,500).")
        
        if flight_candidates:
            flight_options_found = True
            
            # We found flights! Let's calculate total flight path duration
            start_road_dur = 0
            if needs_start_road:
                start_road_route = get_route_directions(start_city, start_airport_city, "driving")
                start_road_dur = start_road_route.get("duration_minutes", 120)
                
            end_road_dur = 0
            if needs_end_road:
                end_road_route = get_route_directions(end_airport_city, end_city, "driving")
                end_road_dur = end_road_route.get("duration_minutes", 120)
                
            flight_dur = flight_candidates[0].duration_minutes
            
            # Flight path overhead: 120 mins buffer (for check-in, security, airport transfers)
            flight_overhead = 120
            
            total_flight_path_duration = start_road_dur + flight_dur + end_road_dur + flight_overhead
            
            log_dev(config, f"[Travel Agent] Comparing durations: Direct Road = {road_duration} mins vs. Flight Path = {total_flight_path_duration} mins (Start transfer: {start_road_dur} mins, Flight: {flight_dur} mins, End transfer: {end_road_dur} mins, Buffer: {flight_overhead} mins)")
            
            # If no road route exists, flight path is always chosen since road_duration is -1
            if road_duration == -1 or total_flight_path_duration < road_duration:
                # Flight path is faster — build and return flight path segments
                log_agent(config, f"Flying is the better option here — it saves significant travel time over driving.")
                
                hop_transit_options = []
                if needs_start_road:
                    road_to_airport = get_road_transit_option(start_city, start_airport_city, idx=0)
                    hop_transit_options.append(road_to_airport)
                    
                # Select only the single best flight candidate to avoid duplicates
                best_flight = flight_candidates[0]
                best_flight.id = f"flight_{start_airport_city.lower().replace(' ', '_')}_{end_airport_city.lower().replace(' ', '_')}_0"
                hop_transit_options.append(best_flight)
                
                if needs_end_road:
                    road_to_dest = get_road_transit_option(end_airport_city, end_city, idx=1)
                    hop_transit_options.append(road_to_dest)
                    
                return hop_transit_options
            else:
                log_agent(config, f"Driving is more efficient for this leg — I'll route by road.")
                return [direct_road]
        else:
            log_agent(config, f"I found no suitable flight connection — I'll review road access options.")
            
    # If no flights needed or no flights found, return direct road option
    log_agent(config, f"{start_city} to {end_city} — routing by road.")
    return [direct_road]
