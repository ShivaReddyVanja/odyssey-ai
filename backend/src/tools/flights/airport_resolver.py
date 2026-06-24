import os
import json
import requests
import threading
from typing import List
from pydantic import BaseModel, Field
from src.agents.base import generate_structured_output
from src.tools.flights.base import NearestAirportResolution, CandidateAirportsResolution, SelectedAirport

_AIRPORT_RESOLUTIONS_FILE = "airport_resolutions_cache.json"
_AIRPORT_CODE_FILE = "airport_code_cache.json"
_cache_lock = threading.Lock()

def _load_json_cache(filename: str) -> dict:
    """Loads a JSON cache file from disk."""
    with _cache_lock:
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

def _save_json_cache(filename: str, data: dict):
    """Saves a JSON cache file to disk."""
    with _cache_lock:
        try:
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

class AirportCodeResolution(BaseModel):
    iata_code: str = Field(..., description="The 3-letter IATA airport code for the location.")

def _lookup_static_india_airports(city_name: str) -> List[NearestAirportResolution]:
    """Looks up city_name in the static Indian airports database."""
    if not city_name:
        return []
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        india_airports_path = os.path.join(current_dir, "data", "india_airports.json")
        if not os.path.exists(india_airports_path):
            return []
        with open(india_airports_path, "r") as f:
            airports = json.load(f)
    except Exception as e:
        print(f"[Airport Resolver] Error loading india_airports.json: {e}")
        return []

    query = city_name.strip().lower()
    matches = []
    for entry in airports:
        score = 0
        name = entry.get("name", "").lower()
        iata = entry.get("iata", "").lower()
        state = entry.get("state", "").lower()
        city = entry.get("city", "").lower()
        aliases = [a.lower() for a in entry.get("aliases", [])]

        if query == city or query in aliases or query == iata:
            score = 3
        elif query in city or any(query in a for a in aliases):
            score = 2
        elif query in state or query in name:
            score = 1

        if score > 0:
            matches.append((score, entry))

    matches.sort(key=lambda x: x[0], reverse=True)
    return [
        NearestAirportResolution(airport_city=entry["city"], iata_code=entry["iata"].upper())
        for _, entry in matches
    ]

def _get_airports_via_places(city_name: str) -> List[dict]:
    """Queries the Google Places API for airports near the city using a Google Maps style query."""
    maps_key = os.getenv("GOOGLE_MAPS", "").strip('"').strip("'")
    if not maps_key:
        return []
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": f"nearest airport to {city_name}",
        "key": maps_key
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("status") in ["OK", "ZERO_RESULTS"]:
            return data.get("results", [])
        print(f"[Airport Resolver] Google Places API status for '{city_name}': {data.get('status')}")
    except Exception as e:
        print(f"[Airport Resolver] Google Places search failed for '{city_name}': {e}")
    return []

