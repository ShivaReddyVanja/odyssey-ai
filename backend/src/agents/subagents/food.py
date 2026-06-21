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
    emit_event(config, {"type": "node_start", "node": "food"})
    params = state.get("parsed_parameters", {})
    styles = params.get("travel_style", [])
    planned_dests = state.get("planned_destinations", [])
    
    if not planned_dests:
        destination = params.get("destination", "")
        log_agent(config, f"Finding dining and culinary options in {destination}...")
        log_dev(config, f"[Food Agent] Warning: No planned_destinations. Searching dining in {destination}...")
        import time
        start_time = time.perf_counter()
        food_options = search_food(destination, styles)
        dur = time.perf_counter() - start_time
        log_dev(config, f"[Latency Metric] Food Agent dining search in {destination}: {dur:.2f}s")
        if food_options:
            log_agent(config, "Discovered dining options:")
            for spot in food_options[:4]:
                rating_str = f"{spot.rating}★" if spot.rating else "No rating"
                log_agent(config, f"  • {spot.name} ({rating_str}) - {spot.location.address}")
        emit_event(config, {
            "type": "candidates_discovered",
            "category": "food",
            "candidates": [opt.model_dump() for opt in food_options]
        })
        emit_event(config, {"type": "node_end", "node": "food"})
        return {"food": food_options}
        
    food_options = []
    log_agent(config, "Sourcing dining options and local cuisines...")
    log_dev(config, f"[Food Agent] Searching dining options across planned destinations: {[d.destination for d in planned_dests]}...")
    for alloc in planned_dests:
        dest = alloc.destination
        log_dev(config, f"[Food Agent] Searching dining in: {dest}...")
        import time
        start_time = time.perf_counter()
        spots = search_food(dest, styles)
        dur = time.perf_counter() - start_time
        log_dev(config, f"[Latency Metric] Food Agent dining search in {dest}: {dur:.2f}s")
        if spots:
            food_options.extend(spots)
            
    if food_options:
        log_agent(config, "Discovered dining options:")
        for spot in food_options[:4]:
            rating_str = f"{spot.rating}★" if spot.rating else "No rating"
            log_agent(config, f"  • {spot.name} ({rating_str}) - {spot.location.address}")
            
    emit_event(config, {
        "type": "candidates_discovered",
        "category": "food",
        "candidates": [opt.model_dump() for opt in food_options]
    })
    emit_event(config, {"type": "node_end", "node": "food"})
    return {
        "food": food_options
    }
