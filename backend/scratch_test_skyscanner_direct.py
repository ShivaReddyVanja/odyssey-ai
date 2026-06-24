import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

token = os.getenv("APIFY_API_TOKEN", "").strip('"').strip("'")
print(f"Apify Token: {token[:10]}...")

def test_direct_flight_search():
    url = f"https://api.apify.com/v2/actors/9Fn6MQ3FlBxgimMwW/run-sync-get-dataset-items?token={token}"
    
    # Let's test passing IATA codes directly as both SkyId and EntityId
    payload = {
        "requests": [
            {
                "endpoint": "searchFlights",
                "originSkyId": "GOI",
                "destinationSkyId": "COK",
                "originEntityId": "GOI",
                "destinationEntityId": "COK",
                "date": "2026-08-04",
                "currency": "INR",
                "market": "IN"
            }
        ]
    }
    try:
        print("Querying searchFlights directly with GOI/COK as both skyId and entityId...")
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        items = response.json()
        print(f"Response Items count: {len(items)}")
        if items:
            first = items[0]
            print(f"Status: {first.get('status')}")
            if first.get("status") == "error":
                print(f"Error: {first.get('error')}")
            else:
                # Log success details
                print("Success! Flights found.")
                itineraries = first.get("itineraries", [])
                print(f"Found {len(itineraries)} itineraries.")
                if itineraries:
                    print(f"Sample price: {itineraries[0].get('price', {}).get('formatted')}")
    except Exception as e:
        print(f"Request failed: {e}")

test_direct_flight_search()
