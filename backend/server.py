import uuid
from typing import Dict, Any, List, Optional, Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from langgraph.types import Command
from src.agents.workflow import build_workflow
from src.graph.state import FullItinerary

# Initialize FastAPI App
app = FastAPI(
    title="NomadGraph API",
    description="REST backend for LangGraph Multi-Agent Travel Planner Engine",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compile LangGraph Workflow once during startup
workflow_app = build_workflow()


# =================================================================
# Pydantic Schemas
# =================================================================

class RunRequest(BaseModel):
    thread_id: Optional[str] = Field(None, description="Unique session thread ID. Generated if not provided.")
    user_prompt: str = Field(..., description="User travel request query.")

class ResumeRequest(BaseModel):
    thread_id: str = Field(..., description="Existing session thread ID to resume.")
    answers: Dict[str, str] = Field(..., description="Mapping of clarifying questions to answers.")

class PlanResponse(BaseModel):
    thread_id: str
    status: Literal["interrupted", "completed", "failed"]
    questions: Optional[List[str]] = None
    itinerary: Optional[Dict[str, Any]] = None
    validation_warnings: Optional[List[str]] = None

class SessionResponse(BaseModel):
    thread_id: str
    is_validated: bool
    status: Literal["interrupted", "completed", "idle"]
    planned_destinations: List[Dict[str, Any]] = []
    itinerary: Optional[Dict[str, Any]] = None
    questions: Optional[List[str]] = None


# =================================================================
# Endpoints
# =================================================================

@app.get("/health")
def health_check():
    """Health check endpoint to verify server status."""
    return {"status": "healthy", "service": "NomadGraph API"}


@app.post("/api/plan/run", response_model=PlanResponse)
def run_planner(request: RunRequest):
    """
    Initializes a new travel planning session or starts a run on a thread.
    If the Gatekeeper node requires more information, it triggers an interrupt
    and returns the clarifying questions.
    """
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_input = {
        "user_prompt": request.user_prompt,
        "clarification_response": {},
        "is_validated": False,
        "transit": [],
        "accommodation": [],
        "food": [],
        "activities": [],
        "planned_destinations": [],
        "final_itinerary": None
    }

    try:
        # Run workflow
        workflow_app.invoke(initial_input, config=config)
        
        # Retrieve post-run state
        thread_state = workflow_app.get_state(config)
        tasks = thread_state.tasks
        
        # Check if the graph is currently suspended on an interrupt
        has_interrupts = len(tasks) > 0 and len(tasks[0].interrupts) > 0
        
        if has_interrupts:
            questions = tasks[0].interrupts[0].value
            return PlanResponse(
                thread_id=thread_id,
                status="interrupted",
                questions=questions
            )
        
        # If no interrupts, graph ran to completion
        values = thread_state.values
        itinerary = values.get("final_itinerary")
        
        return PlanResponse(
            thread_id=thread_id,
            status="completed",
            itinerary=itinerary.model_dump() if itinerary else None,
            validation_warnings=values.get("validation_warnings")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {str(e)}")


@app.post("/api/plan/resume", response_model=PlanResponse)
def resume_planner(request: ResumeRequest):
    """
    Resumes a suspended thread by submitting the user's answers to the clarifying questions.
    """
    config = {"configurable": {"thread_id": request.thread_id}}
    
    # Verify the thread exists and is actually interrupted
    thread_state = workflow_app.get_state(config)
    if not thread_state.values:
        raise HTTPException(status_code=404, detail=f"Session with thread_id '{request.thread_id}' not found.")
        
    tasks = thread_state.tasks
    if not (len(tasks) > 0 and len(tasks[0].interrupts) > 0):
        raise HTTPException(status_code=400, detail="The specified session is not in an interrupted state.")

    try:
        # Resume workflow by sending Command(resume=answers)
        workflow_app.invoke(Command(resume=request.answers), config=config)
        
        # Retrieve post-resume state
        new_state = workflow_app.get_state(config)
        new_tasks = new_state.tasks
        
        # Check if it hit another interrupt
        if len(new_tasks) > 0 and len(new_tasks[0].interrupts) > 0:
            questions = new_tasks[0].interrupts[0].value
            return PlanResponse(
                thread_id=request.thread_id,
                status="interrupted",
                questions=questions
            )
            
        # Completed execution
        values = new_state.values
        itinerary = values.get("final_itinerary")
        
        return PlanResponse(
            thread_id=request.thread_id,
            status="completed",
            itinerary=itinerary.model_dump() if itinerary else None,
            validation_warnings=values.get("validation_warnings")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resume graph: {str(e)}")


@app.get("/api/plan/session/{thread_id}", response_model=SessionResponse)
def get_session_status(thread_id: str):
    """
    Retrieves the current state and checkpoints of a session thread.
    """
    config = {"configurable": {"thread_id": thread_id}}
    thread_state = workflow_app.get_state(config)
    
    if not thread_state.values:
        raise HTTPException(status_code=404, detail=f"Session with thread_id '{thread_id}' not found.")
        
    values = thread_state.values
    tasks = thread_state.tasks
    
    # Determine status
    has_interrupts = len(tasks) > 0 and len(tasks[0].interrupts) > 0
    status = "idle"
    questions = None
    
    if has_interrupts:
        status = "interrupted"
        questions = tasks[0].interrupts[0].value
    elif values.get("final_itinerary") is not None:
        status = "completed"

    planned_dests = []
    for allocation in values.get("planned_destinations", []):
        if hasattr(allocation, "model_dump"):
            planned_dests.append(allocation.model_dump())
        else:
            planned_dests.append(allocation)

    itinerary = values.get("final_itinerary")

    return SessionResponse(
        thread_id=thread_id,
        is_validated=values.get("is_validated", False),
        status=status,
        planned_destinations=planned_dests,
        itinerary=itinerary.model_dump() if itinerary else None,
        questions=questions
    )
