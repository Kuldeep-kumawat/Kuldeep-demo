"""
Hermes Agent 24/7 - Simple FastAPI App
Works with any Python 3.11+ environment
"""
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import httpx

load_dotenv()

app = FastAPI(title="Hermes Agent 24/7")

@app.get("/")
async def root():
    return {"status": "online", "service": "Hermes Agent 24/7"}

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/chat")
async def chat(request):
    try:
        data = await request.json()
        msg = data.get("message", "Hello")
        # Try OpenRouter free model
        key = os.getenv("OPENROUTER_API_KEY")
        if key:
            async with httpx.AsyncClient() as c:
                r = await c.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model":"minimax/minimax-m3:free","messages":[{"role":"user","content":msg}]}
                )
                if r.status_code == 200:
                    reply = r.json()["choices"][0]["message"]["content"]
                    return {"reply": reply, "source": "openrouter"}
        return {"reply": "AI response: " + msg, "note": "Add API keys for full AI"}
    except Exception as e:
        return {"error": str(e)}
