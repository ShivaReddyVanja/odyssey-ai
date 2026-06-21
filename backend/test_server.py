import json
from fastapi.testclient import TestClient
from server import app

# Initialize TestClient
client = TestClient(app)

def test_health_check():
    """Verify that the health check endpoint is operational."""
    print("\n[Test] Running health check...")
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "NomadGraph API"}
    print("-> Health check passed successfully!")


def test_full_hitl_streaming_workflow():
    """
    Simulates a full streaming Human-in-the-Loop flow:
    1. Send an incomplete prompt (no duration).
    2. Read SSE stream events and verify we receive log events and a final interrupt event.
    3. Resume it with answers using a loop, reading the subsequent SSE stream.
    4. Verify it completes and generates the final itinerary.
    """
    print("\n[Test] Testing full HITL streaming workflow...")
    
    run_payload = {
        "user_prompt": "I want a luxury trip to Rome, style: history, monuments, dining"
    }
    
    print(f"Sending prompt: {run_payload['user_prompt']}")
    
    # Start the execution (which returns an SSE stream)
    response = client.post("/api/plan/run", json=run_payload)
    assert response.status_code == 200
    
    thread_id = None
    status = "interrupted"
    questions = []
    
    # Parse the SSE stream
    print("\n--- Phase 1: Reading SSE Stream ---")
    for line in response.iter_lines():
        if not line:
            continue
        decoded_line = line if isinstance(line, str) else line.decode('utf-8')
        if decoded_line.startswith("data: "):
            event = json.loads(decoded_line[6:])
            event_type = event.get("type")
            
            if event_type == "log":
                print(f"[Streaming Log] {event.get('message')}")
            elif event_type == "interrupt":
                thread_id = event.get("thread_id")
                questions = event.get("questions")
                status = "interrupted"
                print(f"\n[Streaming Event] HITL Interrupt! Thread ID: {thread_id}")
                print(f"[Streaming Event] Questions: {questions}")
            elif event_type == "completed":
                thread_id = event.get("thread_id")
                status = "completed"
                itinerary = event.get("itinerary")
                print(f"\n[Streaming Event] Completed directly! Thread ID: {thread_id}")
            elif event_type == "error":
                print(f"\n[Streaming Error] {event.get('message')}")
                raise AssertionError(f"Stream error: {event.get('message')}")

    assert thread_id is not None
    assert status == "interrupted"
    assert len(questions) > 0

    # 2. Get status via REST session endpoint
    print(f"\n[Test] Querying REST session state for thread '{thread_id}'...")
    session_response = client.get(f"/api/plan/session/{thread_id}")
    assert session_response.status_code == 200
    session_data = session_response.json()
    assert session_data["status"] == "interrupted"
    assert session_data["questions"] == questions

    # 3. Resume the execution in a loop until it is completed
    max_iterations = 10
    iteration = 0
    while status == "interrupted":
        iteration += 1
        if iteration > max_iterations:
            raise AssertionError(f"HITL loop exceeded {max_iterations} iterations without completing")
            
        answers = {}
        for question in questions:
            q_lower = question.lower()
            if "start" in q_lower or "origin" in q_lower or "from" in q_lower or "depart" in q_lower:
                answers[question] = "Hyderabad"
            elif "day" in q_lower or "duration" in q_lower or "long" in q_lower:
                answers[question] = "5 days"
            elif "budget" in q_lower or "cost" in q_lower:
                answers[question] = "50k"
            else:
                answers[question] = "general answer"

        resume_payload = {
            "thread_id": thread_id,
            "answers": answers
        }
        
        print(f"\n[Test] Resuming execution with answers: {resume_payload['answers']}")
        resume_response = client.post("/api/plan/resume", json=resume_payload)
        assert resume_response.status_code == 200
        
        # Parse the subsequent SSE stream
        print("\n--- Phase 2: Reading Resume SSE Stream ---")
        for line in resume_response.iter_lines():
            if not line:
                continue
            decoded_line = line if isinstance(line, str) else line.decode('utf-8')
            if decoded_line.startswith("data: "):
                event = json.loads(decoded_line[6:])
                event_type = event.get("type")
                
                if event_type == "log":
                    print(f"[Streaming Log] {event.get('message')}")
                elif event_type == "interrupt":
                    questions = event.get("questions")
                    status = "interrupted"
                    print(f"\n[Streaming Event] HITL Interrupt! Questions: {questions}")
                elif event_type == "completed":
                    status = "completed"
                    itinerary = event.get("itinerary")
                    validation_warnings = event.get("validation_warnings", [])
                    print(f"\n[Streaming Event] Execution Completed! Itinerary generated.")
                    if validation_warnings:
                        print(f"[Streaming Event] Warnings: {validation_warnings}")
                elif event_type == "error":
                    print(f"\n[Streaming Error] {event.get('message')}")
                    raise AssertionError(f"Stream error: {event.get('message')}")

    assert status == "completed"
    assert itinerary is not None
    assert itinerary["destination"] == "Rome"
    assert itinerary["duration_days"] == 5
    
    print("\n=== Generated Itinerary Summary ===")
    print(f"Destination: {itinerary['destination']}")
    print(f"Duration: {itinerary['duration_days']} days")
    print(f"Theme: {itinerary['theme']}")
    print(f"Number of Days Planned: {len(itinerary['days'])}")
    
    # 4. Verify final status via REST session endpoint
    print(f"\n[Test] Querying final session state for thread '{thread_id}'...")
    final_session_response = client.get(f"/api/plan/session/{thread_id}")
    assert final_session_response.status_code == 200
    final_session_data = final_session_response.json()
    assert final_session_data["status"] == "completed"
    assert final_session_data["itinerary"] == itinerary
    
    print("-> Full HITL workflow test passed successfully!")


if __name__ == "__main__":
    test_health_check()
    test_full_hitl_streaming_workflow()
