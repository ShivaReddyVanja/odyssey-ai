import re
from typing import Optional
from langchain_core.runnables import RunnableConfig
from src.graph.state import FullItinerary
from src.utils.logger import emit_event

def parse_budget_level_to_inr(budget_str: str) -> Optional[float]:
    if not budget_str:
        return None
    s = budget_str.lower().strip()
    has_k = 'k' in s
    has_lakh = 'lakh' in s or 'lac' in s
    
    raw_nums = re.findall(r'\b\d+(?:\.\d+)?\b', s)
    if not raw_nums:
        raw_nums = re.findall(r'\d+(?:\.\d+)?', s)
        
    if not raw_nums:
        return None
        
    numbers = []
    for num_str in raw_nums:
        try:
            val = float(num_str)
            if val < 1000 and has_k:
                val *= 1000
            elif val < 100 and has_lakh:
                val *= 100000
            numbers.append(val)
        except ValueError:
            continue
            
    if not numbers:
        return None
        
    if len(numbers) == 1:
        return numbers[0]
    return sum(numbers) / len(numbers)

def calculate_and_emit_budget(config: RunnableConfig, full_itinerary: FullItinerary, parsed_params: dict):
    transit_cost = sum(
        item.estimated_price
        for day in full_itinerary.days
        for item in day.schedule
        if item.type == "transit" and getattr(item, "estimated_price", None)
    )
    accommodation_cost = sum(
        item.cost_estimate
        for day in full_itinerary.days
        for item in day.schedule
        if item.type == "place" and getattr(item, "category", None) == "stay" and getattr(item, "cost_estimate", None)
    )
    food_activities_cost = sum(
        item.cost_estimate
        for day in full_itinerary.days
        for item in day.schedule
        if item.type == "place" and getattr(item, "category", None) in ("food", "sightseeing") and getattr(item, "cost_estimate", None)
    )
    total_estimated = transit_cost + accommodation_cost + food_activities_cost

    user_budget = parsed_params.get("budget_level", "")
    parsed_val = parse_budget_level_to_inr(user_budget)
    
    if parsed_val is not None:
        if total_estimated <= parsed_val:
            verdict = "within_budget"
            message = f"Estimated trip cost is INR {total_estimated:,.0f} — within your stated budget."
        else:
            verdict = "over_budget"
            message = f"Estimated trip cost is INR {total_estimated:,.0f} — slightly over your budget. Consider reviewing accommodation."
    else:
        verdict = "approximate"
        budget_label = user_budget if user_budget else "mid-range"
        budget_label_clean = budget_label.replace("_", "-").replace(" ", "-")
        message = f"Estimated trip cost is INR {total_estimated:,.0f}, consistent with a {budget_label_clean} budget."

    emit_event(config, {
        "type": "budget_summary",
        "total_estimated_inr": int(total_estimated),
        "transit_cost_inr": int(transit_cost),
        "accommodation_cost_inr": int(accommodation_cost),
        "food_activities_cost_inr": int(food_activities_cost),
        "living_cost_inr": int(accommodation_cost + food_activities_cost),
        "user_budget_raw": user_budget,
        "verdict": verdict,
        "message": message
    })
