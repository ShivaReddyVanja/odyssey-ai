from typing import Dict, Any
from src.graph.state import AgentState
from src.tools.places import search_activities

from langchain_core.runnables import RunnableConfig
from src.utils.logger import log_agent

def sightseeing_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Sightseeing Agent Node:
    Loops over all planned destinations and gathers candidate sightseeing options for each city.
    """
    params = state.get("parsed_parameters", {})
    styles = params.get("travel_style", [])
    planned_dests = state.get("planned_destinations", [])
    
    if not planned_dests:
        destination = params.get("destination", "")
        log_agent(config, f"[Sightseeing Agent] Warning: No planned_destinations. Searching activities in {destination}...")
        activity_options = search_activities(destination, styles)
        return {"activities": activity_options}
        
    activity_options = []
    log_agent(config, f"[Sightseeing Agent] Searching activity options across planned destinations: {[d.destination for d in planned_dests]}...")
    for alloc in planned_dests:
        dest = alloc.destination
        log_agent(config, f"[Sightseeing Agent] Searching activities in: {dest}...")
        acts = search_activities(dest, styles)
        if acts:
            activity_options.extend(acts)
            
    return {
        "activities": activity_options
    }
