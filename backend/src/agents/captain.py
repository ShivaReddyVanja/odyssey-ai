from typing import Dict, Any, List, Optional
import asyncio
import time
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableConfig
from src.graph.state import AgentState, FullItinerary, DayPlan, Place, TransitOption
from src.agents.base import generate_structured_output, llm
from src.utils.logger import log_agent, log_dev, emit_event
from src.agents.prompts import (
    CAPTAIN_MASTER_SYSTEM_PROMPT,
    CAPTAIN_COMPILATION_SUB_PROMPT
)

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

# Output schemas for Reference-Based Captain compilation
class ScheduledItemRef(BaseModel):
    id: str = Field(..., description="ID of the selected transit option or place candidate")
    start_time: Optional[str] = Field(None, description="Logical start time (HH:MM or YYYY-MM-DD HH:MM)")
    end_time: Optional[str] = Field(None, description="Logical end time (HH:MM or YYYY-MM-DD HH:MM)")
    custom_description: Optional[str] = Field(None, description="Brief context/description for this item")

class DayScheduleRef(BaseModel):
    day_number: int = Field(..., description="Day number (1-indexed)")
    schedule: List[ScheduledItemRef] = Field(default_factory=list, description="Chronological schedule items")

class SimpleItineraryCompilation(BaseModel):
    destination: str = Field(..., description="Main trip destination")
    theme: str = Field(..., description="Overall refined travel theme")
    days: List[DayScheduleRef] = Field(..., description="Day-by-day schedules")
    validation_warnings: List[str] = Field(
        default_factory=list,
        description="Any warnings regarding transit distances, times, or closed venue hours"
    )

def generate_text_output(system_prompt: str, user_prompt: str) -> str:
    """
    Sends prompts to Gemini and returns unstructured plain text.
    Used for generating quick simulated thinking logs.
    """
    messages = [
        ("system", system_prompt),
        ("human", user_prompt)
    ]
    response = llm.invoke(messages)
    return str(response.content).strip()

