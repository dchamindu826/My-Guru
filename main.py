from fastapi import FastAPI, Request, HTTPException
from ai_engine import process_user_message
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Meta Verification Token (Security sadaha)
VERIFY_TOKEN = "my_guru_secret_token_2026" 

@app.get("/")
async def home():
    return {"status": "Active", "message": "My Guru AI Server is Running!"}

@app.get("/webhook")
async def verify_webhook(request: Request):
    """WhatsApp Webhook Verification"""
    # Meta eken webhook eka verify karanna me request eka ewanawa
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if verify_token == VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Invalid verification token")

@app.post("/webhook")
async def receive_whatsapp_message(request: Request):
    """Handle Incoming Messages"""
    data = await request.json()
    
    try:
        # WhatsApp JSON structure eken message eka eliyata ganna one
        entry = data['entry'][0]
        changes = entry['changes'][0]
        value = changes['value']
        
        if 'messages' in value:
            message_data = value['messages'][0]
            phone_number = message_data['from']
            text_body = message_data['text']['body']
            
            # AI Engine eka wada karawanna
            await process_user_message(phone_number, text_body)
            
    except Exception as e:
        print(f"Error processing message: {e}")
        # Error ekak awath 200 OK yawanna one nathnam WhatsApp eka retry karanawa
        pass

    return {"status": "received"}