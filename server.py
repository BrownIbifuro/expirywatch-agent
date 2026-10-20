import time
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv("expiry_agent/.env")

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from expiry_agent import data
from expiry_agent.agent import root_agent, SUGGESTIONS

APP, USER = "expiry_agent", "demo"
sessions = InMemorySessionService()
runner = Runner(agent=root_agent, app_name=APP, session_service=sessions)
app = FastAPI(title="ExpiryWatch Agent")
HITS = defaultdict(list)


class Chat(BaseModel):
    message: str
    session_id: str


def visible():
    return [s for s in SUGGESTIONS.values() if s["status"] != "dismissed"]


def limit(request: Request):
    """Public demo only: 20 questions per visitor per hour."""
    if not data.DEMO:
        return
    ip = request.headers.get("x-forwarded-for", "").split(",")[0] or request.client.host
    now = time.time()
    HITS[ip] = [t for t in HITS[ip] if now - t < 3600]
    if len(HITS[ip]) >= 20:
        raise HTTPException(429, "Demo limit reached. Try again in an hour.")
    HITS[ip].append(now)


@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.get("/api/stats")
def stats():
    return {**data.fetch_stats(), "demo": data.DEMO}


@app.get("/api/suggestions")
def suggestions():
    return {"suggestions": visible()}


@app.post("/api/chat")
async def chat(req: Chat, request: Request):
    limit(request)
    if not await sessions.get_session(
        app_name=APP, user_id=USER, session_id=req.session_id
    ):
        await sessions.create_session(
            app_name=APP, user_id=USER, session_id=req.session_id
        )
    msg = types.Content(role="user", parts=[types.Part(text=req.message[:500])])
    reply = ""
    try:
        async for ev in runner.run_async(
            user_id=USER, session_id=req.session_id, new_message=msg
        ):
            if ev.is_final_response() and ev.content and ev.content.parts:
                reply = "".join(p.text or "" for p in ev.content.parts)
    except Exception as e:
        raise HTTPException(503, f"The model could not answer: {e}")
    return {"reply": reply, "suggestions": visible()}


@app.post("/api/suggestions/{sid}/{verb}")
def decide(sid: str, verb: str):
    s = SUGGESTIONS.get(sid)
    if not s or verb not in ("approve", "dismiss"):
        raise HTTPException(404, "Unknown suggestion")
    if verb == "approve":
        data.flag(s["item_id"])
        s["status"] = "approved"
    else:
        s["status"] = "dismissed"
    return {"suggestions": visible()}
