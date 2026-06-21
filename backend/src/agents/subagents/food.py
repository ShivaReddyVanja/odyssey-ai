from typing import Dict, Any
from src.graph.state import AgentState
from src.tools.places import search_food

from langchain_core.runnables import RunnableConfig
from src.utils.logger import log_agent

def food_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Food Agent Node:
    Loops over all planned destinations and gathers candidate dining and cafe options for each city.
    """
    params = state.get("parsed_parameters", {})
    styles = params.get("travel_style", [])
    planned_dests = state.get("planned_destinations", [])
    
    if not planned_dests:
        destination = params.get("destination", "")
        log_agent(config, f"[Food Agent] Warning: No planned_destinations. Searching dining in {destination}...")
        food_options = search_food(destination, styles)
        return {"food": food_options}
        
    food_options = []
    log_agent(config, f"[Food Agent] Searching dining options across planned destinations: {[d.destination for d in planned_dests]}...")
    for alloc in planned_dests:
        dest = alloc.destination
        log_agent(config, f"[Food Agent] Searching dining in: {dest}...")
        spots = search_food(dest, styles)
        if spots:
            food_options.extend(spots)
            
    return {
        "food": food_options
    }
