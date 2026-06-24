import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS", "").strip('"').strip("'")

def get_country_via_geocoding(city_name: str):
    if not GOOGLE_MAPS_KEY:
        print("GOOGLE_MAPS key is missing!")
        return None
        
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": city_name,
        "key": GOOGLE_MAPS_KEY
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"Status: {data.get('status')}")
        if data.get("status") == "OK" and data.get("results"):
            result = data["results"][0]
            print(f"Formatted Address: {result.get('formatted_address')}")
            for component in result.get("address_components", []):
                if "country" in component.get("types", []):
                    return component.get("long_name")
    except Exception as e:
        print(f"Error: {e}")
    return None

cities = ["Gokarna", "Nagarkurnool", "Paris", "New York"]
for city in cities:
    country = get_country_via_geocoding(city)
    print(f"City: {city} -> Country: {country}\n")
