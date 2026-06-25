import json
from src.agents.workflow import build_workflow

import asyncio

async def run_test():
    print("=== Compiling LangGraph Workflow ===")
    app = build_workflow()
    print("Workflow compiled successfully!\n")

    # Test Case: Hyderabad to North India 2-week trip
    inputs_complete = {
        "user_prompt": "Plan a 2-week trip to North India starting on 2026-08-01, leaving from Hyderabad. Theme: spiritual, adventure, snow, bike ride, landscapes, great food. Budget: 1 lakh.",
        "clarification_response": {},
        "is_validated": False,
        "transit": [],
        "accommodation": [],
        "food": [],
        "activities": [],
        "planned_destinations": []
    }

    print("=== Executing Workflow with North India Trip Prompt ===")
    print(f"Prompt: {inputs_complete['user_prompt']}\n")
    
    # Run the compiled graph
    config = {
        "recursion_limit": 100,
        "configurable": {"thread_id": "test_thread_north_india"}
    }
    final_state = await app.ainvoke(inputs_complete, config=config)

    print("\n=== Execution Results ===")
    print(f"Is Validated: {final_state.get('is_validated')}")
    print(f"Clarification Questions: {final_state.get('clarification_questions')}")
    
    itinerary = final_state.get("final_itinerary")
    if itinerary:
        print("\n=== Final Compiled Itinerary ===")
        # Pretty print the Pydantic model as JSON
        print(json.dumps(itinerary.model_dump(), indent=2))
        
        print("\n=== Validation Warnings ===")
        print(final_state.get("validation_warnings", []))
    else:
        print("\nError: Final itinerary was not generated!")

if __name__ == "__main__":
    asyncio.run(run_test())
