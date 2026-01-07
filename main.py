from fastapi import FastAPI, Request, HTTPException
import ai_engine
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Meta Verification Token
VERIFY_TOKEN = "my_guru_secret_token_2026" 

@app.get("/")
async def home():
    return {"status": "Active", "message": "My Guru AI Server is Running!"}

@app.get("/webhook")
async def verify_webhook(request: Request):
    """WhatsApp Webhook Verification"""
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if verify_token == VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Invalid verification token")

@app.post("/webhook")
async def receive_whatsapp_message(request: Request):
    """Handle Incoming Messages (Text & Buttons)"""
    data = await request.json()
    
    try:
        # Check if valid message
        if data.get("entry"):
            for entry in data["entry"]:
                for change in entry["changes"]:
                    if change["value"].get("messages"):
                        msg = change["value"]["messages"][0]
                        phone_number = msg["from"]
                        
                        # 1. Handle Text Messages
                        if msg["type"] == "text":
                            user_message = msg["text"]["body"]
                            await ai_engine.process_user_message(phone_number, user_message, "text")
                        
                        # 2. Handle Button Clicks (Interactive)
                        elif msg["type"] == "interactive":
                            # Button ID එක ගන්න (උදා: lang_si, exam_ol)
                            button_reply = msg["interactive"]["button_reply"]
                            button_id = button_reply["id"] 
                            
                            # ID එක ai_engine එකට යවන්න
                            await ai_engine.process_user_message(phone_number, button_id, "interactive")
                        
    except Exception as e:
        print(f"Error processing message: {e}")
        pass

    return {"status": "received"}