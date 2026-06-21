from typing import Dict, Any, List
from datetime import datetime, timedelta
from src.graph.state import AgentState, TransitOption
from src.tools.flights import search_transit

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

from langchain_core.runnables import RunnableConfig
from src.utils.logger import log_agent, log_dev, emit_event

def travel_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Travel Agent Node:
    Loops over the planned destinations list and fetches transit candidates for each segment of the journey
    (e.g., Origin -> Destination 1 -> Destination 2 -> Origin).
    """
    emit_event(config, {"type": "node_start", "node": "travel"})
    params = state.get("parsed_parameters", {})
    origin = params.get("origin", "Delhi")
    start_date = params.get("start_date", "")
    planned_dests = state.get("planned_destinations", [])
    
    if not planned_dests:
        destination = params.get("destination", "")
        log_agent(config, f"Finding flight options from {origin} to {destination}...")
        log_dev(config, f"[Travel Agent] Warning: No planned_destinations. Searching single transit options from {origin} to {destination}...")
        import time
        start_time = time.perf_counter()
        transit_options = search_transit(origin, destination, start_date)
        dur = time.perf_counter() - start_time
        log_dev(config, f"[Latency Metric] Travel Agent flight search ({origin} -> {destination}): {dur:.2f}s")
        if transit_options:
            log_agent(config, "Discovered travel options:")
            for opt in transit_options:
                price_str = f"₹{int(opt.estimated_price):,}" if opt.estimated_price else "Price unavailable"
                log_agent(config, f"  • {opt.carrier}: {opt.origin} -> {opt.destination} ({opt.departure_time} - {price_str})")
        emit_event(config, {
            "type": "candidates_discovered",
            "category": "transit",
            "candidates": [opt.model_dump() for opt in transit_options]
        })
        emit_event(config, {"type": "node_end", "node": "travel"})
        return {"transit": transit_options}
        
    transit_options = []
    current_origin = origin
    current_date = start_date
    
    log_agent(config, "Finding flight options and connections...")
    log_dev(config, f"[Travel Agent] Building transit chain for destinations: {[d.destination for d in planned_dests]} starting on {start_date}...")
    
    # 1. Query transit for all forward hops in the route
    for alloc in planned_dests:
        dest = alloc.destination
        days = alloc.duration_days
        
        log_dev(config, f"[Travel Agent] Hop: {current_origin} -> {dest} (Date: {current_date or 'default'})")
        import time
        start_time = time.perf_counter()
        options = search_transit(current_origin, dest, current_date)
        dur = time.perf_counter() - start_time
        log_dev(config, f"[Latency Metric] Travel Agent flight search ({current_origin} -> {dest}): {dur:.2f}s")
        if options:
            transit_options.extend(options)
            
        current_origin = dest
        current_date = get_next_date(current_date, days)
        
    # 2. Query return transit back to starting origin
    log_dev(config, f"[Travel Agent] Hop (Return): {current_origin} -> {origin} (Date: {current_date or 'default'})")
    import time
    start_time = time.perf_counter()
    return_options = search_transit(current_origin, origin, current_date)
    dur = time.perf_counter() - start_time
    log_dev(config, f"[Latency Metric] Travel Agent flight search ({current_origin} -> {origin}): {dur:.2f}s")
    if return_options:
        transit_options.extend(return_options)
        
    if transit_options:
        log_agent(config, "Discovered travel options:")
        for opt in transit_options:
            price_str = f"₹{int(opt.estimated_price):,}" if opt.estimated_price else "Price unavailable"
            log_agent(config, f"  • {opt.carrier}: {opt.origin} -> {opt.destination} ({opt.departure_time} - {price_str})")
            
    emit_event(config, {
        "type": "candidates_discovered",
        "category": "transit",
        "candidates": [opt.model_dump() for opt in transit_options]
    })
    emit_event(config, {"type": "node_end", "node": "travel"})
    return {
        "transit": transit_options
    }