def get_airport_code(city_name: str, default: str = "DEL") -> str:
    """
    Dynamically resolves a city or region name to its primary 3-letter IATA airport code.
    Queries Google Places API and uses Gemini to resolve it.
    Caches the results persistently in airport_code_cache.json.
    """
    if not city_name:
        return default
        
    city_key = city_name.strip().lower()
    
    # Tier 1: Static DB lookup
    static_matches = _lookup_static_india_airports(city_name)
    if static_matches:
        return static_matches[0].iata_code.upper()
        
    # Check cache
    cache = _load_json_cache(_AIRPORT_CODE_FILE)
    if city_key in cache:
        return cache[city_key]
        
    # Check resolutions cache
    res_cache = _load_json_cache(_AIRPORT_RESOLUTIONS_FILE)
    if city_key in res_cache and res_cache[city_key]:
        return res_cache[city_key][0]["iata_code"].upper()
        
    # Tier 2: Google Places API + LLM Extraction
    places = _get_airports_via_places(city_name)
    if places:
        print(f"[Airport Resolver] get_airport_code Tier 2 Google Places lookup for '{city_name}'...")
        places_str = "\n".join([f"- {p.get('name')} ({p.get('formatted_address')})" for p in places[:5]])
        try:
            system_prompt = (
                "You are a travel database helper. Given a list of physical airports near a location, "
                "resolve the primary 3-letter IATA airport code for the location. "
                "Always return a valid, uppercase 3-letter IATA code."
            )
            user_prompt = (
                f"Location: '{city_name}'\n"
                f"Nearby Airports found via Google Places:\n{places_str}\n\n"
                f"Resolve the primary 3-letter IATA code for this location."
            )
            result = generate_structured_output(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=AirportCodeResolution
            )
            code = result.iata_code.strip().upper()
            if len(code) == 3 and code.isalpha():
                cache[city_key] = code
                _save_json_cache(_AIRPORT_CODE_FILE, cache)
                return code
        except Exception as e:
            print(f"[Airport Resolver] get_airport_code Tier 2 LLM extraction failed for {city_name}: {e}")
        
    # Tier 3: LLM fallback (pure LLM knowledge)
    try:
        print(f"[Airport Resolver] get_airport_code Tier 3 Pure LLM lookup for '{city_name}'...")
        system_prompt = (
            "You are a travel database helper. Given a city, region, or state, "
            "resolve it to its primary or nearest major 3-letter IATA airport code. "
            "Always return a valid, uppercase 3-letter IATA code."
        )
        user_prompt = f"Resolve the primary 3-letter IATA airport code for the location: '{city_name}'"
        
        result = generate_structured_output(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=AirportCodeResolution
        )
        code = result.iata_code.strip().upper()
        
        if len(code) == 3 and code.isalpha():
            cache[city_key] = code
            _save_json_cache(_AIRPORT_CODE_FILE, cache)
            return code
    except Exception as e:
        print(f"[Airport Resolver] get_airport_code Tier 3 Pure LLM failed for {city_name}: {e}")
        
    return default

def resolve_nearest_airport(city_name: str) -> NearestAirportResolution:
    """
    Resolves the nearest major commercial airport for a city.
    """
    candidates = resolve_nearest_airports(city_name)
    if candidates:
        return candidates[0]
    raise ValueError(f"Could not resolve any candidate airports for {city_name}")

def resolve_nearest_airports(city_name: str) -> List[NearestAirportResolution]:
    """
    Resolves up to 3 nearest commercial airports to a city, ordered by proximity.
    Queries Google Places API to find physical airports, then uses Gemini to extract IATA codes.
    Caches results persistently in airport_resolutions_cache.json.
    """
    if not city_name:
        return []
        
    city_key = city_name.strip().lower()
    
    # Tier 1: Static DB lookup
    static_matches = _lookup_static_india_airports(city_name)
    if static_matches:
        print(f"[Airport Resolver] Tier 1 Static DB match for '{city_name}': {[m.iata_code for m in static_matches]}")
        return static_matches
        
    # Check cache
    cache = _load_json_cache(_AIRPORT_RESOLUTIONS_FILE)
    if city_key in cache:
        return [NearestAirportResolution(**item) for item in cache[city_key]]

    # Tier 2: Google Places API + LLM Extraction
    places = _get_airports_via_places(city_name)
    if places:
        print(f"[Airport Resolver] Tier 2 Google Places lookup for '{city_name}' found {len(places)} candidates...")
        places_str = "\n".join([f"- {p.get('name')} ({p.get('formatted_address')})" for p in places[:5]])
        try:
            system_prompt = (
                "You are a travel database helper. Given a list of physical airports near a location, "
                "resolve their 3-letter IATA codes and select up to 3 nearest major commercial airports that have regular scheduled passenger flights. "
                "Order them by geographic proximity. Provide the airport city name, 3-letter IATA code, and driving distance in km."
            )
            user_prompt = (
                f"Location: '{city_name}'\n"
                f"Nearby Airports found via Google Places:\n{places_str}\n\n"
                f"Identify the 3-letter IATA codes and return the candidate airports."
            )
            result = generate_structured_output(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=CandidateAirportsResolution
            )
            res = []
            for a in result.airports:
                code = a.iata_code.strip().upper()
                if len(code) == 3 and code.isalpha():
                    res.append(NearestAirportResolution(airport_city=a.airport_city, iata_code=code))
            if res:
                cache[city_key] = [item.model_dump() for item in res]
                _save_json_cache(_AIRPORT_RESOLUTIONS_FILE, cache)
                return res
        except Exception as e:
            print(f"[Airport Resolver] Tier 2 LLM extraction failed for {city_name}: {e}")

    # Tier 3: LLM fallback (pure LLM knowledge)
    try:
        print(f"[Airport Resolver] Tier 3 Pure LLM lookup for '{city_name}'...")
        system_prompt = (
            "You are a travel database helper. Given a city or region name, "
            "identify up to 3 nearest major commercial airports that have regular scheduled passenger flights. "
            "Order them by geographic proximity. Provide the airport city name, 3-letter IATA code, and driving distance in km."
        )
        user_prompt = f"List up to 3 nearest commercial airports to: '{city_name}'"
        
        result = generate_structured_output(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=CandidateAirportsResolution
        )
        
        res = []
        for a in result.airports:
            code = a.iata_code.strip().upper()
            if len(code) == 3 and code.isalpha():
                res.append(NearestAirportResolution(airport_city=a.airport_city, iata_code=code))
            
        if res:
            cache[city_key] = [item.model_dump() for item in res]
            _save_json_cache(_AIRPORT_RESOLUTIONS_FILE, cache)
            return res
            
    except Exception as e:
        print(f"[Airport Resolver] Tier 3 Pure LLM failed for {city_name}: {e}")
        
    # Final fallback: simple airport code mapping
    code = get_airport_code(city_name)
    fallback = [NearestAirportResolution(airport_city=city_name, iata_code=code)]
    return fallback

