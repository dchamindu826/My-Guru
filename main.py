from fastapi import FastAPI, Request, HTTPException
import ai_engine
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
VERIFY_TOKEN = "my_guru_secret_token_2026"

@app.get("/")
async def home():
    return {"status": "Active", "mode": "My Guru Multimodal"}

@app.get("/webhook")
async def verify_webhook(request: Request):
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if verify_token == VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Invalid token")

@app.post("/webhook")
async def receive_whatsapp_message(request: Request):
    data = await request.json()
    
    try:
        if data.get("entry"):
            for entry in data["entry"]:
                for change in entry["changes"]:
                    if change["value"].get("messages"):
                        msg = change["value"]["messages"][0]
                        phone_number = msg["from"]
                        msg_type = msg["type"]

                        print(f"📩 New Message Type: {msg_type}")

                        if msg_type == "text":
                            body = msg["text"]["body"]
                            await ai_engine.process_message(phone_number, body, "text")
                        
                        elif msg_type == "audio":
                            media_id = msg["audio"]["id"]
                            await ai_engine.process_message(phone_number, "", "audio", media_id)
                        
                        elif msg_type == "image":
                            media_id = msg["image"]["id"]
                            caption = msg["image"].get("caption", "") # Caption එකත් ගන්නවා
                            await ai_engine.process_message(phone_number, caption, "image", media_id)
                            
    except Exception as e:
        print(f"❌ Error: {e}")
        pass

    return {"status": "received"}