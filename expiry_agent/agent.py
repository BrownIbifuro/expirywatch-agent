from google.adk.agents import Agent
from google.genai import types
from expiry_agent import data

# Suggestions the agent has proposed. A human approves or dismisses each one.
SUGGESTIONS = {}


def get_expiring_items(days: int = 30) -> dict:
    """Returns inventory items that are already expired or will expire
    within the given number of days. days_left is negative for items
    that have already expired."""
    rows = data.fetch_expiring(days)
    return {"count": len(rows), "items": rows}


def propose_action(item_id: int, product_name: str, action: str,
                   reason: str, days_left: int) -> dict:
    """Records a suggested action for a human to approve.
    action must be one of: discount, move_to_front, reorder_review."""
    key = f"{item_id}:{action}"
    if key not in SUGGESTIONS:
        SUGGESTIONS[key] = {
            "id": key, "item_id": item_id, "product": product_name,
            "action": action, "reason": reason, "days_left": days_left,
            "status": "pending",
        }
    return {"recorded": True}


root_agent = Agent(
    name="expiry_agent",
    model="gemini-3.5-flash",
    description="Monitors inventory expiry dates for a retail store.",
    instruction=(
        "You are an inventory expiry assistant for a retail store. "
        "Use get_expiring_items to check stock (30 days unless the person "
        "asks for another window). Start with one line: how many items are "
        "already expired and how many expire within the window. When the "
        "person asks what to do, what needs attention, or to check stock, "
        "take up to 5 of the most urgent items that have NOT yet expired "
        "and fall inside the window they asked about, soonest first, and "
        "call propose_action once for each (discount, move_to_front or "
        "reorder_review, a one-sentence reason, and days_left). Then reply "
        "in short plain text naming those items and why. Do not list "
        "long-expired items one by one; say how many there are and suggest "
        "a bulk removal review. You can only read data and propose "
        "actions. A human approves every action. Never claim you changed "
        "anything."
    ),
    tools=[get_expiring_items, propose_action],
    generate_content_config=types.GenerateContentConfig(
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                attempts=5, initial_delay=2.0, max_delay=30.0
            )
        )
    ),
)
