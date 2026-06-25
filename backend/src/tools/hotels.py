import os
from typing import List
from src.graph.state import Place, Location, PlaceCategory
from src.tools.geocoding import geocode_city
from src.tools.places import query_google_places


def search_accommodation(destination: str, budget_level: str) -> List[Place]:
    """
    Queries Google Places API (New) for accommodations/hotels in the destination.
    Returns real hotels with accurate names and coordinates.
    Raises errors on failure or if no results are found.
    """
    coords = geocode_city(destination)
    lat, lng = coords
    
    # Construct a search query reflecting the destination and budget preference
    query_str = f"hotels resorts lodging accommodation in {destination}"
    if budget_level:
        query_str = f"{budget_level} {query_str}"
        
    print(f"[Hotels Tool] Querying Google Places for: '{query_str}' at ({lat}, {lng})...")
    places = query_google_places(lat, lng, query_str, PlaceCategory.STAY, limit=10)
    if not places:
        raise RuntimeError(f"No accommodation options found for '{destination}' near coordinate ({lat}, {lng}) from Google Places API.")
    for p in places:
        p.destination = destination
    return places