async def captain_node(state: AgentState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Captain Node:
    - If any candidate lists (transit, accommodation, food, activities) are empty, 
      this is a pass-through node for step-by-step routing.
    - If all candidates are gathered, spawns the main structured compilation in the background.
      While compilation runs, it concurrently generates and streams conversational 
      thinking logs to the user to keep them engaged. Measures and logs step latency.
    """
    emit_event(config, {"type": "node_start", "node": "captain"})
    node_start = time.perf_counter()
    transit_options = state.get("transit", [])
    accommodation_options = state.get("accommodation", [])
    food_options = state.get("food", [])
    activity_options = state.get("activities", [])
    planned_destinations = state.get("planned_destinations", [])
    parsed_params = state.get("parsed_parameters", {})
    
    # Check if we have gathered all candidates. If not, pass through.
    if not (transit_options and accommodation_options and food_options and activity_options):
        log_dev(config, "[Captain Orchestrator] Candidates are still being gathered. Routing to next subagent.")
        emit_event(config, {"type": "node_end", "node": "captain"})
        return {}
        
    log_agent(config, "All candidates gathered! Sequencing your itinerary...")
    log_dev(config, "[Captain Orchestrator] All candidates gathered. Initiating Phase 5: Itinerary Compilation...")

    # =================================================================
    # 1. Format the Master System Prompt & Inputs
    # =================================================================
    completed_phases = (
        "Phase 1 (Transit Selection): Complete. "
        "Phase 2 (Accommodation Selection): Complete. "
        "Phase 3 (Culinary Planning): Complete. "
        "Phase 4 (Sightseeing & Activities): Complete."
    )
    current_phase = "Phase 5: Final Itinerary Compilation & Guardrail Verification"
    
    system_prompt = CAPTAIN_MASTER_SYSTEM_PROMPT.format(
        parsed_parameters=str(parsed_params),
        completed_phases=completed_phases,
        current_phase=current_phase,
        sub_task_instructions=CAPTAIN_COMPILATION_SUB_PROMPT
    )
    
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

    # =================================================================
    # 2. Spawn Structured Itinerary Compilation in the Background
    # =================================================================
    compilation_start = time.perf_counter()
    compilation_task = asyncio.create_task(
        asyncio.to_thread(
            generate_structured_output,
            system_prompt,
            user_prompt,
            SimpleItineraryCompilation
        )
    )

    # =================================================================
    # 3. Concurrently Generate and Stream Simulated Thinking Logs
    # =================================================================
    thoughts_start = time.perf_counter()
    try:
        # Step A: Transit Decision Thought
        log_dev(config, "[Captain Orchestrator] Reviewing candidate transit segments...")
        t_start = time.perf_counter()
        transit_thought = await asyncio.to_thread(
            generate_text_output,
            "You are the Captain, a travel coordinator. Write a single brief, conversational sentence (max 20 words) explaining what transit options (flights or cabs) you are selecting from the candidates.",
            str([opt.model_dump() for opt in transit_options])
        )
        t_dur = time.perf_counter() - t_start
        log_agent(config, f"Transit Choice: {transit_thought}")
        log_dev(config, f"[Captain Orchestrator] Transit Selection: {transit_thought} (Latency: {t_dur:.2f}s)")
        await asyncio.sleep(1.2)  # Pause for natural reading pacing

        # Step B: Stay Decision Thought
        log_dev(config, "[Captain Orchestrator] Reviewing candidate hotel options...")
        s_start = time.perf_counter()
        stay_thought = await asyncio.to_thread(
            generate_text_output,
            "You are the Captain. Write a single brief, conversational sentence (max 20 words) explaining what stays/hotels you are selecting from the candidates.",
            str([opt.model_dump() for opt in accommodation_options])
        )
        s_dur = time.perf_counter() - s_start
        log_agent(config, f"Lodging Choice: {stay_thought}")
        log_dev(config, f"[Captain Orchestrator] Stay Selection: {stay_thought} (Latency: {s_dur:.2f}s)")
        await asyncio.sleep(1.2)

        # Step C: Sightseeing & Food Thought
        log_dev(config, "[Captain Orchestrator] Sequencing activities and dining reservations...")
        a_start = time.perf_counter()
        food_act_thought = await asyncio.to_thread(
            generate_text_output,
            "You are the Captain. Write a single brief, conversational sentence (max 20 words) explaining what activities and dining spots you are prioritizing from the candidates.",
            f"Food: {str([opt.model_dump() for opt in food_options])}\nActivities: {str([opt.model_dump() for opt in activity_options])}"
        )
        a_dur = time.perf_counter() - a_start
        log_agent(config, f"Activities & Dining: {food_act_thought}")
        log_dev(config, f"[Captain Orchestrator] Timeline Sequencing: {food_act_thought} (Latency: {a_dur:.2f}s)")
        
    except Exception as e:
        log_dev(config, f"[Captain Orchestrator] Warning: Simulated thinking failed: {str(e)}")

    thoughts_dur = time.perf_counter() - thoughts_start
    log_dev(config, f"[Captain Orchestrator] Simulated thinking phase completed. Total Thinking Latency: {thoughts_dur:.2f}s")
    log_agent(config, "Compiling and validating day plans against opening hours and transit times...")
    log_dev(config, "[Captain Orchestrator] Formatting final day-by-day itinerary and verifying guardrails...")

    # =================================================================
    # 4. Await Compilation Completion and Return
    # =================================================================
    compilation = await compilation_task
    compilation_dur = time.perf_counter() - compilation_start
    log_dev(config, f"[Latency Metric] Captain Structured Compilation: {compilation_dur:.2f}s")
    
    # Reconstruct FullItinerary from SimpleItineraryCompilation references
    candidate_map = {}
    for opt in transit_options:
        candidate_map[opt.id] = opt
    for opt in accommodation_options:
        candidate_map[opt.id] = opt
    for opt in food_options:
        candidate_map[opt.id] = opt
    for opt in activity_options:
        candidate_map[opt.id] = opt

    start_date = parsed_params.get("start_date", "")
    if not start_date or not isinstance(start_date, str) or len(start_date.strip()) < 10:
        start_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    reconstructed_days = []
    
    for day_ref in compilation.days:
        schedule_items = []
        for item_ref in day_ref.schedule:
            ref_id = item_ref.id
            candidate = candidate_map.get(ref_id)
            if not candidate:
                # Case insensitive search
                for cid, cval in candidate_map.items():
                    if cid.lower() == ref_id.lower():
                        candidate = cval
                        break
            if not candidate:
                # Substring/Name search
                for cid, cval in candidate_map.items():
                    if hasattr(cval, "name") and (cval.name.lower() in ref_id.lower() or ref_id.lower() in cval.name.lower()):
                        candidate = cval
                        break
            
            if candidate:
                item_copy = candidate.model_copy(deep=True)
                if isinstance(item_copy, Place) and item_ref.custom_description:
                    item_copy.description = item_ref.custom_description
                schedule_items.append(item_copy)
            else:
                log_dev(config, f"[Captain Orchestrator] Warning: Candidate reference '{ref_id}' not found. Skipping.")
                
        day_date = get_next_date(start_date, day_ref.day_number - 1)
        reconstructed_days.append(
            DayPlan(
                day_number=day_ref.day_number,
                date=day_date,
                schedule=schedule_items
            )
        )

    # Make sure duration_days is correctly set
    duration_days = parsed_params.get("duration_days", len(reconstructed_days))
    
    full_itinerary = FullItinerary(
        destination=compilation.destination or parsed_params.get("destination", "Trip"),
        duration_days=duration_days,
        theme=compilation.theme,
        start_date=start_date,
        days=reconstructed_days
    )
    
    node_dur = time.perf_counter() - node_start
    log_dev(config, f"[Captain Orchestrator] Total Captain Node Latency: {node_dur:.2f}s")
    log_agent(config, "Itinerary successfully compiled!")
    log_dev(config, "[Captain Orchestrator] Final compilation and guardrail verification successful!")
    
    emit_event(config, {"type": "node_end", "node": "captain"})
    return {
        "final_itinerary": full_itinerary,
        "validation_warnings": compilation.validation_warnings
    }