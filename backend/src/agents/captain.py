from typing import Dict, Any, List
import asyncio
import time
from datetime import datetime, timedelta
from langchain_core.runnables import RunnableConfig

from src.graph.state import AgentState, FullItinerary
from src.utils.logger import log_agent, log_dev, emit_event

# Modular Helpers
from src.agents.helpers.date_utils import get_next_date
from src.agents.helpers.scheduler import group_candidates_by_destination, compile_day_plans
from src.agents.helpers.validator import run_itinerary_guardrails
from src.agents.helpers.budget import calculate_and_emit_budget

async def captain_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Captain Node:
    - If any candidate lists (transit, accommodation, food, activities) are empty, 
      this is a pass-through node for step-by-step routing.
    - If all candidates are gathered, programmatically builds the FullItinerary 
      data structure using modular helper utilities, verifying budget and guardrails.
    """
    emit_event(config, {"type": "node_start", "node": "captain"})
    node_start = time.perf_counter()
    
    transit_options = state.get("transit", [])
    accommodation_options = state.get("accommodation", [])
    food_options = state.get("food", [])
    activity_options = state.get("activities", [])
    planned_destinations = state.get("planned_destinations", [])
    parsed_params = state.get("parsed_parameters", {})
    origin = parsed_params.get("origin", "Delhi")
    
    # 1. Check if we have gathered all candidates. If not, pass through.
    if not (transit_options and accommodation_options and food_options and activity_options):
        log_dev(config, "[Captain Orchestrator] Candidates are still being gathered. Routing to next subagent.")
        emit_event(config, {"type": "node_end", "node": "captain"})
        return {}
        
    log_agent(config, "All data is gathered — I'm building your day-by-day itinerary.")
    log_dev(config, "[Captain Orchestrator] All candidates gathered. Building itinerary programmatically...")

    # 2. Generate Conversational Thinking Logs Programmatically
    modes = list(set(opt.mode.value for opt in transit_options))
    modes_str = " and ".join(modes) if modes else "transit"
    hotel_names = [h.name for h in accommodation_options[:2]]
    act_names = [a.name for a in activity_options[:2]]
    food_names = [f.name for f in food_options[:2]]

    log_agent(config, f"I'm selecting the most efficient {modes_str} connections across your route.")
    await asyncio.sleep(0.5)
    log_agent(config, f"I'm shortlisting stays at {', '.join(hotel_names)} for your nights.")
    await asyncio.sleep(0.5)
    log_agent(config, f"I'm planning visits to {', '.join(act_names)} with dining at {', '.join(food_names)}.")
    await asyncio.sleep(0.5)
    
    log_agent(config, "I'm assembling and validating your day-by-day schedule.")

    # 3. Build Day-to-Destination Mapping
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

    # 4. Group Candidates by Destination (Precision Matching)
    unique_dests = list(set(day_to_dest.values()))
    matches = group_candidates_by_destination(
        unique_dests, accommodation_options, food_options, activity_options
    )

    # 5. Build DayPlan schedules (incorporating transition flights/drives, activities/dining)
    start_date = parsed_params.get("start_date", "")
    if not start_date or not isinstance(start_date, str) or len(start_date.strip()) < 10:
        start_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    reconstructed_days = compile_day_plans(
        total_days=total_days,
        start_date=start_date,
        day_to_dest=day_to_dest,
        matches=matches,
        transit_options=transit_options,
        origin=origin
    )

    # 6. Compile Final Itinerary
    theme = parsed_params.get("theme") or f"Exploration of {', '.join(set(day_to_dest.values()))}"
    destination_title = parsed_params.get("destination") or list(set(day_to_dest.values()))[0]
    
    full_itinerary = FullItinerary(
        destination=destination_title,
        duration_days=total_days,
        theme=theme,
        start_date=start_date,
        days=reconstructed_days
    )

    # 7. Run Guardrail warnings
    validation_warnings = run_itinerary_guardrails(
        full_itinerary=full_itinerary,
        day_to_dest=day_to_dest,
        transit_options=transit_options
    )

    # 8. Calculate and emit budget summary
    calculate_and_emit_budget(
        config=config,
        full_itinerary=full_itinerary,
        parsed_params=parsed_params
    )

    node_dur = time.perf_counter() - node_start
    log_dev(config, f"[Captain Orchestrator] Total Captain Node Latency: {node_dur:.2f}s")
    log_agent(config, "I've compiled your itinerary.")
    log_dev(config, "[Captain Orchestrator] Final compilation and guardrail verification successful!")
    
    emit_event(config, {"type": "node_end", "node": "captain"})
    return {
        "final_itinerary": full_itinerary,
        "validation_warnings": validation_warnings
    }