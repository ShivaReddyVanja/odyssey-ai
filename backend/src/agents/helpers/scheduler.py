import re
from typing import List, Dict, Any
from collections import defaultdict
from src.graph.state import Place, TransitOption, DayPlan
from src.agents.helpers.date_utils import get_next_date
from src.agents.helpers.pathfinder import find_transit_path

def is_place_for_destination(place_address: str, place_name: str, dest: str) -> bool:
    addr = place_address.lower()
    name = place_name.lower()
    d_clean = dest.lower().strip()
    
    # 1. Direct substring match
    if d_clean in addr or d_clean in name:
        return True
        
    # 2. Check individual significant words (length > 3) to handle variations
    words = [w for w in re.split(r'[^a-zA-Z0-9]+', d_clean) if len(w) > 3]
    if words and any(w in addr or w in name for w in words):
        return True
        
    return False

def group_candidates_by_destination(
    unique_dests: List[str],
    accommodation_options: List[Place],
    food_options: List[Place],
    activity_options: List[Place]
) -> Dict[str, Any]:
    dest_to_hotel = {}
    for dest in unique_dests:
        hotels_for_dest = [
            h for h in accommodation_options
            if (getattr(h, "destination", None) and h.destination.lower().strip() == dest.lower().strip())
               or is_place_for_destination(h.location.address, h.name, dest)
        ]
        # Absolute fallback to all accommodation options
        if not hotels_for_dest:
            hotels_for_dest = accommodation_options
        if hotels_for_dest:
            dest_to_hotel[dest] = hotels_for_dest[0]

    dest_activities = defaultdict(list)
    for act in activity_options:
        matched = False
        act_dest = getattr(act, "destination", None)
        if act_dest:
            for dest in unique_dests:
                if act_dest.lower().strip() == dest.lower().strip():
                    dest_activities[dest].append(act)
                    matched = True
                    break
        if not matched:
            for dest in unique_dests:
                if is_place_for_destination(act.location.address, act.name, dest):
                    dest_activities[dest].append(act)
                    matched = True
                    break
        if not matched:
            dest_activities[unique_dests[0]].append(act)

    dest_food = defaultdict(list)
    for f in food_options:
        matched = False
        f_dest = getattr(f, "destination", None)
        if f_dest:
            for dest in unique_dests:
                if f_dest.lower().strip() == dest.lower().strip():
                    dest_food[dest].append(f)
                    matched = True
                    break
        if not matched:
            for dest in unique_dests:
                if is_place_for_destination(f.location.address, f.name, dest):
                    dest_food[dest].append(f)
                    matched = True
                    break
        if not matched:
            dest_food[unique_dests[0]].append(f)

    return {
        "dest_to_hotel": dest_to_hotel,
        "dest_activities": dest_activities,
        "dest_food": dest_food
    }

def compile_day_plans(
    total_days: int,
    start_date: str,
    day_to_dest: Dict[int, str],
    matches: Dict[str, Any],
    transit_options: List[TransitOption],
    origin: str
) -> List[DayPlan]:
    dest_to_hotel = matches["dest_to_hotel"]
    dest_activities = matches["dest_activities"]
    dest_food = matches["dest_food"]

    dest_day_counters = defaultdict(int)
    reconstructed_days = []
    scheduled_place_ids = set()

    for day_number in range(1, total_days + 1):
        day_date = get_next_date(start_date, day_number - 1)
        dest = day_to_dest[day_number]
        day_schedule = []

        # A. Transit on Day 1 or Transition Day
        if day_number == 1:
            first_transits = find_transit_path(origin, dest, transit_options)
            day_schedule.extend(first_transits)
        elif day_to_dest[day_number] != day_to_dest[day_number - 1]:
            prev_dest = day_to_dest[day_number - 1]
            transition_transits = find_transit_path(prev_dest, dest, transit_options)
            day_schedule.extend(transition_transits)

        # B. Sights/Activities (Distribute 2 per day, cycle through candidates if we run out of unique ones)
        acts_list = dest_activities[dest]
        if acts_list:
            counter = dest_day_counters[dest]
            idx1 = (counter * 2) % len(acts_list)
            idx2 = (counter * 2 + 1) % len(acts_list)
            
            act1 = acts_list[idx1]
            day_schedule.append(act1)
            scheduled_place_ids.add(act1.id)
            
            if len(acts_list) > 1:
                act2 = acts_list[idx2]
                day_schedule.append(act2)
                scheduled_place_ids.add(act2.id)

        # C. Dining/Food (Distribute 2 per day, cycle through candidates if we run out of unique ones)
        food_list = dest_food[dest]
        if food_list:
            counter = dest_day_counters[dest]
            idx1 = (counter * 2) % len(food_list)
            idx2 = (counter * 2 + 1) % len(food_list)
            
            f1 = food_list[idx1]
            day_schedule.append(f1)
            scheduled_place_ids.add(f1.id)
            
            if len(food_list) > 1:
                f2 = food_list[idx2]
                day_schedule.append(f2)
                scheduled_place_ids.add(f2.id)

        # Increment day counter for the destination
        dest_day_counters[dest] += 1

        # D. Lodging / Hotel (Allowed to repeat, not added to scheduled_place_ids)
        hotel = dest_to_hotel.get(dest)
        if hotel:
            day_schedule.append(hotel)

        # E. Transit on Last Day (Return to Origin)
        if day_number == total_days:
            return_transits = find_transit_path(dest, origin, transit_options)
            day_schedule.extend(return_transits)

        reconstructed_days.append(
            DayPlan(
                day_number=day_number,
                date=day_date,
                schedule=day_schedule
            )
        )

    return reconstructed_days
