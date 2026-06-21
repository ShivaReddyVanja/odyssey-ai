from typing import Dict, Any
from src.graph.state import AgentState
from src.tools.places import search_activities

from langchain_core.runnables import RunnableConfig
from src.utils.logger import log_agent, log_dev, emit_event

def sightseeing_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Sightseeing Agent Node:
    Loops over all planned destinations and gathers candidate sightseeing options for each city.
    """
    emit_event(config, {"type": "node_start", "node": "sightseeing"})
    params = state.get("parsed_parameters", {})
    styles = params.get("travel_style", [])
    planned_dests = state.get("planned_destinations", [])
    
    if not planned_dests:
        destination = params.get("destination", "")
        log_agent(config, f"Finding attractions and activities in {destination}...")
        log_dev(config, f"[Sightseeing Agent] Warning: No planned_destinations. Searching activities in {destination}...")
        import time
        start_time = time.perf_counter()
        activity_options = search_activities(destination, styles)
        dur = time.perf_counter() - start_time
        log_dev(config, f"[Latency Metric] Sightseeing Agent activities search in {destination}: {dur:.2f}s")
        if activity_options:
            log_agent(config, "Discovered sightseeing and activities:")
            for spot in activity_options[:4]:
                rating_str = f"{spot.rating}★" if spot.rating else "No rating"
                log_agent(config, f"  • {spot.name} ({rating_str}) - {spot.location.address}")
        emit_event(config, {
            "type": "candidates_discovered",
            "category": "activities",
            "candidates": [opt.model_dump() for opt in activity_options]
        })
        emit_event(config, {"type": "node_end", "node": "sightseeing"})
        return {"activities": activity_options}
        
    activity_options = []
    log_agent(config, "Sourcing sightseeing spots and things to do...")
    log_dev(config, f"[Sightseeing Agent] Searching activity options across planned destinations: {[d.destination for d in planned_dests]}...")
    for alloc in planned_dests:
        dest = alloc.destination
        log_dev(config, f"[Sightseeing Agent] Searching activities in: {dest}...")
        import time
        start_time = time.perf_counter()
        acts = search_activities(dest, styles)
        dur = time.perf_counter() - start_time
        log_dev(config, f"[Latency Metric] Sightseeing Agent activities search in {dest}: {dur:.2f}s")
        if acts:
            activity_options.extend(acts)
            
    if activity_options:
        log_agent(config, "Discovered sightseeing and activities:")
        for spot in activity_options[:4]:
            rating_str = f"{spot.rating}★" if spot.rating else "No rating"
            log_agent(config, f"  • {spot.name} ({rating_str}) - {spot.location.address}")
            
    emit_event(config, {
        "type": "candidates_discovered",
        "category": "activities",
        "candidates": [opt.model_dump() for opt in activity_options]
    })
    emit_event(config, {"type": "node_end", "node": "sightseeing"})
    return {
        "activities": activity_options
    }
