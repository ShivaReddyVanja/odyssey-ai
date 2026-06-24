import os
import requests
from typing import List
from src.graph.state import Place, Location, PlaceCategory
from src.tools.geocoding import geocode_city

# Load key from .env (cleaned from quotes)
GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS", "").strip('"').strip("'")

def query_google_places(
    lat: float,
    lng: float,
    text_query: str,
    category: PlaceCategory,
    limit: int = 5
) -> List[Place]:
    """
    Queries Google Places API (New) for places near the given coordinates.
    Raises ValueError or RuntimeError on configuration/API errors.
    """
    if not GOOGLE_MAPS_KEY:
        raise ValueError("[Google Places Tool] Error: GOOGLE_MAPS API key is missing in the environment. Please add it to your .env file.")

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_KEY,
        # Restrict returned fields to optimize costs and retrieve needed data
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.priceLevel,places.editorialSummary,places.photos"
    }
    
    payload = {
        "textQuery": text_query,
        "locationBias": {
            "circle": {
                "center": {
                    "latitude": lat,
                    "longitude": lng
                },
                "radius": 5000.0  # 5 km search radius
            }
        },
        "maxResultCount": limit
    }

    attempts = 3
    results = []
    
    for attempt in range(attempts):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            results = response.json().get("places", [])
            break
        except Exception as e:
            print(f"[Google Places Tool] Attempt {attempt + 1} failed: {e}.")
            if attempt < attempts - 1:
                import time
                time.sleep(1)
                continue
            raise RuntimeError(f"[Google Places Tool] Failed after {attempts} attempts. Last error: {e}") from e
        
    places = []
    for r in results:
        display_name = r.get("displayName", {}).get("text", "Unknown Place")
        location_coords = r.get("location", {})
        latitude = location_coords.get("latitude", lat)
        longitude = location_coords.get("longitude", lng)
        
        # Map Google's price levels to a cost estimate number (1 to 4)
        price_level = r.get("priceLevel", "")
        cost_estimate = 2.0  # default to moderate
        if "INEXPENSIVE" in price_level:
            cost_estimate = 1.0
        elif "MODERATE" in price_level:
            cost_estimate = 2.0
        elif "EXPENSIVE" in price_level:
            cost_estimate = 3.0
        elif "VERY_EXPENSIVE" in price_level:
            cost_estimate = 4.0
            
        # Get editorial description if available, fallback to display name
        description = r.get("editorialSummary", {}).get("text", f"A local {category.value} recommendation: {display_name}.")

        # Extract the first photo's media URL if available
        photos = r.get("photos", [])
        photo_url = None
        if photos:
            photo_name = photos[0].get("name")
            if photo_name:
                photo_url = f"https://places.googleapis.com/v1/{photo_name}/media?key={GOOGLE_MAPS_KEY}&maxHeightPx=400"

        places.append(
            Place(
                id=r.get("id"),
                name=display_name,
                category=category,
                location=Location(
                    name=display_name,
                    address=r.get("formattedAddress", "Address unavailable"),
                    latitude=latitude,
                    longitude=longitude
                ),
                rating=r.get("rating"),  # Google ratings are out of 5.0 (no conversion needed)
                cost_estimate=cost_estimate,
                description=description,
                photo_url=photo_url
            )
        )
    return places


def search_food(destination: str, travel_styles: List[str], limit: int = 12) -> List[Place]:
    """
    Resolves destination coordinates and fetches real restaurants/cafes from Google Places.
    Raises errors on failure or if no results are found.
    """
    coords = geocode_city(destination)
    lat, lng = coords
    query_str = f"top restaurants cafe in {destination}"
    if travel_styles:
        query_str += f" specializing in {', '.join(travel_styles)}"
        
    places = query_google_places(lat, lng, query_str, PlaceCategory.FOOD, limit=limit)
    if not places:
        raise RuntimeError(f"No dining options found for '{destination}' near coordinate ({lat}, {lng}) from Google Places API.")
    return places

def search_activities(destination: str, travel_styles: List[str], limit: int = 12) -> List[Place]:
    """
    Resolves destination coordinates and fetches tourist attractions/sights from Google Places.
    Raises errors on failure or if no results are found.
    """
    coords = geocode_city(destination)
    lat, lng = coords
    query_str = f"tourist attractions sights things to do in {destination}"
    if travel_styles:
        query_str += f" for {', '.join(travel_styles)}"
        
    places = query_google_places(lat, lng, query_str, PlaceCategory.SIGHTSEEING, limit=limit)
    if not places:
        raise RuntimeError(f"No sightseeing activities found for '{destination}' near coordinate ({lat}, {lng}) from Google Places API.")
    return places
