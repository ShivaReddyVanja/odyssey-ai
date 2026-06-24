from typing import Dict, Any, List, Optional
import asyncio
import time
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig
from src.graph.state import AgentState, FullItinerary, DayPlan, Place, TransitOption
from src.agents.base import generate_structured_output, llm
from src.utils.logger import log_agent, log_dev, emit_event
from src.agents.prompts import (
    CAPTAIN_MASTER_SYSTEM_PROMPT,
    CAPTAIN_COMPILATION_SUB_PROMPT
)

def get_next_date(date_str: str, days: int) -> str:
    """
    Safely adds days to a YYYY-MM-DD date string. Falls back to original string on error.
    """
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str.strip(), "%Y-%m-%d")
        next_dt = dt + timedelta(days=days)
        return next_dt.strftime("%Y-%m-%d")
    except Exception:
        return date_str

# Output schemas for Reference-Based Captain compilation
class ScheduledItemRef(BaseModel):
    id: str = Field(..., description="ID of the selected transit option or place candidate")
    start_time: Optional[str] = Field(None, description="Logical start time (HH:MM or YYYY-MM-DD HH:MM)")
    end_time: Optional[str] = Field(None, description="Logical end time (HH:MM or YYYY-MM-DD HH:MM)")
    custom_description: Optional[str] = Field(None, description="Brief context/description for this item")

class DayScheduleRef(BaseModel):
    day_number: int = Field(..., description="Day number (1-indexed)")
    schedule: List[ScheduledItemRef] = Field(default_factory=list, description="Chronological schedule items")

class SimpleItineraryCompilation(BaseModel):
    destination: str = Field(..., description="Main trip destination")
    theme: str = Field(..., description="Overall refined travel theme")
    days: List[DayScheduleRef] = Field(..., description="Day-by-day schedules")
    validation_warnings: List[str] = Field(
        default_factory=list,
        description="Any warnings regarding transit distances, times, or closed venue hours"
    )

def generate_text_output(system_prompt: str, user_prompt: str) -> str:
    """
    Sends prompts to Gemini and returns unstructured plain text.
    Used for generating quick simulated thinking logs.
    """
    messages = [
        ("system", system_prompt),
        ("human", user_prompt)
    ]
    response = llm.invoke(messages)
    return str(response.content).strip()

