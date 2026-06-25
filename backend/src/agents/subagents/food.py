from typing import Dict, Any
from src.graph.state import AgentState
from src.tools.places import search_food

from langchain_core.runnables import RunnableConfig
from src.utils.logger import log_agent, log_dev, emit_event

def food_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Food Agent Node:
    Loops over all planned destinations and gathers candidate dining and cafe options for each city.
    """
    from collections import defaultdict

    emit_event(config, {"type": "node_start", "node": "food"})
    params = state.get("parsed_parameters", {})
    styles = params.get("travel_style", [])
    planned_dests = state.get("planned_destinations", [])
    
    if not planned_dests:
        destination = params.get("destination", "")
        duration_days = params.get("duration_days", 3) or 3
        limit = max(12, duration_days * 2 + 4)
        log_agent(config, f"I'm sourcing dining options in {destination}...")
        log_dev(config, f"[Food Agent] Warning: No planned_destinations. Searching dining in {destination}...")
        import time
        start_time = time.perf_counter()
        emit_event(config, {"type": "api_call", "tool": "Google Places"})
        food_options = search_food(destination, styles, limit=limit)
        dur = time.perf_counter() - start_time
        log_dev(config, f"[Latency Metric] Food Agent dining search in {destination}: {dur:.2f}s")
        
        if food_options:
            emit_event(config, {
                "type": "food_finalized",
                "selections": [opt.model_dump() for opt in food_options]
            })

        emit_event(config, {
            "type": "candidates_discovered",
            "category": "food",
            "candidates": [opt.model_dump() for opt in food_options]
        })
        emit_event(config, {"type": "node_end", "node": "food"})
        return {"food": food_options}
        
    food_options = []
    log_agent(config, "I'm finding dining and culinary options...")
    log_dev(config, f"[Food Agent] Searching dining options across planned destinations: {[d.destination for d in planned_dests]}...")
    
    grouped_food = defaultdict(list)
    for alloc in planned_dests:
        dest = alloc.destination
        limit = max(12, alloc.duration_days * 2 + 4)
        log_agent(config, f"I'm sourcing dining options in {dest}...")
        log_dev(config, f"[Food Agent] Searching dining in: {dest}...")
        import time
        start_time = time.perf_counter()
        emit_event(config, {"type": "api_call", "tool": "Google Places"})
        spots = search_food(dest, styles, limit=limit)
        dur = time.perf_counter() - start_time
        log_dev(config, f"[Latency Metric] Food Agent dining search in {dest}: {dur:.2f}s")
        
        if spots:
            food_options.extend(spots)
            grouped_food[dest].extend(spots)
            
    if food_options:
        emit_event(config, {
            "type": "food_finalized",
            "selections": [opt.model_dump() for opt in food_options]
        })
            
    emit_event(config, {
        "type": "candidates_discovered",
        "category": "food",
        "candidates": [opt.model_dump() for opt in food_options]
    })
    emit_event(config, {"type": "node_end", "node": "food"})
    return {
        "food": food_options
    }
