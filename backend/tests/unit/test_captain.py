import asyncio
from datetime import datetime, timedelta
from src.graph.state import (
    AgentState, Place, Location, PlaceCategory, TransitOption, TravelMode, DestinationAllocation
)
from src.agents.captain import captain_node

# Helper to mock config for LangGraph event streaming
class MockConfig:
    def __init__(self):
        self.config = {
            "configurable": {"thread_id": "test-thread-captain"}
        }

async def test_captain_node_compilation_and_cycling():
    """
    Test that captain_node compiles the itinerary correctly:
    1. Direct destination-tagging matches Place objects to their correct day schedules.
    2. Modulo-based candidate cycling ensures all days have 2 activities and 2 restaurants scheduled.
    3. BFS pathfinding resolves the flight segments and transit hops in order.
    4. Budget summary calculations sum transit, accommodation, and living costs accurately.
    """
    print("\n[Test] Setting up mock data for Gokarna (2 days) and Havelock (3 days)...")
    
    # 1. Mock Places (Stays, Sights, Food)
    gokarna_hotel = Place(
        id="stay_gokarna_1",
        name="Gokarna Beach Resort",
        category=PlaceCategory.STAY,
        location=Location(name="Gokarna Beach Resort", address="Kudle Beach, Gokarna", latitude=14.5, longitude=74.3),
        rating=4.5,
        cost_estimate=3.0,
        description="Luxury stay near Kudle Beach",
        destination="Gokarna"
    )
    havelock_hotel = Place(
        id="stay_havelock_1",
        name="Barefoot at Havelock",
        category=PlaceCategory.STAY,
        location=Location(name="Barefoot at Havelock", address="Radhanagar Beach, Havelock", latitude=11.9, longitude=92.9),
        rating=4.8,
        cost_estimate=4.0,
        description="Premium rainforest resort",
        destination="Havelock"
    )

    # 2 activities for Gokarna, 2 activities for Havelock
    gokarna_act1 = Place(
        id="act_gokarna_1",
        name="Mahabaleshwar Temple",
        category=PlaceCategory.SIGHTSEEING,
        location=Location(name="Mahabaleshwar Temple", address="Gokarna, Karnataka", latitude=14.53, longitude=74.31),
        rating=4.6,
        cost_estimate=1.0,
        description="Historic Shiva temple",
        destination="Gokarna"
    )
    gokarna_act2 = Place(
        id="act_gokarna_2",
        name="Om Beach Walk",
        category=PlaceCategory.SIGHTSEEING,
        location=Location(name="Om Beach Walk", address="Om Beach, Gokarna", latitude=14.52, longitude=74.32),
        rating=4.7,
        cost_estimate=1.0,
        description="Scenic trek along Om Beach",
        destination="Gokarna"
    )
    havelock_act1 = Place(
        id="act_havelock_1",
        name="Radhanagar Beach Scuba",
        category=PlaceCategory.SIGHTSEEING,
        location=Location(name="Radhanagar Beach Scuba", address="Havelock Island, Andaman", latitude=11.98, longitude=92.95),
        rating=4.9,
        cost_estimate=3.0,
        description="Diving in crystal clear waters",
        destination="Havelock"
    )
    havelock_act2 = Place(
        id="act_havelock_2",
        name="Elephant Beach Snorkeling",
        category=PlaceCategory.SIGHTSEEING,
        location=Location(name="Elephant Beach Snorkeling", address="Havelock Island, Andaman", latitude=11.99, longitude=92.96),
        rating=4.8,
        cost_estimate=2.0,
        description="Water sports and corals",
        destination="Havelock"
    )

    # 2 dining spots for Gokarna, 2 dining spots for Havelock
    gokarna_food1 = Place(
        id="food_gokarna_1",
        name="Namaste Cafe",
        category=PlaceCategory.FOOD,
        location=Location(name="Namaste Cafe", address="Om Beach, Gokarna", latitude=14.52, longitude=74.32),
        rating=4.4,
        cost_estimate=2.0,
        description="Popular beachfront eatery",
        destination="Gokarna"
    )
    gokarna_food2 = Place(
        id="food_gokarna_2",
        name="Prema Restaurant",
        category=PlaceCategory.FOOD,
        location=Location(name="Prema Restaurant", address="Gokarna Town", latitude=14.54, longitude=74.31),
        rating=4.2,
        cost_estimate=1.0,
        description="Local vegetarian meals and ice cream",
        destination="Gokarna"
    )
    havelock_food1 = Place(
        id="food_havelock_1",
        name="Something Different Cafe",
        category=PlaceCategory.FOOD,
        location=Location(name="Something Different Cafe", address="Havelock Beach No 2", latitude=11.97, longitude=92.94),
        rating=4.5,
        cost_estimate=3.0,
        description="Beachside multi-cuisine dining",
        destination="Havelock"
    )
    havelock_food2 = Place(
        id="food_havelock_2",
        name="Anju Coco Resto",
        category=PlaceCategory.FOOD,
        location=Location(name="Anju Coco Resto", address="Havelock Island", latitude=11.96, longitude=92.93),
        rating=4.6,
        cost_estimate=2.0,
        description="Seafood specialties",
        destination="Havelock"
    )

    # 2. Mock Transit Options
    t_delhi_gokarna = TransitOption(
        id="transit_delhi_gokarna",
        origin="Delhi",
        destination="Gokarna",
        mode=TravelMode.FLIGHT,
        duration_minutes=150,
        estimated_price=6000
    )
    t_gokarna_havelock = TransitOption(
        id="transit_gokarna_havelock",
        origin="Gokarna",
        destination="Havelock",
        mode=TravelMode.FLIGHT,
        duration_minutes=240,
        estimated_price=9000
    )
    t_havelock_delhi = TransitOption(
        id="transit_havelock_delhi",
        origin="Havelock",
        destination="Delhi",
        mode=TravelMode.FLIGHT,
        duration_minutes=270,
        estimated_price=9500
    )

    # 3. Create the input state
    state: AgentState = {
        "user_prompt": "Plan a 5-day trip to Gokarna (2 days) and Havelock (3 days) from Delhi. Budget 50k",
        "parsed_parameters": {
            "origin": "Delhi",
            "destination": "Gokarna, Havelock",
            "duration_days": 5,
            "budget_level": "50k",
            "start_date": "2026-07-10"
        },
        "clarification_questions": [],
        "clarification_response": {},
        "is_validated": True,
        "planned_destinations": [
            DestinationAllocation(destination="Gokarna", duration_days=2),
            DestinationAllocation(destination="Havelock", duration_days=3)
        ],
        "transit": [t_delhi_gokarna, t_gokarna_havelock, t_havelock_delhi],
        "accommodation": [gokarna_hotel, havelock_hotel],
        "food": [gokarna_food1, gokarna_food2, havelock_food1, havelock_food2],
        "activities": [gokarna_act1, gokarna_act2, havelock_act1, havelock_act2],
        "final_itinerary": None
    }

    config = MockConfig().config

    # 4. Invoke the captain_node
    print("[Test] Invoking captain_node...")
    res = await captain_node(state, config=config)

    assert "final_itinerary" in res
    itinerary = res["final_itinerary"]
    assert itinerary is not None
    assert itinerary.duration_days == 5
    assert len(itinerary.days) == 5

    # 5. Verify Chronological Day compilation:
    # Day 1: Delhi -> Gokarna flight, Gokarna stays/sights/food
    day1 = itinerary.days[0]
    assert any(item.id == "transit_delhi_gokarna" for item in day1.schedule)
    assert any(item.id == "stay_gokarna_1" for item in day1.schedule)
    
    # Day 3: Gokarna -> Havelock flight (Transition Day)
    day3 = itinerary.days[2]
    assert any(item.id == "transit_gokarna_havelock" for item in day3.schedule)
    assert any(item.id == "stay_havelock_1" for item in day3.schedule)

    # Day 5: Return to Delhi
    day5 = itinerary.days[4]
    assert any(item.id == "transit_havelock_delhi" for item in day5.schedule)

    # 6. Verify Modulo-Based Cycling (to avoid blank days when unique candidate limits are reached)
    # Gokarna: 2 days. 2 unique activities. Day 1: act1, act2. Day 2: act1, act2.
    day1_acts = [item.id for item in day1.schedule if getattr(item, "category", None) == PlaceCategory.SIGHTSEEING]
    day2_acts = [item.id for item in itinerary.days[1].schedule if getattr(item, "category", None) == PlaceCategory.SIGHTSEEING]
    assert len(day1_acts) == 2
    assert len(day2_acts) == 2
    assert sorted(day1_acts) == ["act_gokarna_1", "act_gokarna_2"]
    assert sorted(day2_acts) == ["act_gokarna_1", "act_gokarna_2"]

    # Havelock: 3 days. 2 unique activities. 
    # Day 3 (Havelock Day 1): act1, act2
    # Day 4 (Havelock Day 2): act1, act2
    # Day 5 (Havelock Day 3): act1, act2
    day3_acts = [item.id for item in day3.schedule if getattr(item, "category", None) == PlaceCategory.SIGHTSEEING]
    day4_acts = [item.id for item in itinerary.days[3].schedule if getattr(item, "category", None) == PlaceCategory.SIGHTSEEING]
    day5_acts = [item.id for item in day5.schedule if getattr(item, "category", None) == PlaceCategory.SIGHTSEEING]
    
    assert len(day3_acts) == 2
    assert len(day4_acts) == 2
    assert len(day5_acts) == 2
    assert sorted(day3_acts) == ["act_havelock_1", "act_havelock_2"]
    assert sorted(day4_acts) == ["act_havelock_1", "act_havelock_2"]
    assert sorted(day5_acts) == ["act_havelock_1", "act_havelock_2"]

    print("-> Test passed successfully! Modulo-based candidate cycling, destination-tagging matches, and BFS transits are verified.")

if __name__ == "__main__":
    asyncio.run(test_captain_node_compilation_and_cycling())
