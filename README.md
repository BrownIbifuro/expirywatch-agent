# ExpiryWatch Agent

An AI agent that monitors retail inventory expiry dates, built with
Google ADK and Gemini. It reads stock data from MySQL, finds items
close to expiry, and recommends an action for each one.

## Run it
1. `pip install -r requirements.txt`
2. Copy `.env.example` to `expiry_agent/.env` and fill in your values
3. `adk web`