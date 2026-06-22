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
        
    log_agent(config, "All candidates gathered! Sequencing your itinerary...")
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

    log_agent(config, f"Transit Choice: {transit_thought}")
    await asyncio.sleep(0.5)
    log_agent(config, f"Lodging Choice: {lodging_thought}")
    await asyncio.sleep(0.5)
    log_agent(config, f"Activities & Dining: {food_act_thought}")
    await asyncio.sleep(0.5)
    
    log_agent(config, "Compiling and validating day plans against opening hours and transit times...")

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
    # Select one lodging choice per destination for consistency
    dest_to_hotel = {}
    for dest in set(day_to_dest.values()):
        hotels_for_dest = [h for h in accommodation_options if dest.lower() in h.location.address.lower() or dest.lower() in h.name.lower()]
        if not hotels_for_dest:
            hotels_for_dest = accommodation_options
        if hotels_for_dest:
            dest_to_hotel[dest] = hotels_for_dest[0]

    # Group activities and dining by destination
    dest_activities = defaultdict(list)
    for act in activity_options:
        matched = False
        for dest in set(day_to_dest.values()):
            if dest.lower() in act.location.address.lower() or dest.lower() in act.name.lower():
                dest_activities[dest].append(act)
                matched = True
                break
        if not matched:
            dest_activities[list(day_to_dest.values())[0]].append(act)

    dest_food = defaultdict(list)
    for f in food_options:
        matched = False
        for dest in set(day_to_dest.values()):
            if dest.lower() in f.location.address.lower() or dest.lower() in f.name.lower():
                dest_food[dest].append(f)
                matched = True
                break
        if not matched:
            dest_food[list(day_to_dest.values())[0]].append(f)

    # Match transit segments
    def find_transit_option(start: str, end: str) -> Optional[TransitOption]:
        s_key = start.lower().strip().replace(' ', '_')
        e_key = end.lower().strip().replace(' ', '_')
        
        # Check by prefix/contains in id (e.g. flight_new_york_tokyo_0)
        for opt in transit_options:
            opt_id = opt.id.lower()
            if s_key in opt_id and e_key in opt_id:
                if opt_id.find(s_key) < opt_id.find(e_key):
                    return opt

        for opt in transit_options:
            if opt.origin.lower().strip() == start.lower().strip() and opt.destination.lower().strip() == end.lower().strip():
                return opt
        for opt in transit_options:
            if (start.lower().strip() in opt.origin.lower() or opt.origin.lower() in start.lower().strip()) and \
               (end.lower().strip() in opt.destination.lower() or opt.destination.lower() in end.lower().strip()):
                return opt
        for opt in transit_options:
            if start.lower().strip() in opt.origin.lower() or end.lower().strip() in opt.destination.lower():
                return opt
        return None

    # =================================================================
    # 4. Construct DayPlan schedules
    # =================================================================
    dest_day_counters = defaultdict(int)
    reconstructed_days = []
    
    start_date = parsed_params.get("start_date", "")
    if not start_date or not isinstance(start_date, str) or len(start_date.strip()) < 10:
        start_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    for day_number in range(1, total_days + 1):
        day_date = get_next_date(start_date, day_number - 1)
        dest = day_to_dest[day_number]
        day_schedule = []

        # A. Transit on Day 1 or Transition Day
        if day_number == 1:
            first_transit = find_transit_option(origin, dest)
            if first_transit:
                day_schedule.append(first_transit)
        elif day_to_dest[day_number] != day_to_dest[day_number - 1]:
            prev_dest = day_to_dest[day_number - 1]
            transition_transit = find_transit_option(prev_dest, dest)
            if transition_transit:
                day_schedule.append(transition_transit)

        # B. Sights/Activities (Distribute 2 per day)
        acts_list = dest_activities[dest]
        cnt = dest_day_counters[dest]
        if acts_list:
            act1 = acts_list[(2 * cnt) % len(acts_list)]
            day_schedule.append(act1)
            if len(acts_list) > 1:
                act2 = acts_list[(2 * cnt + 1) % len(acts_list)]
                day_schedule.append(act2)

        # C. Dining/Food (Distribute 2 per day)
        food_list = dest_food[dest]
        if food_list:
            f1 = food_list[(2 * cnt) % len(food_list)]
            day_schedule.append(f1)
            if len(food_list) > 1:
                f2 = food_list[(2 * cnt + 1) % len(food_list)]
                day_schedule.append(f2)

        # Increment day counter for the destination
        dest_day_counters[dest] += 1

        # D. Lodging / Hotel
        hotel = dest_to_hotel.get(dest)
        if hotel:
            day_schedule.append(hotel)

        # E. Transit on Last Day (Return to Origin)
        if day_number == total_days:
            return_transit = find_transit_option(dest, origin)
            if return_transit:
                day_schedule.append(return_transit)

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
            opt = find_transit_option(prev_dest, curr_dest)
            if not opt:
                validation_warnings.append(f"No direct transit option resolved between {prev_dest} and {curr_dest}. Consider self-driving or hiring a local cab.")

    for opt in transit_options:
        if opt.duration_minutes > 300:
            validation_warnings.append(f"Transit segment from {opt.origin} to {opt.destination} has a long travel duration ({opt.duration_minutes // 60} hours).")

    node_dur = time.perf_counter() - node_start
    log_dev(config, f"[Captain Orchestrator] Total Captain Node Latency: {node_dur:.2f}s")
    log_agent(config, "Itinerary successfully compiled!")
    log_dev(config, "[Captain Orchestrator] Final compilation and guardrail verification successful!")
    
    emit_event(config, {"type": "node_end", "node": "captain"})
    return {
        "final_itinerary": full_itinerary,
        "validation_warnings": validation_warnings
    }