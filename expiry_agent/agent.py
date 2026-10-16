import os
import pymysql
from google.adk.agents import Agent


def get_expiring_items(days: int = 30) -> dict:
    """Returns inventory items that are already expired or will expire
    within the given number of days. days_left is negative for items
    that have already expired."""
    conn = pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, product_name, category, quantity, flagged,
                       expiry_date,
                       DATEDIFF(expiry_date, CURDATE()) AS days_left
                FROM inventory
                WHERE expiry_date <= DATE_ADD(CURDATE(), INTERVAL %s DAY)
                ORDER BY expiry_date
                """,
                (days,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    for row in rows:
        row["expiry_date"] = str(row["expiry_date"])
    return {"count": len(rows), "items": rows}


root_agent = Agent(
    name="expiry_agent",
    model="gemini-3.5-flash",
    description="Monitors inventory expiry dates for a retail store.",
       instruction=(
        "You are an inventory expiry assistant for a retail store. "
        "Use the get_expiring_items tool to check stock. "
        "Start with a one-line summary: how many items are expired and "
        "how many expire within 30 days. "
        "Then list the 5 most urgent items that have NOT yet expired, "
        "soonest first. For each: name, quantity, days left, one "
        "recommended action (discount, move to front, or reorder review) "
        "and a short reason. "
        "Do not list items that expired long ago one by one. Mention only "
        "how many there are and suggest a bulk removal review. "
        "You can only read data. Never claim you changed anything."
    ),
    tools=[get_expiring_items],
)