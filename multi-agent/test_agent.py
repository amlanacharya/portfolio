"""
Quick CLI test — validates all four agent paths.
"""

from agents.orchestrator import run_query, approve_action, reject_action

DEMO_QUERIES = [
    ("state",     "What is the current state of our supply chain?"),
    ("root",      "Why are deliveries to DC North delayed?"),
    ("simulate",  "What if we reroute shipments from route 1 to route 3?"),
    ("action",    "Mark vendor X as suspended due to the port congestion"),
]

SEP = "-" * 60

for tag, query in DEMO_QUERIES:
    print(f"\n{SEP}")
    print(f"[{tag.upper()}] {query}")
    print(SEP)

    state = run_query(query, thread_id=tag)

    print(f"Intent   : {state['intent']}")
    print(f"Entity   : {state['target_entity']}")

    if state.get("pending_action"):
        print(f"Pending  : {state['pending_action']}")
        print(">> Auto-approving for test...")
        state = approve_action(thread_id=tag)

    print(f"\nResponse :\n{state['final_response']}")
