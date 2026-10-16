from dotenv import load_dotenv
load_dotenv("expiry_agent/.env")

from expiry_agent.agent import get_expiring_items

print(get_expiring_items(30))