async def captain_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Captain Node:
    - If any candidate lists (transit, accommodation, food, activities) are empty, 
      this is a pass-through node for step-by-step routing.
    - If all candidates are gathered, programmatically builds the FullItinerary 
      data structure to avoid the latency and cost of a final LLM compilation call.
    """
    from collections import defaultdict
    
    emit_event(config, {"type": "node_start", "node": "captain"})
    node_start = time.perf_counter()
    
    transit_options = state.get("transit", [])
    accommodation_options = state.get("accommodation", [])
    food_options = state.get("food", [])
    activity_options = state.get("activities", [])
    planned_destinations = state.get("planned_destinations", [])
    parsed_params = state.get("parsed_parameters", {})
    origin = parsed_params.get("origin", "Delhi")
    
    # Check if we have gathered all candidates. If not, pass through.
    if not (transit_options and accommodation_options and food_options and activity_options):
        log_dev(config, "[Captain Orchestrator] Candidates are still being gathered. Routing to next subagent.")
        emit_event(config, {"type": "node_end", "node": "captain"})
        return {}
        
    log_agent(config, "All data is gathered — I'm building your day-by-day itinerary.")
    log_dev(config, "[Captain Orchestrator] All candidates gathered. Building itinerary programmatically...")

    # =================================================================
    # 1. Generate Conversational Thinking Logs Programmatically
    # =================================================================
    # Determine unique modes
    modes = list(set(opt.mode.value for opt in transit_options))
    modes_str = " and ".join(modes) if modes else "transit"
    transit_thought = f"Selecting convenient {modes_str} segments to seamlessly connect your journey."
    
    # Determine lodging choices
    hotel_names = [h.name for h in accommodation_options[:2]]
    lodging_thought = f"Staying at premium spots like {', '.join(hotel_names)} for comfort and style."
    
    # Determine activities & dining choices
    act_names = [a.name for a in activity_options[:2]]
    food_names = [f.name for f in food_options[:2]]
    food_act_thought = f"Prioritizing visits to {', '.join(act_names)} alongside dining at {', '.join(food_names)}."

    log_agent(config, f"I'm selecting the most efficient {modes_str} connections across your route.")
    await asyncio.sleep(0.5)
    log_agent(config, f"I'm shortlisting stays at {', '.join(hotel_names)} for your nights.")
    await asyncio.sleep(0.5)
    log_agent(config, f"I'm planning visits to {', '.join(act_names)} with dining at {', '.join(food_names)}.")
    await asyncio.sleep(0.5)
    
    log_agent(config, "I'm assembling and validating your day-by-day schedule.")

    # =================================================================
    # 2. Build Day-by-Day Route & Allocations
    # =================================================================
    day_to_dest = {}
    day_idx = 1
    for alloc in planned_destinations:
        for _ in range(alloc.duration_days):
            day_to_dest[day_idx] = alloc.destination
            day_idx += 1
            
    total_days = day_idx - 1
    if total_days == 0:
        dest = parsed_params.get("destination", "Destination")
        total_days = parsed_params.get("duration_days", 1) or 1
        for d in range(1, total_days + 1):
            day_to_dest[d] = dest

    # =================================================================
    # 3. Match Stays, Dining, and Sights to Destinations
    # =================================================================
    # =================================================================
    # 3. Match Stays, Dining, and Sights to Destinations
    # =================================================================
    import re
    
    unique_dests = list(set(day_to_dest.values()))

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

    # Select one lodging choice per destination for consistency
    dest_to_hotel = {}
    for dest in unique_dests:
        hotels_for_dest = [
            h for h in accommodation_options
            if is_place_for_destination(h.location.address, h.name, dest)
        ]
        # Absolute fallback to all accommodation options
        if not hotels_for_dest:
            hotels_for_dest = accommodation_options
        if hotels_for_dest:
            dest_to_hotel[dest] = hotels_for_dest[0]

    # Group activities and dining by destination
    dest_activities = defaultdict(list)
    for act in activity_options:
        matched = False
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
        for dest in unique_dests:
            if is_place_for_destination(f.location.address, f.name, dest):
                dest_food[dest].append(f)
                matched = True
                break
        if not matched:
            dest_food[unique_dests[0]].append(f)

    # Match transit segments via BFS pathfinding
    def is_city_match(node: str, city: str) -> bool:
        def normalize_city_name(name: str) -> str:
            n = name.lower().strip()
            # Replace known alias words/substrings
            replacements = {
                "madras": "chennai",
                "trivandrum": "thiruvananthapuram",
                "cochin": "kochi",
                "vasco da gama": "goa",
                "kulu": "kullu"
            }
            for old, new in replacements.items():
                n = n.replace(old, new)
            return n

        n = normalize_city_name(node)
        c = normalize_city_name(city)
        
        # 1. Direct or substring matches
        if n == c or c in n or n in c:
            return True
            
        # 2. Match using airport code extraction
        import re
        from src.tools.flights import get_airport_code, resolve_nearest_airport
        
        n_iatas = re.findall(r'\(([a-z]{3})\)', n)
        c_iatas = re.findall(r'\(([a-z]{3})\)', c)
        
        def is_primary_airport_city(city_name: str) -> bool:
            try:
                info = resolve_nearest_airport(city_name)
                # Normalize both target city and airport city for comparison
                airport_city = normalize_city_name(info.airport_city)
                target_city = normalize_city_name(city_name)
                return target_city in airport_city or airport_city in target_city
            except Exception:
                return False
        
        c_code = get_airport_code(city).lower().strip()
        if n_iatas and c_code in n_iatas and is_primary_airport_city(city):
            return True
            
        n_code = get_airport_code(node).lower().strip()
        if c_iatas and n_code in c_iatas and is_primary_airport_city(node):
            return True
            
        # 3. Clean parenthesis fallbacks
        if "(" in n:
            n_clean = n.split("(")[0].strip()
            if n_clean == c or c in n_clean or n_clean in c:
                return True
        if "(" in c:
            c_clean = c.split("(")[0].strip()
            if n == c_clean or c_clean in n or n in c_clean:
                return True
                
        return False


    def find_transit_path(start: str, end: str) -> List[TransitOption]:
        from collections import deque
        queue = deque()
        
        # Enqueue initial segments
        for opt in transit_options:
            if is_city_match(opt.origin, start):
                queue.append((opt.destination, [opt]))
                
        visited = set()
        
        while queue:
            curr_city, path = queue.popleft()
            
            if is_city_match(curr_city, end):
                return path
                
            state_key = curr_city.lower().strip()
            if state_key in visited:
                continue
            visited.add(state_key)
            
            for opt in transit_options:
                if is_city_match(opt.origin, curr_city):
                    if opt.destination.lower().strip() not in visited:
                        queue.append((opt.destination, path + [opt]))
                        
        # Fallback 1: ID prefix matches
        s_key = start.lower().strip().replace(' ', '_')
        e_key = end.lower().strip().replace(' ', '_')
        for opt in transit_options:
            opt_id = opt.id.lower()
            if s_key in opt_id and e_key in opt_id:
                if opt_id.find(s_key) < opt_id.find(e_key):
                    return [opt]
                    
        # Fallback 2: Direct match
        for opt in transit_options:
            if is_city_match(opt.origin, start) and is_city_match(opt.destination, end):
                return [opt]
                
        return []

    # =================================================================
    # 4. Construct DayPlan schedules
    # =================================================================
    dest_day_counters = defaultdict(int)
    reconstructed_days = []
    scheduled_place_ids = set()
    
    start_date = parsed_params.get("start_date", "")
    if not start_date or not isinstance(start_date, str) or len(start_date.strip()) < 10:
        start_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    for day_number in range(1, total_days + 1):
        day_date = get_next_date(start_date, day_number - 1)
        dest = day_to_dest[day_number]
        day_schedule = []

        # A. Transit on Day 1 or Transition Day
        if day_number == 1:
            first_transits = find_transit_path(origin, dest)
            day_schedule.extend(first_transits)
        elif day_to_dest[day_number] != day_to_dest[day_number - 1]:
            prev_dest = day_to_dest[day_number - 1]
            transition_transits = find_transit_path(prev_dest, dest)
            day_schedule.extend(transition_transits)

        # B. Sights/Activities (Distribute 2 per day, strictly deduplicated)
        acts_list = dest_activities[dest]
        if acts_list:
            available_acts = [a for a in acts_list if a.id not in scheduled_place_ids]
            if not available_acts:
                log_dev(config, f"[Captain Node] Warning: Out of unique sightseeing candidates for {dest}. Sightseeing spots will not be duplicated.")
            else:
                act1 = available_acts[0]
                day_schedule.append(act1)
                scheduled_place_ids.add(act1.id)
                
                if len(available_acts) > 1:
                    act2 = available_acts[1]
                    day_schedule.append(act2)
                    scheduled_place_ids.add(act2.id)

        # C. Dining/Food (Distribute 2 per day, strictly deduplicated)
        food_list = dest_food[dest]
        if food_list:
            available_food = [f for f in food_list if f.id not in scheduled_place_ids]
            if not available_food:
                log_dev(config, f"[Captain Node] Warning: Out of unique dining candidates for {dest}. Dining spots will not be duplicated.")
            else:
                f1 = available_food[0]
                day_schedule.append(f1)
                scheduled_place_ids.add(f1.id)
                
                if len(available_food) > 1:
                    f2 = available_food[1]
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
            return_transits = find_transit_path(dest, origin)
            day_schedule.extend(return_transits)

        reconstructed_days.append(
            DayPlan(
                day_number=day_number,
                date=day_date,
                schedule=day_schedule
            )
        )

    # =================================================================
    # 5. Compile Final Itinerary and Run Guardrails
    # =================================================================
    theme = parsed_params.get("theme") or f"Exploration of {', '.join(set(day_to_dest.values()))}"
    destination_title = parsed_params.get("destination") or list(set(day_to_dest.values()))[0]
    
    full_itinerary = FullItinerary(
        destination=destination_title,
        duration_days=total_days,
        theme=theme,
        start_date=start_date,
        days=reconstructed_days
    )

    # Simple validation warnings
    validation_warnings = []
    for day_number in range(2, total_days + 1):
        prev_dest = day_to_dest[day_number - 1]
        curr_dest = day_to_dest[day_number]
        if prev_dest != curr_dest:
            path = find_transit_path(prev_dest, curr_dest)
            if not path:
                validation_warnings.append(f"No direct or multi-hop transit path resolved between {prev_dest} and {curr_dest}. Consider self-driving or hiring a local cab.")

    for opt in transit_options:
        if opt.duration_minutes > 300:
            validation_warnings.append(f"Transit segment from {opt.origin} to {opt.destination} has a long travel duration ({opt.duration_minutes // 60} hours).")

    # Calculate budget details from the compiled itinerary
    transit_cost = sum(
        item.estimated_price
        for day in full_itinerary.days
        for item in day.schedule
        if item.type == "transit" and getattr(item, "estimated_price", None)
    )
    accommodation_cost = sum(
        item.cost_estimate
        for day in full_itinerary.days
        for item in day.schedule
        if item.type == "place" and getattr(item, "category", None) == "stay" and getattr(item, "cost_estimate", None)
    )
    food_activities_cost = sum(
        item.cost_estimate
        for day in full_itinerary.days
        for item in day.schedule
        if item.type == "place" and getattr(item, "category", None) in ("food", "sightseeing") and getattr(item, "cost_estimate", None)
    )
    total_estimated = transit_cost + accommodation_cost + food_activities_cost

    import re
    def parse_budget_level_to_inr(budget_str: str) -> Optional[float]:
        if not budget_str:
            return None
        s = budget_str.lower().strip()
        has_k = 'k' in s
        has_lakh = 'lakh' in s or 'lac' in s
        
        raw_nums = re.findall(r'\b\d+(?:\.\d+)?\b', s)
        if not raw_nums:
            raw_nums = re.findall(r'\d+(?:\.\d+)?', s)
            
        if not raw_nums:
            return None
            
        numbers = []
        for num_str in raw_nums:
            try:
                val = float(num_str)
                if val < 1000 and has_k:
                    val *= 1000
                elif val < 100 and has_lakh:
                    val *= 100000
                numbers.append(val)
            except ValueError:
                continue
                
        if not numbers:
            return None
            
        if len(numbers) == 1:
            return numbers[0]
        return sum(numbers) / len(numbers)

    user_budget = parsed_params.get("budget_level", "")
    parsed_val = parse_budget_level_to_inr(user_budget)
    
    if parsed_val is not None:
        if total_estimated <= parsed_val:
            verdict = "within_budget"
            message = f"Estimated trip cost is INR {total_estimated:,.0f} — within your stated budget."
        else:
            verdict = "over_budget"
            message = f"Estimated trip cost is INR {total_estimated:,.0f} — slightly over your budget. Consider reviewing accommodation."
    else:
        verdict = "approximate"
        budget_label = user_budget if user_budget else "mid-range"
        budget_label_clean = budget_label.replace("_", "-").replace(" ", "-")
        message = f"Estimated trip cost is INR {total_estimated:,.0f}, consistent with a {budget_label_clean} budget."

    emit_event(config, {
        "type": "budget_summary",
        "total_estimated_inr": int(total_estimated),
        "transit_cost_inr": int(transit_cost),
        "accommodation_cost_inr": int(accommodation_cost),
        "food_activities_cost_inr": int(food_activities_cost),
        "living_cost_inr": int(accommodation_cost + food_activities_cost),
        "user_budget_raw": user_budget,
        "verdict": verdict,
        "message": message
    })

    node_dur = time.perf_counter() - node_start
    log_dev(config, f"[Captain Orchestrator] Total Captain Node Latency: {node_dur:.2f}s")
    log_agent(config, "I've compiled your itinerary.")
    log_dev(config, "[Captain Orchestrator] Final compilation and guardrail verification successful!")
    
    emit_event(config, {"type": "node_end", "node": "captain"})
    return {
        "final_itinerary": full_itinerary,
        "validation_warnings": validation_warnings
    }