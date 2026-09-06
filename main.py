"""
Hermes Agent 24/7 - Main Entry Point for Render
Keep alive endpoint + Telegram bot webhook
"""
import os
import asyncio
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Hermes Agent 24/7", version="1.0.0")

# ============ Keep Alive (prevents free tier spin-down) ============
@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Hermes Agent 24/7",
        "owner": "Kuldeep-kumawat",
        "telegram_bot": "connected" if os.getenv("TELEGRAM_BOT_TOKEN") else "not_configured",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "telegram_webhook": "/telegram"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "uptime": "running"}

# ============ Chat Endpoint (calls AI models) ============
@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_message = data.get("message", "")
        model = data.get("model", "gpt-5.5")

        if not user_message:
            return JSONResponse({"error": "No message provided"}, status_code=400)

        # Try OpenRouter first (free models available)
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openrouter_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": f"minimax/{model}:free" if not model.startswith("minimax") else model,
                        "messages": [
                            {"role": "system", "content": "You are Hermes Agent, a helpful AI assistant created by Kuldeep-kumawat. Respond in Hindi + English when appropriate."},
                            {"role": "user", "content": user_message}
                        ]
                    }
                )
                if response.status_code == 200:
                    result = response.json()
                    ai_reply = result["choices"][0]["message"]["content"]
                    return {"reply": ai_reply, "model": model, "source": "openrouter"}

        # Fallback to Google Gemini (free tier)
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={google_key}",
                    json={
                        "contents": [{"parts": [{"text": user_message}]}]
                    }
                )
                if response.status_code == 200:
                    result = response.json()
                    ai_reply = result["candidates"][0]["content"]["parts"][0]["text"]
                    return {"reply": ai_reply, "model": "gemini-2.5-flash", "source": "google"}

        return JSONResponse({"error": "No API keys configured"}, status_code=503)

    except Exception as e:
        logger.error(f"Chat error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# ============ Telegram Bot Webhook ============
@app.post("/telegram")
async def telegram_webhook(request: Request):
    try:
        update = await request.json()
        logger.info(f"Telegram update: {update}")

        # Extract message
        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")

        if not chat_id or not text:
            return {"ok": True}

        # Call chat endpoint internally
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:8000/chat",
                json={"message": text, "model": "minimax-m3:free"}
            )
            if response.status_code == 200:
                ai_reply = response.json().get("reply", "Sorry, I couldn't process that.")
            else:
                ai_reply = "Service temporarily unavailable."

        # Send reply to Telegram
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if bot_token:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": ai_reply}
                )

        return {"ok": True}
    except Exception as e:
        logger.error(f"Telegram error: {e}")
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
