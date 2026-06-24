import os
import sys
import asyncio
from dotenv import load_dotenv

# Ensure the backend directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load env variables
load_dotenv(override=True)

from src.agents.subagents.travel import travel_node
from src.agents.captain import captain_node
from src.graph.state import DestinationAllocation, AgentState, Place
from src.graph.state import PlaceCategory, Location

# Helper to format output
def print_separator(title):
    print("\n" + "="*70)
    print(f" {title} ")
    print("="*70)

async def test_large_itinerary():
    print_separator("TEST CASE: Akunellikudur ➔ Delhi ➔ Lakshadweep ➔ Akunellikudur (Delhi & Lakshadweep Route)")
    
    state: AgentState = {
        "user_prompt": "Plan a trip starting from Akunellikudur on 2026-08-01 visiting Delhi (3 days), and Lakshadweep (2 days).",
        "parsed_parameters": {
            "origin": "Akunellikudur",
            "start_date": "2026-08-01",
            "travel_style": []
        },
        "clarification_questions": [],
        "clarification_response": {},
        "is_validated": False,
        "planned_destinations": [
            DestinationAllocation(destination="Delhi", duration_days=3),
            DestinationAllocation(destination="Lakshadweep", duration_days=2)
        ], 
        "transit": [],
        "accommodation": [],
        "food": [],
        "activities": [],
        "final_itinerary": None
    }
    
    class DummyConfig(dict):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.metadata = {}

    config = DummyConfig()

    print("\n[Step 1] Running travel_node...")
    travel_output = travel_node(state, config)
    transit_options = travel_output.get("transit", [])
    
    print(f"\nResolved {len(transit_options)} transit options:")
    for idx, opt in enumerate(transit_options):
        print(f"  [{idx+1}] {opt.mode.value.upper()}: {opt.origin} ➔ {opt.destination}")
        print(f"      Carrier: {opt.carrier} | Price: INR {opt.estimated_price} | Duration: {opt.duration_minutes} mins")

    # Update state
    state["transit"] = transit_options
    
    # Mock resources for all destinations
    dests = ["Delhi", "Lakshadweep"]
    state["accommodation"] = [
        Place(id=f"h_{d.lower()}", name=f"{d} Stay", category=PlaceCategory.STAY, location=Location(name=d, address=f"{d}, India", latitude=10.0, longitude=75.0), rating=4.5, cost_estimate=100.0, description=f"H_{d}")
        for d in dests
    ]
    state["food"] = [
        Place(id=f"f_{d.lower()}", name=f"{d} Food Spot", category=PlaceCategory.FOOD, location=Location(name=d, address=f"{d}, India", latitude=10.0, longitude=75.0), rating=4.5, cost_estimate=10.0, description=f"F_{d}")
        for d in dests
    ]
    state["activities"] = [
        Place(id=f"a_{d.lower()}", name=f"{d} Sight", category=PlaceCategory.SIGHTSEEING, location=Location(name=d, address=f"{d}, India", latitude=10.0, longitude=75.0), rating=4.5, cost_estimate=20.0, description=f"A_{d}")
        for d in dests
    ]

    print("\n[Step 2] Running captain_node...")
    captain_output = await captain_node(state, config)
    
    itinerary = captain_output.get("final_itinerary")
    if itinerary:
        print("\n=== Compiled Day Plans ===")
        for day in itinerary.days:
            print(f"\nDay {day.day_number} ({day.date}):")
            for item in day.schedule:
                if item.type == "transit":
                    print(f"  • [Transit] {item.mode.value.upper()}: {item.origin} ➔ {item.destination} ({item.duration_minutes} mins)")
                else:
                    print(f"  • [{item.category.value.upper()}] {item.name}")
        
        print("\nValidation Warnings:")
        print(captain_output.get("validation_warnings", []))
    else:
        print("\nError: Captain node failed to compile the itinerary!")

async def main():
    await test_large_itinerary()

if __name__ == "__main__":
    asyncio.run(main())
