from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from src.graph.state import AgentState
from src.agents.base import generate_structured_output
from src.agents.prompts import GATEKEEPER_SYSTEM_PROMPT
from langgraph.types import interrupt

from langchain_core.runnables import RunnableConfig
from src.utils.logger import log_agent

# Pydantic schema for structured output extraction
class GatekeeperExtraction(BaseModel):
    origin: Optional[str] = Field(None, description="Starting city or airport code of the traveler")
    destination: Optional[str] = Field(None, description="Target travel city/region")
    duration_days: Optional[int] = Field(None, description="Number of days for the trip")
    theme: Optional[str] = Field(None, description="Overall theme (e.g. food trip, historical tour)")
    start_date: Optional[str] = Field(None, description="Expected start date or year/season (e.g. 2026-06-20)")
    budget_level: Optional[str] = Field(None, description="Natural language budget constraints or range, e.g. '14-20k' or 'up to 15k, buffer 2k'")
    travel_style: List[str] = Field(default_factory=list, description="List of preferences/tags")
    
    is_validated: bool = Field(..., description="True if all mandatory parameters are present, False otherwise")
    clarification_questions: List[str] = Field(
        default_factory=list, 
        description="Clarifying questions to ask if critical parameters (destination or duration) are missing"
    )

def gatekeeper_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Gatekeeper Node:
    1. Extracts trip details from user_prompt and clarification_response.
    2. If validation fails, calls interrupt() to pause the graph and ask clarifying questions.
    3. When resumed, merges the user's answers and loops back to re-evaluate.
    4. Returns updates to the AgentState once validated.
    """
    # Initialize local copy of clarification responses from state
    clarification_response = dict(state.get("clarification_response", {}))
    user_prompt_base = state.get("user_prompt", "")
    
    # 1. Fetch current date
    current_date = datetime.now().strftime("%Y-%m-%d")
    system_prompt = GATEKEEPER_SYSTEM_PROMPT.format(current_date=current_date)
    
    while True:
        log_agent(config, f"[Gatekeeper Node Execution] Checking validation... Active responses: {clarification_response}")
        
        # 2. Format the clarification responses string
        if clarification_response:
            clarification_responses_str = "\n".join(
                f"Q: {q}\nA: {a}" for q, a in clarification_response.items()
            )
        else:
            clarification_responses_str = "None"
            
        # 3. Format user prompt
        user_prompt = (
            f"Initial User Prompt: {user_prompt_base}\n"
            f"Clarification Responses:\n{clarification_responses_str}"
        )
        
        # 4. Invoke Gemini with Gatekeeper extraction schema
        extraction = generate_structured_output(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=GatekeeperExtraction
        )
        
        # 5. If validated, compile parameters and break loop to proceed to Captain
        if extraction.is_validated:
            log_agent(config, "[Gatekeeper Node Execution] Validation Successful! Routing to Captain.")
            # 5. Prepare parsed parameters for state updates
            parsed_params = {
                "origin": extraction.origin,
                "destination": extraction.destination,
                "duration_days": extraction.duration_days,
                "theme": extraction.theme,
                "start_date": extraction.start_date,
                "budget_level": extraction.budget_level,
                "travel_style": extraction.travel_style
            }
            return {
                "parsed_parameters": parsed_params,
                "is_validated": True,
                "clarification_questions": [],
                "clarification_response": clarification_response
            }
            
        # 6. If validation fails, trigger LangGraph interrupt to pause execution.
        # This halts execution and returns the list of questions to the caller.
        # When the graph is resumed, `interrupt()` returns the user's answers.
        log_agent(config, f"[Gatekeeper Node Execution] Validation Failed. Pausing graph to ask: {extraction.clarification_questions}")
        user_answers = interrupt(extraction.clarification_questions)
        
        # 7. Merge the user responses (dictionary: {question: answer}) and repeat loop
        log_agent(config, f"[Gatekeeper Node Execution] Resumed. Received user answers: {user_answers}")
        clarification_response.update(user_answers)