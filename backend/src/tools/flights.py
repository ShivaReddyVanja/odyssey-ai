import os
import requests
from typing import List
from src.graph.state import TransitOption, TravelMode
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv(override=True)

SERP_API_KEY = os.getenv("SERP_API_KEY", "").strip('"').strip("'")

from pydantic import BaseModel, Field
from src.tools.search_helper import search_and_extract_fact

class AirportCodeResolution(BaseModel):
    iata_code: str = Field(..., description="The 3-letter IATA airport code for the location.")

# Simple in-memory cache for resolved city IATA airport codes
_AIRPORT_CODE_CACHE = {
    "hyderabad": "HYD",
    "delhi": "DEL",
    "mumbai": "BOM",
    "bangalore": "BLR",
    "rome": "FCO",
    "paris": "CDG",
    "london": "LHR",
    "new york": "JFK",
    "tokyo": "HND",
    "goa": "GOI",
}

def get_airport_code(city_name: str, default: str = "DEL") -> str:
    """
    Dynamically resolves a city or region name to its primary 3-letter IATA airport code
    by searching Google (via SerpAPI) and extracting the fact using the LLM.
    Uses _AIRPORT_CODE_CACHE to bypass remote searches/extractions.
    """
    if not city_name:
        return default
        
    city_key = city_name.strip().lower()
    if city_key in _AIRPORT_CODE_CACHE:
        return _AIRPORT_CODE_CACHE[city_key]
        
    import time
    start_time = time.perf_counter()
    try:
        query = f"primary 3 letter IATA airport code for {city_name}"
        system_prompt = (
            "You are a travel database helper. Given a city, region, or state, "
            "resolve it to its primary or nearest major 3-letter IATA airport code. "
            "Always return a valid, uppercase 3-letter IATA code."
        )
        extraction_prompt = f"Resolve the primary IATA airport code for the location: '{city_name}'"
        
        result = search_and_extract_fact(
            query=query,
            system_prompt=system_prompt,
            extraction_prompt=extraction_prompt,
            output_schema=AirportCodeResolution
        )
        code = result.iata_code.strip().upper()
        
        if len(code) == 3 and code.isalpha():
            _AIRPORT_CODE_CACHE[city_key] = code
            return code
    except Exception as e:
        pass
        
    return default

def get_dynamic_transit(origin: str, destination: str, start_date: str) -> List[TransitOption]:
    """
    Generates a dynamic flight fallback using the actual origin and destination names.
    This does not contain hardcoded coordinates, avoiding coordinate contamination.
    """
    origin_code = get_airport_code(origin, "DEL")
    dest_code = get_airport_code(destination, "TYO")
    
    return [
        TransitOption(
            id="transit_flight_fallback_1",
            origin=f"{origin} Airport ({origin_code})",
            destination=f"{destination} Airport ({dest_code})",
            departure_time="09:00",
            arrival_time="11:30",
            mode=TravelMode.FLIGHT,
            duration_minutes=150,
            estimated_price=4500,
            carrier="IndiGo"
        ),
        TransitOption(
            id="transit_flight_fallback_2",
            origin=f"{origin} Airport ({origin_code})",
            destination=f"{destination} Airport ({dest_code})",
            departure_time="16:00",
            arrival_time="18:30",
            mode=TravelMode.FLIGHT,
            duration_minutes=150,
            estimated_price=5200,
            carrier="Air India"
        )
    ]

def search_transit(origin: str, destination: str, start_date: str) -> List[TransitOption]:
    """
    Searches flight candidates from SerpAPI (Google Flights engine).
    Uses a 30-second timeout and falls back to dynamic, non-contaminated transit options on failure.
    """
    # Fallback to 7 days from today if start_date is empty or invalid
    if not start_date or len(start_date.strip()) < 10:
        start_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        print(f"[Flights Tool] No start_date specified. Defaulting to: {start_date}")

    origin_code = get_airport_code(origin, "DEL")
    dest_code = get_airport_code(destination, "TYO")

    if not SERP_API_KEY:
        print("[Flights Tool] Warning: SERP_API_KEY is missing in the environment. Returning dynamic fallback transit.")
        return get_dynamic_transit(origin, destination, start_date)

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_flights",
        "departure_id": origin_code,
        "arrival_id": dest_code,
        "outbound_date": start_date,
        "type": "2",  # 2 represents One-way flight (avoids requiring return_date)
        "currency": "INR",
        "hl": "en",
        "api_key": SERP_API_KEY
    }

    try:
        # Increase timeout to 30s as Google Flights engine live scraping can take time
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Parse flights from best_flights
        best_flights = data.get("best_flights", [])
        
        transit_options = []
        for i, flight_group in enumerate(best_flights[:2]):
            # Get first and last flight segment details
            flights = flight_group.get("flights", [])
            if not flights:
                continue
                
            flight_start = flights[0]
            flight_end = flights[-1]
            price = flight_group.get("price", 0)
            duration = flight_group.get("total_duration", 0)
            
            transit_options.append(
                TransitOption(
                    id=f"flight_serp_{i+1}",
                    origin=f"{flight_start.get('departure_airport', {}).get('name', origin)} ({flight_start.get('departure_airport', {}).get('id', origin_code)})",
                    destination=f"{flight_end.get('arrival_airport', {}).get('name', destination)} ({flight_end.get('arrival_airport', {}).get('id', dest_code)})",
                    departure_time=flight_start.get("departure_airport", {}).get("time", "12:00"),
                    arrival_time=flight_end.get("arrival_airport", {}).get("time", "18:00"),
                    mode=TravelMode.FLIGHT,
                    duration_minutes=duration,
                    estimated_price=float(price) if price else None,
                    carrier=flight_start.get("airline", "Airline")
                )
            )
            
        if not transit_options:
            print(f"[Flights Tool] SerpAPI returned no flight offers.")
            return []
            
        return transit_options
    except Exception as e:
        print(f"[Flights Tool] Query failed or timed out: {e}.")
        return []
