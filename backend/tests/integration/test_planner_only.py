import uuid
import json
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver

# Import schemas and nodes from the codebase
from src.graph.state import AgentState
from src.agents.gatekeeper import gatekeeper_node
from src.agents.planner import planner_node
from src.agents.workflow import check_gatekeeper_status
from src.utils.logger import session_logger

# =================================================================
# 1. Build a Test Workflow that terminates after the Planner node
# =================================================================

from src.agents.subagents import travel_node, stay_node, food_node, sightseeing_node

def build_test_workflow():
    workflow = StateGraph(AgentState)
    
    # Add Gatekeeper, Planner, Travel, Stay, Food, and Sightseeing nodes
    workflow.add_node("gatekeeper", gatekeeper_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("travel", travel_node)
    workflow.add_node("stay", stay_node)
    workflow.add_node("food", food_node)
    workflow.add_node("sightseeing", sightseeing_node)
    
    # Start at gatekeeper
    workflow.set_entry_point("gatekeeper")
    
    # Route to planner on success, or END on interrupt
    workflow.add_conditional_edges(
        "gatekeeper",
        check_gatekeeper_status,
        {
            "planner": "planner",
            END: END
        }
    )
    
    # Route to Travel after Planner, then stay, food, and sightseeing
    workflow.add_edge("planner", "travel")
    workflow.add_edge("travel", "stay")
    workflow.add_edge("stay", "food")
    workflow.add_edge("food", "sightseeing")
    workflow.add_edge("sightseeing", END)
    
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

test_workflow_app = build_test_workflow()

# =================================================================
# 2. Setup a Mock FastAPI App with SSE Endpoints (like server.py)
# =================================================================

app = FastAPI(title="OdysseyAI Planner Test API")

class RunRequest(BaseModel):
    thread_id: Optional[str] = None
    user_prompt: str

class ResumeRequest(BaseModel):
    thread_id: str
    answers: Dict[str, str]

@app.post("/api/plan/run")
async def run_planner(request: RunRequest):
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
        queue = session_logger.register(thread_id)
        task = asyncio.create_task(test_workflow_app.ainvoke(initial_input, config=config))
        
        try:
            while not task.done():
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=0.1)
                    if isinstance(item, dict):
                        yield f"data: {json.dumps(item)}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'log', 'message': item})}\n\n"
                except asyncio.TimeoutError:
                    pass
            
            while not queue.empty():
                item = queue.get_nowait()
                if isinstance(item, dict):
                    yield f"data: {json.dumps(item)}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'log', 'message': item})}\n\n"
                    
            if task.exception():
                err = task.exception()
                yield f"data: {json.dumps({'type': 'error', 'message': f'Execution failed: {str(err)}'})}\n\n"
                return
                
            thread_state = test_workflow_app.get_state(config)
            tasks = thread_state.tasks
            has_interrupts = len(tasks) > 0 and len(tasks[0].interrupts) > 0
            
            if has_interrupts:
                questions = tasks[0].interrupts[0].value
                yield f"data: {json.dumps({'type': 'interrupt', 'thread_id': thread_id, 'questions': questions})}\n\n"
            else:
                values = thread_state.values
                # We return the planned destinations (which is the output of the planner)
                planned_dests = []
                for alloc in values.get("planned_destinations", []):
                    planned_dests.append(alloc.model_dump() if hasattr(alloc, "model_dump") else alloc)
                yield f"data: {json.dumps({
                    'type': 'completed',
                    'thread_id': thread_id,
                    'planned_destinations': planned_dests,
                    'theme': values.get("parsed_parameters", {}).get("theme", "")
                }, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Server error: {str(e)}'})}\n\n"
        finally:
            session_logger.unregister(thread_id)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/plan/resume")
async def resume_planner(request: ResumeRequest):
    config = {"configurable": {"thread_id": request.thread_id}}
    
    async def event_generator():
        queue = session_logger.register(request.thread_id)
        task = asyncio.create_task(test_workflow_app.ainvoke(Command(resume=request.answers), config=config))
        
        try:
            while not task.done():
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=0.1)
                    if isinstance(item, dict):
                        yield f"data: {json.dumps(item)}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'log', 'message': item})}\n\n"
                except asyncio.TimeoutError:
                    pass
            
            while not queue.empty():
                item = queue.get_nowait()
                if isinstance(item, dict):
                    yield f"data: {json.dumps(item)}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'log', 'message': item})}\n\n"
                    
            if task.exception():
                err = task.exception()
                yield f"data: {json.dumps({'type': 'error', 'message': f'Resumption failed: {str(err)}'})}\n\n"
                return
                
            new_state = test_workflow_app.get_state(config)
            new_tasks = new_state.tasks
            
            if len(new_tasks) > 0 and len(new_tasks[0].interrupts) > 0:
                questions = new_tasks[0].interrupts[0].value
                yield f"data: {json.dumps({'type': 'interrupt', 'thread_id': request.thread_id, 'questions': questions})}\n\n"
            else:
                values = new_state.values
                planned_dests = []
                for alloc in values.get("planned_destinations", []):
                    planned_dests.append(alloc.model_dump() if hasattr(alloc, "model_dump") else alloc)
                yield f"data: {json.dumps({
                    'type': 'completed',
                    'thread_id': request.thread_id,
                    'planned_destinations': planned_dests,
                    'theme': values.get("parsed_parameters", {}).get("theme", "")
                }, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Server error: {str(e)}'})}\n\n"
        finally:
            session_logger.unregister(request.thread_id)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# =================================================================
