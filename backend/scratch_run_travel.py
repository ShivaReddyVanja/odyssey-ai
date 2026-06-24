import os
import sys
from dotenv import load_dotenv

# Ensure the backend directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load env variables
load_dotenv(override=True)

from src.agents.subagents.travel import travel_node
from src.graph.state import DestinationAllocation, AgentState
from langchain_core.runnables import RunnableConfig

# Helper to format output
def print_separator(title):
    print("\n" + "="*60)
    print(f" {title} ")
    print("="*60)

def main():
    # 1. Setup Mock LangChain Config
    class DummyConfig(dict):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.metadata = {}

    config = DummyConfig()

    # TEST CASE 1: Single Destination (Delhi to Goa, Flight)
    print_separator("TEST CASE 1: Delhi to Goa (Single Destination, Flight)")
    state_1: AgentState = {
        "user_prompt": "Plan a trip from Delhi to Goa on 2026-08-01",
        "parsed_parameters": {
            "origin": "Delhi",
            "destination": "Goa",
            "start_date": "2026-08-01",
            "travel_style": []
        },
        "clarification_questions": [],
        "clarification_response": {},
        "is_validated": False,
        "planned_destinations": [], # Empty list to trigger single destination logic
        "transit": [],
        "accommodation": [],
        "food": [],
        "activities": [],
        "final_itinerary": None
    }
    
    print("Input State:")
    print(f"  Origin: {state_1['parsed_parameters']['origin']}")
    print(f"  Destination: {state_1['parsed_parameters']['destination']}")
    print(f"  Start Date: {state_1['parsed_parameters']['start_date']}")
    print(f"  Planned Destinations: {state_1['planned_destinations']}")
    print("\nExecuting travel_node...")
    
    try:
        result_1 = travel_node(state_1, config)
        print("\nOutput Transit Options:")
        for idx, option in enumerate(result_1.get("transit", [])):
            print(f"  [{idx+1}] {option.mode.value.upper()}: {option.origin} ➔ {option.destination}")
            print(f"      Carrier: {option.carrier}")
            print(f"      Departure: {option.departure_time} | Arrival: {option.arrival_time}")
            print(f"      Duration: {option.duration_minutes} mins | Price: INR {option.estimated_price}")
    except Exception as e:
        print(f"Error executing Test Case 1: {e}")

    # TEST CASE 2: Multi-Destination (Delhi -> Mumbai -> Jaipur -> Delhi, with road trip style for Jaipur)
    print_separator("TEST CASE 2: Delhi -> Mumbai -> Jaipur -> Delhi (Multi-Destination)")
    state_2: AgentState = {
        "user_prompt": "Trip to Mumbai and Jaipur starting 2026-08-01 from Delhi",
        "parsed_parameters": {
            "origin": "Delhi",
            "start_date": "2026-08-01",
            "travel_style": ["road trip", "driving"] # Jaipur road trip preference
        },
        "clarification_questions": [],
        "clarification_response": {},
        "is_validated": False,
        "planned_destinations": [
            DestinationAllocation(destination="Mumbai", duration_days=3),
            DestinationAllocation(destination="Jaipur", duration_days=2)
        ],
        "transit": [],
        "accommodation": [],
        "food": [],
        "activities": [],
        "final_itinerary": None
    }
    
    print("Input State:")
    print(f"  Origin: {state_2['parsed_parameters']['origin']}")
    print(f"  Start Date: {state_2['parsed_parameters']['start_date']}")
    print(f"  Travel Style: {state_2['parsed_parameters']['travel_style']}")
    print(f"  Planned Destinations: {[(d.destination, d.duration_days) for d in state_2['planned_destinations']]}")
    print("\nExecuting travel_node...")
    
    try:
        result_2 = travel_node(state_2, config)
        print("\nOutput Transit Options:")
        for idx, option in enumerate(result_2.get("transit", [])):
            print(f"  [{idx+1}] {option.mode.value.upper()}: {option.origin} ➔ {option.destination}")
            print(f"      Carrier: {option.carrier}")
            print(f"      Departure: {option.departure_time} | Arrival: {option.arrival_time}")
            print(f"      Duration: {option.duration_minutes} mins | Price: INR {option.estimated_price}")
    except Exception as e:
        print(f"Error executing Test Case 2: {e}")

if __name__ == "__main__":
    main()
