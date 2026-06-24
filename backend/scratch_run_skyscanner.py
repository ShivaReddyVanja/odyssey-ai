import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

token = os.getenv("APIFY_API_TOKEN", "").strip('"').strip("'")
print(f"Apify Token: {token[:10]}...")

def test_search_airport(city_name: str):
    url = f"https://api.apify.com/v2/actors/9Fn6MQ3FlBxgimMwW/run-sync-get-dataset-items?token={token}"
    payload = {
        "requests": [
            {
                "endpoint": "searchAirport",
                "query": city_name
            }
        ]
    }
    try:
        print(f"Querying searchAirport for '{city_name}'...")
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        items = response.json()
        print(f"Response Items count: {len(items)}")
        if items:
            first = items[0]
            print(f"Keys in first item: {list(first.keys())}")
            # Log first few characters or nested structure
            import json
            print(json.dumps(first, indent=2)[:1000])
            
            # Let's see how our parser resolves it
            sky_id = None
            entity_id = None
            for item in items:
                data = item.get("data", [])
                if isinstance(data, list) and len(data) > 0:
                    sky_id = data[0].get("skyId")
                    entity_id = data[0].get("entityId")
                    break
                if "skyId" in item and "entityId" in item:
                    sky_id = item.get("skyId")
                    entity_id = item.get("entityId")
                    break
            print(f"Parsed skyId: {sky_id}, entityId: {entity_id}")
    except Exception as e:
        print(f"Error: {e}")

test_search_airport("Goa")