def select_best_airport(
    origin_city: str, 
    destination_city: str, 
    candidates: List[NearestAirportResolution],
    is_departure: bool = False
) -> NearestAirportResolution:
    """
    Uses Gemini to select the best airport from candidate airports based on connectivity.
    """
    if not candidates:
        raise ValueError("Candidates list cannot be empty.")
    if len(candidates) == 1:
        return candidates[0]
        
    # Check if all candidate IATAs are in the static India airport DB
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        india_airports_path = os.path.join(current_dir, "data", "india_airports.json")
        if os.path.exists(india_airports_path):
            with open(india_airports_path, "r") as f:
                airports = json.load(f)
            static_iatas = {entry["iata"].upper() for entry in airports}
            if all(c.iata_code.upper() in static_iatas for c in candidates):
                print(f"[Airport Resolver] All candidates {[c.iata_code for c in candidates]} are in the static India DB. Skipping LLM selection.")
                return candidates[0]
    except Exception as e:
        print(f"[Airport Resolver] Error checking candidates against static DB: {e}")
        
    candidates_str = "\n".join([f"- {c.airport_city} ({c.iata_code})" for c in candidates])
    
    if is_departure:
        system_prompt = (
            "You are an expert travel planner. Given the traveler's starting town/origin and destination, "
            "select the best starting commercial airport from the candidates near the starting town. "
            "Typically, the closest major commercial airport with reliable flights is best. Select the single best airport and return it."
        )
        user_prompt = (
            f"Traveler is starting from: {origin_city}\n"
            f"Going to: {destination_city}\n"
            f"Candidate starting airports near {origin_city}:\n{candidates_str}\n\n"
            f"Which starting airport is the best choice?"
        )
    else:
        system_prompt = (
            "You are an expert travel planner. Given the traveler's origin and final destination city, "
            "select the best arrival airport near the destination from the candidates. "
            "If the closest airport (e.g. Kullu KUU) has very limited connectivity or flight options, "
            "prefer a larger/major hub airport (e.g. Delhi DEL or Chandigarh IXC) that connects well with the origin "
            "even if the driving distance is longer. Select the single best airport and return it."
        )
        user_prompt = (
            f"Traveler is flying from: {origin_city}\n"
            f"Final Destination: {destination_city}\n"
            f"Candidate arrival airports near {destination_city}:\n{candidates_str}\n\n"
            f"Which arrival airport is the best choice for flying from {origin_city}?"
        )
        
    try:
        selected = generate_structured_output(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=SelectedAirport
        )
        
        for c in candidates:
            if c.iata_code.upper().strip() == selected.iata_code.upper().strip():
                return c
                
        return NearestAirportResolution(airport_city=selected.airport_city, iata_code=selected.iata_code)
    except Exception:
        return candidates[0]
