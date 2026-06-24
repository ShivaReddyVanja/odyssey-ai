import json
from src.agents.workflow import build_workflow
from langgraph.types import Command

def run_hitl_checkpoint_simulation():
    print("=== Compiling LangGraph Workflow with MemorySaver ===")
    app = build_workflow()
    print("Workflow compiled successfully!\n")

    # Thread config (represents a unique user session)
    config = {"configurable": {"thread_id": "travel_session_xyz"}}

    # =================================================================
    # TURN 1: Initial Incomplete User Prompt (No duration specified)
    # =================================================================
    print("--- TURN 1: Initial Prompt ---")
    initial_input = {
        "user_prompt": "I want a luxury trip to Rome, style: history, monuments, dining",
        "clarification_response": {},
        "is_validated": False,
        "transit": [],
        "accommodation": [],
        "food": [],
        "activities": []
    }
    
    print(f"User Prompt: {initial_input['user_prompt']}\n")
    
    # Run the graph on the configured thread
    print("Executing graph on thread 'travel_session_xyz'...")
    state = app.invoke(initial_input, config=config)

    # Inspect the persisted state of the thread in memory
    thread_state = app.get_state(config)
    
    print("\n--- Thread State After Turn 1 ---")
    # Check if there are active interrupts
    tasks = thread_state.tasks
    has_interrupts = len(tasks) > 0 and len(tasks[0].interrupts) > 0
    
    if has_interrupts:
        # Retrieve the questions payload sent to interrupt()
        questions = tasks[0].interrupts[0].value
        print(f"Graph is interrupted! Pending Clarification Questions: {questions}\n")
        
        # =================================================================
        # TURN 2: Resume Thread using Command(resume=...)
        # =================================================================
        question = questions[0]
        user_answer = "5 days"
        
        print("--- TURN 2: Simulating User Clarification Response ---")
        print(f"Question Asked: {question}")
        print(f"User Response: {user_answer}\n")
        
        # Prepare the resume payload (a dictionary mapping the question to the answer)
        resume_payload = {question: user_answer}
        
        print("Resuming execution on thread 'travel_session_xyz' using Command(resume=...)...")
        # Invoking with Command(resume=...) tells LangGraph to continue from the interrupt point
        final_state = app.invoke(Command(resume=resume_payload), config=config)

        print("\n=== Final Execution Results ===")
        print(f"Is Validated: {final_state.get('is_validated')}")
        print(f"Clarification Questions remaining: {final_state.get('clarification_questions')}")
        
        itinerary = final_state.get("final_itinerary")
        if itinerary:
            print("\n=== Final Compiled Itinerary ===")
            print(json.dumps(itinerary.model_dump(), indent=2))
        else:
            print("\nError: Final itinerary was not compiled!")
    else:
        print("No interrupts found. Itinerary compiled directly!")

if __name__ == "__main__":
    run_hitl_checkpoint_simulation()