# 3. Simulate Frontend Client Operations
# =================================================================

client = TestClient(app)

def run_sse_test(prompt: str):
    print("\n" + "="*80)
    print(f"TESTING USER PROMPT: \"{prompt}\"")
    print("="*80)
    
    # 1. Hitting the run endpoint
    response = client.post("/api/plan/run", json={"user_prompt": prompt})
    assert response.status_code == 200, "Failed to run planner endpoint"
    
    thread_id = None
    status = "running"
    questions = []
    
    # 2. Consuming SSE stream
    for line in response.iter_lines():
        if not line:
            continue
        decoded_line = line if isinstance(line, str) else line.decode('utf-8')
        if decoded_line.startswith("data: "):
            event = json.loads(decoded_line[6:])
            event_type = event.get("type")
            
            if event_type == "log":
                print(f"[Log] {event.get('message')}")
            elif event_type == "node_start":
                print(f"\n>>> Node Start: {event.get('node').upper()}")
            elif event_type == "node_end":
                print(f"<<< Node End: {event.get('node').upper()}\n")
            elif event_type == "planner_finalized":
                print(f"\n[Event: PLANNER_FINALIZED]")
                print(f"Destinations: {event.get('destinations')}")
                print(f"Theme: {event.get('theme')}")
                print(f"Explanation: {event.get('explanation')}\n")
            elif event_type == "interrupt":
                thread_id = event.get("thread_id")
                questions = event.get("questions")
                status = "interrupted"
                print(f"\n[Interrupt] Thread: {thread_id} - Questions: {questions}")
            elif event_type == "completed":
                thread_id = event.get("thread_id")
                status = "completed"
                print(f"\n[Completed] Thread: {thread_id}")
                print(f"Planned Destinations: {event.get('planned_destinations')}")
            elif event_type == "error":
                print(f"\n[Error] {event.get('message')}")
                status = "error"
                
    # 3. If interrupted, simulate frontend answering questions
    if status == "interrupted":
        print("\n--- Simulating Human-in-the-Loop Clarification ---")
        answers = {}
        for q in questions:
            q_low = q.lower()
            if "start" in q_low or "origin" in q_low or "from" in q_low:
                answers[q] = "Delhi"
            elif "days" in q_low or "duration" in q_low or "long" in q_low:
                answers[q] = "3 days"
            elif "budget" in q_low or "cost" in q_low:
                answers[q] = "moderate"
            else:
                answers[q] = "surprise me"
                
        print(f"Answers: {answers}")
        resume_response = client.post("/api/plan/resume", json={"thread_id": thread_id, "answers": answers})
        assert resume_response.status_code == 200, "Failed to resume planner endpoint"
        
        for line in resume_response.iter_lines():
            if not line:
                continue
            decoded_line = line if isinstance(line, str) else line.decode('utf-8')
            if decoded_line.startswith("data: "):
                event = json.loads(decoded_line[6:])
                event_type = event.get("type")
                
                if event_type == "log":
                    print(f"[Log] {event.get('message')}")
                elif event_type == "node_start":
                    print(f"\n>>> Node Start: {event.get('node').upper()}")
                elif event_type == "node_end":
                    print(f"<<< Node End: {event.get('node').upper()}\n")
                elif event_type == "planner_finalized":
                    print(f"\n[Event: PLANNER_FINALIZED]")
                    print(f"Destinations: {event.get('destinations')}")
                    print(f"Theme: {event.get('theme')}")
                    print(f"Explanation: {event.get('explanation')}\n")
                elif event_type == "completed":
                    status = "completed"
                    print(f"\n[Completed] Thread: {thread_id}")
                    print(f"Planned Destinations: {event.get('planned_destinations')}")
                elif event_type == "error":
                    print(f"\n[Error] {event.get('message')}")
                    status = "error"

if __name__ == "__main__":
    import os
    # Load dotenv if present
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run ONLY the adventurous motorcycle riding trip to North India
    run_sse_test("Plan a 1-week adventurous riding trip to North India starting on 2026-08-01, style: motorcycle riding, mountain passes, adventure, budget: moderate, leaving from Delhi.")
