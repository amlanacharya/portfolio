import os
import requests
from groq import Groq
from typing import TypedDict, Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

class AgentState(TypedDict):
    query: str    
    intent: str
    node_id: str
    changes: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    approval: Optional[bool]

ROUTER_PROMPT = """You are a query classifier for a supply chain management system.

Classify the user's query into exactly one of these intents:

1. **query** - User wants to check the current status or state of a supply chain node
   Examples: "What is the status of port_1?", "Show me vendor_1 details", "What's the throughput at Vizag Port?"

2. **rca** - User wants to understand why something is happening or find root cause
   Examples: "Why is port_1 congested?", "What's the root cause of the delay?", "Why is route_2 disrupted?"

3. **simulate** - User wants to explore hypothetical scenarios or "what if" changes
   Examples: "What if we increase throughput at port_1?", "Simulate changing vendor_1 status", "What happens if we reroute through Chennai?"

4. **action** - User wants to execute or fix something in the system
   Examples: "Fix the port_1 status", "Change vendor_1 to operational", "Execute the reroute"

5. **document** - User is asking about policies, contracts, procedures, or regulations
   Examples: "What's the penalty for late delivery?", "What's the protocol for port congestion?", "Is this covered under force majeure?", "How do I handle a cyclone?",
             "What is the maximum storage capacity of a warehouse?", "What is the reorder trigger threshold?",
             "What is the cost increase for diverting cargo to another port?",
             "What happens when the defect rate exceeds a threshold?",
             "At what throughput level is an incident classified as high severity?",
             "What is the current price of a commodity?",
             "What is the backup route if a sea route is disrupted?",
             "Which alternative route is used when the primary route fails?"

NOTE on **query** vs **document**: Use **query** ONLY for questions about the live real-time
status of a named supply chain node (e.g. port_1, vendor_1, warehouse_1). Do NOT use query
for questions about policy values, contractual thresholds, or SOP-defined numbers — those
are always **document**.

Return ONLY the intent word. No explanation. No punctuation. Just one word: query, rca, simulate, action, or document.

User query: {query}
Intent:"""



def llm_router(state: Dict) -> Dict[str, str]:
    query = state["query"].lower()
    prompt = ROUTER_PROMPT.format(query=query)
    valid_intents = {"query", "rca", "simulate", "action", "document"}
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.1:8b",
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        answer = response.json()["response"].strip().lower()
        
        if answer in valid_intents:
            return {"intent": answer}
        else:
            print(f"[Ollama] Invalid intent: {answer}, falling back...")
    except requests.exceptions.RequestException as e:
        print(f"[Ollama] Failed: {e}")
    
    try:
        groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        answer = response.choices[0].message.content.strip().lower()
        
        if answer in valid_intents:
            return {"intent": answer}
        else:
            print(f"[Groq] Invalid intent: {answer}, falling back to keywords...")
            
    except Exception as e:
        print(f"[Groq] Failed: {e}")

    print("[Fallback] Using keyword router")
    intent = keyword_router({"query": query})["intent"]
    return {"intent": intent}

def keyword_router(state: AgentState) -> Dict[str, str]:
    query = state["query"].lower()
    
    # Action intent first (highest priority)
    if "fix" in query or "execute" in query or "change" in query:
        intent = "action"
    elif "what if" in query or "simulate" in query:
        intent = "simulate"
    elif "why" in query or "root cause" in query:
        intent = "rca"
    elif "status" in query or "state" in query:
        intent = "query"
    # Document intent keywords
    elif any(kw in query for kw in [
        "penalty", "contract", "sla", "clause", "terms",
        "protocol", "procedure", "sop", "how do i", "what do i do",
        "policy", "threshold", "reorder",
        "force majeure", "covered", "allowed", "requirement",
        "escalation", "steps", "when", "what happens"
    ]):
        intent = "document"
    else:
        intent = "document"  # Default fallback
    
    return {"intent": intent}

if __name__ == "__main__":
    test_queries = [
    "What is the status of port_1?",
    "Why is warehouse_1 struggling?",
    "What if port_1 becomes operational?",
    "Fix port_1 status to operational",
    "What's the penalty for late delivery?"
    ]

    for q in test_queries:
        result = llm_router({"query": q})
        print(f"{q} -> {result['intent']}")