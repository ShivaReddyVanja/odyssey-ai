import uuid
import json
import asyncio
from typing import Dict, Any, List, Optional, Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from langgraph.types import Command
from src.agents.workflow import build_workflow
from src.graph.state import FullItinerary
from src.utils.logger import session_logger

# Initialize FastAPI App
app = FastAPI(
    title="OdysseyAI API",
    description="Real-time SSE backend for LangGraph Multi-Agent Travel Planner Engine",
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
    return {"status": "healthy", "service": "OdysseyAI API"}


@app.post("/api/plan/run")
async def run_planner(request: RunRequest):
    """
    Initializes a new travel planning session or starts a run on a thread.
    Returns a Server-Sent Events (SSE) streaming response of agent reasoning logs.
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

    async def event_generator():
        # Register a log queue for this thread_id
        queue = session_logger.register(thread_id)
        
        # Start graph execution in a background task
        task = asyncio.create_task(workflow_app.ainvoke(initial_input, config=config))
        
        try:
            # Yield log events in real-time while the graph is executing
            while not task.done():
                try:
                    # Wait up to 0.1 seconds for new messages or events
                    item = await asyncio.wait_for(queue.get(), timeout=0.1)
                    if isinstance(item, dict):
                        yield f"data: {json.dumps(item)}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'log', 'message': item})}\n\n"
                except asyncio.TimeoutError:
                    pass

            # Drain any remaining logs/events in the queue
            while not queue.empty():
                item = queue.get_nowait()
                if isinstance(item, dict):
                    yield f"data: {json.dumps(item)}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'log', 'message': item})}\n\n"

            # Check if the execution failed
            if task.exception():
                err = task.exception()
                yield f"data: {json.dumps({'type': 'error', 'message': f'Graph execution failed: {str(err)}'})}\n\n"
                return

            # Check post-run state checkpoints
            thread_state = workflow_app.get_state(config)
            tasks = thread_state.tasks
            has_interrupts = len(tasks) > 0 and len(tasks[0].interrupts) > 0

            if has_interrupts:
                questions = tasks[0].interrupts[0].value
                yield f"data: {json.dumps({'type': 'interrupt', 'thread_id': thread_id, 'questions': questions})}\n\n"
            else:
                values = thread_state.values
                itinerary = values.get("final_itinerary")
                yield f"data: {json.dumps({
                    'type': 'completed',
                    'thread_id': thread_id,
                    'itinerary': itinerary.model_dump() if itinerary else None,
                    'validation_warnings': values.get('validation_warnings', [])
                }, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Streaming server error: {str(e)}'})}\n\n"
        finally:
            # Unregister queue to clean up resources
            session_logger.unregister(thread_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/plan/resume")
async def resume_planner(request: ResumeRequest):
    """
    Resumes a suspended thread by submitting the user's answers to the clarifying questions.
    Returns a Server-Sent Events (SSE) streaming response of remaining agent reasoning logs.
    """
    config = {"configurable": {"thread_id": request.thread_id}}
    
    # Verify the thread exists and is actually interrupted
    thread_state = workflow_app.get_state(config)
    if not thread_state.values:
        raise HTTPException(status_code=404, detail=f"Session with thread_id '{request.thread_id}' not found.")
        
    tasks = thread_state.tasks
    if not (len(tasks) > 0 and len(tasks[0].interrupts) > 0):
        raise HTTPException(status_code=400, detail="The specified session is not in an interrupted state.")

    async def event_generator():
        # Register a log queue for this thread_id
        queue = session_logger.register(request.thread_id)
        
        # Start graph resumption in a background task
        task = asyncio.create_task(workflow_app.ainvoke(Command(resume=request.answers), config=config))
        
        try:
            # Yield log events in real-time while the graph is resuming
            while not task.done():
                try:
                    # Wait up to 0.1 seconds for new messages or events
                    item = await asyncio.wait_for(queue.get(), timeout=0.1)
                    if isinstance(item, dict):
                        yield f"data: {json.dumps(item)}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'log', 'message': item})}\n\n"
                except asyncio.TimeoutError:
                    pass

            # Drain any remaining logs/events in the queue
            while not queue.empty():
                item = queue.get_nowait()
                if isinstance(item, dict):
                    yield f"data: {json.dumps(item)}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'log', 'message': item})}\n\n"

            # Check if the execution failed
            if task.exception():
                err = task.exception()
                yield f"data: {json.dumps({'type': 'error', 'message': f'Failed to resume graph: {str(err)}'})}\n\n"
                return

            # Check post-resume state checkpoints
            new_state = workflow_app.get_state(config)
            new_tasks = new_state.tasks
            
            if len(new_tasks) > 0 and len(new_tasks[0].interrupts) > 0:
                questions = new_tasks[0].interrupts[0].value
                yield f"data: {json.dumps({'type': 'interrupt', 'thread_id': request.thread_id, 'questions': questions})}\n\n"
            else:
                values = new_state.values
                itinerary = values.get("final_itinerary")
                yield f"data: {json.dumps({
                    'type': 'completed',
                    'thread_id': request.thread_id,
                    'itinerary': itinerary.model_dump() if itinerary else None,
                    'validation_warnings': values.get('validation_warnings', [])
                }, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Streaming server error: {str(e)}'})}\n\n"
        finally:
            session_logger.unregister(request.thread_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

