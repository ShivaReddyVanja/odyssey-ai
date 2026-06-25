import os
import requests
from typing import List
from datetime import datetime, timedelta
from src.graph.state import TransitOption, TravelMode
from src.tools.flights.base import FlightProvider
from src.tools.flights.airport_resolver import get_airport_code

SERP_API_KEY = os.getenv("SERP_API_KEY", "").strip('"').strip("'")

class SerpApiFlightProvider(FlightProvider):
    """
    Search flight options using the SerpAPI Google Flights live scraping engine.
    """
    def search_flights(self, origin: str, destination: str, start_date: str) -> List[TransitOption]:
        origin_code = get_airport_code(origin, "DEL")
        dest_code = get_airport_code(destination, "TYO")

        if not SERP_API_KEY:
            raise ValueError("[Flights Tool] Error: SERP_API_KEY is missing in the environment. Please add it to your .env file.")

        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_flights",
            "departure_id": origin_code,
            "arrival_id": dest_code,
            "outbound_date": start_date,
            "type": "2",  # 2 represents One-way flight
            "currency": "INR",
            "hl": "en",
            "api_key": SERP_API_KEY
        }

        attempts = 3
        data = None
        for attempt in range(attempts):
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                break
            except Exception as e:
                print(f"[Flights Tool] SerpAPI Attempt {attempt + 1} failed: {e}.")
                if attempt < attempts - 1:
                    import time
                    time.sleep(1)
                    continue
                print(f"[Flights Tool] Failed to query flights from {origin} to {destination} via SerpAPI: {e}.")
                return []

        best_flights = data.get("best_flights", [])
        transit_options = []
        for i, flight_group in enumerate(best_flights[:2]):
            flights = flight_group.get("flights", [])
            if not flights:
                continue
                
            flight_start = flights[0]
            flight_end = flights[-1]
            price = flight_group.get("price")
            duration = flight_group.get("total_duration")
            
            if not price or not duration:
                continue
                
            transit_options.append(
                TransitOption(
                    id=f"flight_serp_{i+1}",
                    origin=f"{flight_start.get('departure_airport', {}).get('name', origin)} ({flight_start.get('departure_airport', {}).get('id', origin_code)})",
                    destination=f"{flight_end.get('arrival_airport', {}).get('name', destination)} ({flight_end.get('arrival_airport', {}).get('id', dest_code)})",
                    departure_time=flight_start.get("departure_airport", {}).get("time", "12:00"),
                    arrival_time=flight_end.get("arrival_airport", {}).get("time", "18:00"),
                    mode=TravelMode.FLIGHT,
                    duration_minutes=int(duration),
                    estimated_price=int(price),
                    carrier=flight_start.get("airline", "Airline")
                )
            )
        return transit_options
