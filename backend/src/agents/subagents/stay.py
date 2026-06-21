from typing import Dict, Any
from src.graph.state import AgentState
from src.tools.hotels import search_accommodation

from langchain_core.runnables import RunnableConfig
from src.utils.logger import log_agent, log_dev, emit_event

def stay_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Stay Agent Node:
    Loops over all planned destinations and gathers candidate hotel options for each city.
    """
    emit_event(config, {"type": "node_start", "node": "stay"})
    params = state.get("parsed_parameters", {})
    budget = params.get("budget_level", "mid_range")
    planned_dests = state.get("planned_destinations", [])
    
    if not planned_dests:
        destination = params.get("destination", "")
        log_agent(config, f"Finding stay options in {destination}...")
        log_dev(config, f"[Stay Agent] Warning: No planned_destinations. Searching accommodation in {destination}...")
        import time
        start_time = time.perf_counter()
        hotel_options = search_accommodation(destination, budget)
        dur = time.perf_counter() - start_time
        log_dev(config, f"[Latency Metric] Stay Agent accommodation search in {destination}: {dur:.2f}s")
        if hotel_options:
            log_agent(config, "Discovered accommodation options:")
            for spot in hotel_options[:4]:
                rating_str = f"{spot.rating}★" if spot.rating else "No rating"
                log_agent(config, f"  • {spot.name} ({rating_str}) - {spot.location.address}")
        emit_event(config, {
            "type": "candidates_discovered",
            "category": "accommodation",
            "candidates": [opt.model_dump() for opt in hotel_options]
        })
        emit_event(config, {"type": "node_end", "node": "stay"})
        return {"accommodation": hotel_options}
        
    hotel_options = []
    log_agent(config, "Finding hotel and lodging options...")
    log_dev(config, f"[Stay Agent] Searching accommodations across planned destinations: {[d.destination for d in planned_dests]}...")
    for alloc in planned_dests:
        dest = alloc.destination
        log_dev(config, f"[Stay Agent] Searching stays in: {dest}...")
        import time
        start_time = time.perf_counter()
        hotels = search_accommodation(dest, budget)
        dur = time.perf_counter() - start_time
        log_dev(config, f"[Latency Metric] Stay Agent accommodation search in {dest}: {dur:.2f}s")
        if hotels:
            hotel_options.extend(hotels)
            
    if hotel_options:
        log_agent(config, "Discovered accommodation options:")
        for spot in hotel_options[:4]:
            rating_str = f"{spot.rating}★" if spot.rating else "No rating"
            log_agent(config, f"  • {spot.name} ({rating_str}) - {spot.location.address}")
            
    emit_event(config, {
        "type": "candidates_discovered",
        "category": "accommodation",
        "candidates": [opt.model_dump() for opt in hotel_options]
    })
    emit_event(config, {"type": "node_end", "node": "stay"})
    return {
        "accommodation": hotel_options
    }
