from typing import List, Dict
from src.graph.state import FullItinerary, TransitOption
from src.agents.helpers.pathfinder import find_transit_path

def run_itinerary_guardrails(
    full_itinerary: FullItinerary,
    day_to_dest: Dict[int, str],
    transit_options: List[TransitOption]
) -> List[str]:
    validation_warnings = []
    total_days = full_itinerary.duration_days
    
    for day_number in range(2, total_days + 1):
        prev_dest = day_to_dest[day_number - 1]
        curr_dest = day_to_dest[day_number]
        if prev_dest != curr_dest:
            path = find_transit_path(prev_dest, curr_dest, transit_options)
            if not path:
                validation_warnings.append(
                    f"No direct or multi-hop transit path resolved between {prev_dest} and {curr_dest}. "
                    "Consider self-driving or hiring a local cab."
                )

    for opt in transit_options:
        if opt.duration_minutes > 300:
            validation_warnings.append(
                f"Transit segment from {opt.origin} to {opt.destination} has a long travel duration "
                f"({opt.duration_minutes // 60} hours)."
            )
            
    return validation_warnings
