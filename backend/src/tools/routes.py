import os
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv(override=True)

GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS", "").strip('"').strip("'")

def get_route_directions(
    origin: str,
    destination: str,
    mode: str = "driving"
) -> Dict[str, Any]:
    """
    Queries Google Directions API for travel duration, distance, and polyline.
    Modes supported: driving, walking, bicycling, transit.
    """
    if not GOOGLE_MAPS_KEY:
        print("[Routes Tool] Warning: GOOGLE_MAPS key missing. Returning mock segment.")
        return get_mock_route_segment(origin, destination, mode)

    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "key": GOOGLE_MAPS_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK" and data.get("routes"):
            route = data["routes"][0]
            leg = route["legs"][0]
            
            duration_minutes = leg["duration"]["value"] // 60
            distance_meters = float(leg["distance"]["value"])
            polyline = route.get("overview_polyline", {}).get("points", "")
            
            # If it's a transit route, extract public transport details (like train number)
            transit_details = None
            if mode == "transit":
                for step in leg.get("steps", []):
                    if step.get("travel_mode") == "TRANSIT" and "transit_details" in step:
                        td = step["transit_details"]
                        line = td.get("line", {})
                        transit_details = {
                            "vehicle": line.get("vehicle", {}).get("name", "Transit"),
                            "line_name": line.get("name", ""),
                            "short_name": line.get("short_name", ""), # E.g. Train number
                            "departure_stop": td.get("departure_stop", {}).get("name", ""),
                            "arrival_stop": td.get("arrival_stop", {}).get("name", ""),
                            "carrier": line.get("agencies", [{}])[0].get("name", "")
                        }
                        break  # Capture first transit leg details

            return {
                "duration_minutes": duration_minutes,
                "distance_meters": distance_meters,
                "polyline": polyline,
                "transit_details": transit_details
            }

        if data.get("status") == "ZERO_RESULTS":
            print(f"[Routes Tool] Directions API returned ZERO_RESULTS (no road route exists) for {origin} ➔ {destination}.")
            return {
                "duration_minutes": -1,
                "distance_meters": 0.0,
                "polyline": "",
                "transit_details": None,
                "no_route": True
            }
        print(f"[Routes Tool] Directions API returned status: {data.get('status')}. Using mock.")
    except Exception as e:
        print(f"[Routes Tool] Error querying Directions API: {e}. Using mock.")

    return get_mock_route_segment(origin, destination, mode)

def get_mock_route_segment(origin: str, destination: str, mode: str) -> Dict[str, Any]:
    """
    Fallback mock values for routing.
    """
    return {
        "duration_minutes": 25,
        "distance_meters": 5200.0,
        "polyline": "a~l~Fjk~uCw@e@",
        "transit_details": {
            "vehicle": "Train" if mode == "transit" else "Metro",
            "line_name": "Indian Railways Express" if mode == "transit" else "Line 1",
            "short_name": "12626" if mode == "transit" else "M1",
            "departure_stop": "NDLS Station",
            "arrival_stop": "Agra Fort",
            "carrier": "Indian Railways"
        } if mode in ["transit", "train"] else None
    }
