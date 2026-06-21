from typing import Dict, Any, List
from pydantic import BaseModel, Field
from src.graph.state import AgentState, FullItinerary
from src.agents.base import generate_structured_output
from src.agents.prompts import (
    CAPTAIN_MASTER_SYSTEM_PROMPT,
    CAPTAIN_COMPILATION_SUB_PROMPT
)

from langchain_core.runnables import RunnableConfig
from src.utils.logger import log_agent

# Output schema for Captain compilation
class CaptainCompilationOutput(BaseModel):
    itinerary: FullItinerary
    validation_warnings: List[str] = Field(
        default_factory=list,
        description="Any warnings regarding transit distances, times, or closed venue hours"
    )

def captain_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Captain Node:
    - If any candidate lists (transit, accommodation, food, activities) are empty, 
      this is a pass-through node for step-by-step routing.
    - If all candidates are gathered, executes Phase 5: compiles the final 
      FullItinerary and double-checks travel logistics/guardrails.
    """
    transit_options = state.get("transit", [])
    accommodation_options = state.get("accommodation", [])
    food_options = state.get("food", [])
    activity_options = state.get("activities", [])
    
    # Check if we have gathered all candidates. If not, pass through.
    if not (transit_options and accommodation_options and food_options and activity_options):
        log_agent(config, "[Captain Orchestrator] Candidates are still being gathered. Routing to next subagent.")
        return {}
        
    log_agent(config, "[Captain Orchestrator] All candidates gathered. Initiating Phase 5: Itinerary Compilation...")
    log_agent(config, "[Captain Orchestrator] Compiling final itinerary structure and verifying guardrails (this can take 30-60 seconds)...")
    
    # 1. Format workspace details
    parsed_params = state.get("parsed_parameters", {})
    completed_phases = (
        "Phase 1 (Transit Selection): Complete. "
        "Phase 2 (Accommodation Selection): Complete. "
        "Phase 3 (Culinary Planning): Complete. "
        "Phase 4 (Sightseeing & Activities): Complete."
    )
    current_phase = "Phase 5: Final Itinerary Compilation & Guardrail Verification"
    
    # 2. Format the Master System Prompt
    system_prompt = CAPTAIN_MASTER_SYSTEM_PROMPT.format(
        parsed_parameters=str(parsed_params),
        completed_phases=completed_phases,
        current_phase=current_phase,
        sub_task_instructions=CAPTAIN_COMPILATION_SUB_PROMPT
    )
    
    # 3. Format the candidate choices for the user prompt
    # We serialize the lists to readable text so the LLM can select and sequence them
    candidates_text = (
        f"--- Transit Candidates ---\n"
        f"{[opt.model_dump() for opt in transit_options]}\n\n"
        f"--- Accommodation Candidates ---\n"
        f"{[opt.model_dump() for opt in accommodation_options]}\n\n"
        f"--- Food Candidates ---\n"
        f"{[opt.model_dump() for opt in food_options]}\n\n"
        f"--- Sightseeing/Activity Candidates ---\n"
        f"{[opt.model_dump() for opt in activity_options]}\n"
    )
    
    user_prompt = (
        f"Here are the active candidates for this phase:\n{candidates_text}\n"
        f"State Warnings (if any): {state.get('validation_warnings', [])}"
    )
    
    # 4. Invoke LLM for structured compilation
    compilation = generate_structured_output(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        output_schema=CaptainCompilationOutput
    )
    
    # 5. Return updates to state
    return {
        "final_itinerary": compilation.itinerary,
        "validation_warnings": compilation.validation_warnings
    }