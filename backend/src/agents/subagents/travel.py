import time
from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from concurrent.futures import ThreadPoolExecutor

from src.graph.state import AgentState
from src.utils.logger import log_agent, log_dev, emit_event
from src.agents.subagents.travel_utils import get_next_date, resolve_hop_segments

def travel_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Travel Agent Node:
    Loops over the planned destinations list and fetches transit candidates for each segment of the journey.
    Supports complex sub-hop resolution (e.g. Road to nearest airport -> Flight -> Road to destination).
    Runs hop resolutions in parallel for optimal speed.
    """
    from src.graph.state import TravelMode
    
    emit_event(config, {"type": "node_start", "node": "travel"})
    params = state.get("parsed_parameters", {})
    origin = params.get("origin", "Delhi")
    start_date = params.get("start_date", "")
    planned_dests = state.get("planned_destinations", [])
    styles = params.get("travel_style", [])

    transit_options = []
    hops = []

    # Check if single destination or multi destination and compile all hops
    if not planned_dests:
        destination = params.get("destination", "")
        if destination:
            log_dev(config, f"[Travel Agent] Planning single destination: {origin} -> {destination}")
            hops.append({
                "start_city": origin,
                "end_city": destination,
                "date": start_date,
                "force_driving": False,
                "label": f"Single Destination: {origin} ➔ {destination}"
            })
    else:
        current_origin = origin
        current_date = start_date
        has_road_style = any(s.lower() in ["motorcycle riding", "motorcycle", "riding", "road trip", "driving", "car", "roadtrip"] for s in styles)
        
        log_dev(config, f"[Travel Agent] Planning multi-destination: {[d.destination for d in planned_dests]} starting on {start_date}...")
        
        # 1. Forward hops
        for i, alloc in enumerate(planned_dests):
            dest = alloc.destination
            days = alloc.duration_days
            force_driving = (i > 0 and has_road_style)
            
            hops.append({
                "start_city": current_origin,
                "end_city": dest,
                "date": current_date,
                "force_driving": force_driving,
                "label": f"Hop {i+1}: {current_origin} ➔ {dest}"
            })
            
            current_origin = dest
            current_date = get_next_date(current_date, days)
            
        # 2. Return hop
        hops.append({
            "start_city": current_origin,
            "end_city": origin,
            "date": current_date,
            "force_driving": False,
            "label": f"Hop (Return): {current_origin} ➔ {origin}"
        })

    # Resolve all hops in parallel
    if hops:
        def run_resolve_hop(hop_info):
            log_dev(config, f"[Travel Agent] Concurrent Start - {hop_info['label']} (Date: {hop_info['date'] or 'default'}, Force Driving: {hop_info['force_driving']})")
            start_time = time.perf_counter()
            res = resolve_hop_segments(
                start_city=hop_info["start_city"],
                end_city=hop_info["end_city"],
                date=hop_info["date"],
                styles=styles,
                config=config,
                force_driving=hop_info["force_driving"]
            )
            duration = time.perf_counter() - start_time
            log_dev(config, f"[Travel Agent] Concurrent Finish - {hop_info['label']} in {duration:.2f}s")
            return res

        max_workers = min(len(hops), 4)
        log_dev(config, f"[Travel Agent] Fan-out: Resolving {len(hops)} hops concurrently using {max_workers} threads...")
        start_fan_out = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # executor.map preserves the original order of the hops list
            results = list(executor.map(run_resolve_hop, hops))
            
        total_time = time.perf_counter() - start_fan_out
        log_dev(config, f"[Travel Agent] Fan-in: Completed all {len(hops)} hops in {total_time:.2f}s")
        
        for res in results:
            transit_options.extend(res)

    # 3. Emit structured transit plan event
    if transit_options:
        segments = [
            {
                "origin": opt.origin,
                "destination": opt.destination,
                "mode": opt.mode.value,
                "mode_label": "Flight" if opt.mode == TravelMode.FLIGHT else "Drive",
                "carrier": opt.carrier,
                "departure_time": opt.departure_time,
                "duration_minutes": opt.duration_minutes,
                "estimated_price": opt.estimated_price
            }
            for opt in transit_options
        ]
        hop_count = len(set((s["origin"], s["destination"]) for s in segments))
        log_agent(config, f"I've mapped out all {hop_count} travel legs for your trip.")
        
        emit_event(config, {
            "type": "transit_plan_finalized",
            "segments": segments
        })
            
    emit_event(config, {
        "type": "candidates_discovered",
        "category": "transit",
        "candidates": [opt.model_dump() for opt in transit_options]
    })
    emit_event(config, {"type": "node_end", "node": "travel"})
    return {
        "transit": transit_options
    }
