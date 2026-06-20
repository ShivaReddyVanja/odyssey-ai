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


def test_full_hitl_workflow():
    """
    Simulates a full Human-in-the-Loop flow:
    1. Send an incomplete prompt (no duration).
    2. Verify it interrupts and returns a clarifying question.
    3. Resume it with the answer.
    4. Verify it completes and generates the final itinerary.
    """
    print("\n[Test] Testing full HITL workflow...")
    
    # 1. Run with incomplete prompt (triggers gatekeeper interrupt)
    run_payload = {
        "user_prompt": "I want a luxury trip to Rome, style: history, monuments, dining"
    }
    
    print(f"Sending prompt: {run_payload['user_prompt']}")
    response = client.post("/api/plan/run", json=run_payload)
    
    assert response.status_code == 200
    data = response.json()
    
    thread_id = data.get("thread_id")
    status = data.get("status")
    questions = data.get("questions")
    
    print(f"Received status: '{status}'")
    print(f"Thread ID: '{thread_id}'")
    print(f"Clarification Questions: {questions}")
    
    assert thread_id is not None
    assert status == "interrupted"
    assert questions is not None
    assert len(questions) > 0
    
    # 2. Get status via REST session endpoint
    print(f"\n[Test] Querying session state for thread '{thread_id}'...")
    session_response = client.get(f"/api/plan/session/{thread_id}")
    assert session_response.status_code == 200
    session_data = session_response.json()
    assert session_data["status"] == "interrupted"
    assert session_data["questions"] == questions
    
    # 3. Resume the execution in a loop until it is completed
    status = "interrupted"
    while status == "interrupted":
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
        resume_data = resume_response.json()
        
        status = resume_data.get("status")
        questions = resume_data.get("questions")
        itinerary = resume_data.get("itinerary")
        
        print(f"Response status: '{status}'")
        if status == "interrupted":
            print(f"Next Clarification Questions: {questions}")

    assert status == "completed"
    assert itinerary is not None
    assert itinerary["destination"] == "Rome"
    assert itinerary["duration_days"] == 5
    
    print("\n=== Generated Itinerary Summary ===")
    print(f"Destination: {itinerary['destination']}")
    print(f"Duration: {itinerary['duration_days']} days")
    print(f"Theme: {itinerary['theme']}")
    print(f"Number of Days Planned: {len(itinerary['days'])}")
    
    # 4. Verify status via REST session endpoint is completed
    print(f"\n[Test] Querying final session state for thread '{thread_id}'...")
    final_session_response = client.get(f"/api/plan/session/{thread_id}")
    assert final_session_response.status_code == 200
    final_session_data = final_session_response.json()
    assert final_session_data["status"] == "completed"
    assert final_session_data["itinerary"] == itinerary
    
    print("-> Full HITL workflow test passed successfully!")


if __name__ == "__main__":
    test_health_check()
    test_full_hitl_workflow()
