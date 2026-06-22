import os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from src.graph.state import AgentState, DestinationAllocation
from src.agents.base import generate_structured_output
from src.agents.prompts import PLANNER_SYSTEM_PROMPT
from langchain_core.runnables import RunnableConfig
from src.utils.logger import log_agent, log_dev, emit_event
from src.tools.search_helper import google_search_snippets

# 1. Output Schemas for the Planner ReAct step
class SearchAction(BaseModel):
    query: str = Field(..., description="The Google Search query to run to check route distances, popular cities, or travel times.")

class FinalPlanning(BaseModel):
    ordered_destinations: List[DestinationAllocation] = Field(..., description="The chronologically ordered sequence of destinations/cities to visit with allocated days.")
    theme: str = Field(..., description="A refined adventure/travel theme matching the user's prompt.")
    explanation: str = Field(..., description="A short explanation of why this multi-destination selection fits the user's requirements.")

class PlannerStep(BaseModel):
    reasoning: str = Field(..., description="Internal detailed reasoning and thought process on what facts are needed or how to sequence the travel plan.")
    agent_log: str = Field(..., description="A friendly, conversational update (1 sentence) for the user describing what you are doing or thinking right now (e.g. 'Checking if Dharamshala is a good fit for spiritual retreats...').")
    action: Optional[SearchAction] = Field(None, description="Provide this if you need to run a Google search to verify routing, airport details, or destinations.")
    final_plan: Optional[FinalPlanning] = Field(None, description="Provide this ONLY when you are satisfied and have all the information required to build the final plan.")

def planner_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Planner Node:
    - Analyzes regional prompts (e.g. 'North India' or 'Kerala') and travel themes.
    - Executes an iterative ReAct search loop (up to 5 iterations) to lookup candidate spots,
      travel routes, and geographical sequences.
    - Once satisfied, returns the ordered list of specific destinations and allocated days.
    """
    emit_event(config, {"type": "node_start", "node": "planner"})
    params = state.get("parsed_parameters", {})
    destination = params.get("destination", "")
    duration_days = params.get("duration_days", 3)
    theme = params.get("theme", "")
    style = params.get("travel_style", [])

    log_agent(config, "Determining the best routing and destination breakdown...")
    log_dev(config, f"[Planner Agent] Starting planning node for region: '{destination}' ({duration_days} days, theme: {theme})...")

    # If it's a specific single city (e.g. Paris, Goa, Delhi, Tokyo, Rome, etc.), bypass the search loop
    # and directly allocate the entire duration to that single destination.
    # We do a quick check on major known cities or if the word 'state', 'region', 'country', 'north', 'south', 'east', 'west' is not present.
    # However, to be robust, we let the LLM make this determination in its first reasoning turn.
    
    search_history = []
    
    for iteration in range(10):
        log_dev(config, f"[Planner Agent] ReAct Loop Iteration {iteration + 1}/10...")
        
        # 1. Build context from search history
        history_context = ""
        if search_history:
            history_context = "\nSearch History & Context gathered so far:\n"
            for idx, h in enumerate(search_history):
                # Truncate search snippets to avoid overflowing context window
                snippet_preview = h["result"][:1000] if h["result"] else "No search results returned."
                history_context += f"--- Search Query {idx+1}: '{h['query']}' ---\n{snippet_preview}\n\n"

        # 2. Call LLM for the current reasoning step
        user_prompt = (
            f"User requested a {duration_days}-day trip to '{destination}' with theme '{theme}' and styles: {style}.\n"
            f"{history_context}"
            f"Decide whether you need to run a Google search to find specific cities/routes/times, or if you can compile the final plan now."
        )

        import time
        llm_start = time.perf_counter()
        try:
            step = generate_structured_output(
                system_prompt=PLANNER_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                output_schema=PlannerStep
            )
            log_dur = time.perf_counter() - llm_start
            log_dev(config, f"[Latency Metric] Planner ReAct step LLM call: {log_dur:.2f}s")
        except Exception as e:
            log_dev(config, f"[Planner Agent] LLM generation failed: {e}. Falling back to default single destination.")
            break

        log_dev(config, f"[Planner Agent] Reasoning: {step.reasoning}")
        if step.agent_log:
            log_agent(config, f"💭 {step.agent_log}")

        # 3. Handle Google Search Action
        if step.action and not step.final_plan:
            query = step.action.query
            log_dev(config, f"[Planner Agent] Action: Querying Google Search for: '{query}'...")
            import time
            search_start = time.perf_counter()
            search_results = google_search_snippets(query)
            search_dur = time.perf_counter() - search_start
            log_dev(config, f"[Latency Metric] Google search query: {search_dur:.2f}s")
            search_history.append({
                "query": query,
                "result": search_results
            })
            continue

        # 4. Handle Finalizing the Plan
        if step.final_plan:
            plan = step.final_plan
            # Verify that the allocated duration sums up to the user's duration_days
            total_allocated = sum(dest.duration_days for dest in plan.ordered_destinations)
            if total_allocated != duration_days:
                log_dev(config, f"[Planner Agent] Warning: LLM allocated {total_allocated} days but user requested {duration_days} days. Adjusting the last destination to fit.")
                # Automatically adjust the last destination's duration to satisfy the constraint
                diff = duration_days - sum(dest.duration_days for dest in plan.ordered_destinations[:-1])
                if len(plan.ordered_destinations) > 0:
                    plan.ordered_destinations[-1].duration_days = max(1, diff)

            # Format the output beautifully as a premium card
            route_lines = []
            for dest in plan.ordered_destinations:
                route_lines.append(f"🗺️  {dest.destination} ({dest.duration_days} days)")
            route_str = "\n".join(route_lines)
            
            final_card = (
                f"📍 ROUTE DECIDED!\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{route_str}\n"
                f"✨ Vibe: {plan.theme or theme}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Why this fits:\n"
                f"{plan.explanation}"
            )
            log_agent(config, final_card)
            
            log_dev(config, f"[Planner Agent] Planning Finalized! Destinations: {[d.destination for d in plan.ordered_destinations]} (Total Days: {duration_days})")
            log_dev(config, f"[Planner Agent] Explanation: {plan.explanation}")
            
            # Emit a structured event for the client
            emit_event(config, {
                "type": "planner_finalized",
                "destinations": [dest.model_dump() if hasattr(dest, "model_dump") else dest for dest in plan.ordered_destinations],
                "theme": plan.theme,
                "explanation": plan.explanation
            })
            
            # Update the theme in parsed parameters if a refined one is suggested
            refined_params = {**params}
            if plan.theme:
                refined_params["theme"] = plan.theme

            emit_event(config, {"type": "node_end", "node": "planner"})
            return {
                "planned_destinations": plan.ordered_destinations,
                "parsed_parameters": refined_params
            }

    final_card = (
        f"📍 ROUTE DECIDED!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🗺️  {destination} ({duration_days} days)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Defaulting to a single destination plan."
    )
    log_agent(config, final_card)
    
    log_dev(config, f"[Planner Agent] ReAct loop completed without final plan. Defaulting to single destination: '{destination}'")
    default_allocations = [DestinationAllocation(destination=destination, duration_days=duration_days)]
    
    emit_event(config, {
        "type": "planner_finalized",
        "destinations": [{"destination": destination, "duration_days": duration_days}],
        "theme": "Single Destination Exploration",
        "explanation": "Defaulted to single destination plan."
    })
    
    emit_event(config, {"type": "node_end", "node": "planner"})
    return {
        "planned_destinations": default_allocations
    }
