import os
import time
import json
import traceback
from fastapi import FastAPI, Request, HTTPException
from supabase import create_client
import google.generativeai as genai
import whatsapp_utils
from dotenv import load_dotenv
import PIL.Image
import io

load_dotenv()

app = FastAPI(docs_url=None, redoc_url=None)

# --- CONFIGS ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
VERIFY_TOKEN = "myguru_secure_token_2026"

# 🔥 Health Book File ID (Make sure this matches your upload)
HEALTH_FILE_NAME = "files/o21hwlhrlrfd"

# --- INIT ---
print("🚀 Starting Smart Guru (Direct File Mode)...")
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
    print("✅ Services Initialized Successfully!")
except Exception as e:
    print(f"❌ Initialization Error: {e}")

# --- HELPERS ---
def get_chat_history(user_id, limit=4):
    try:
        response = supabase.table("chat_logs").select("role, message").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
        return response.data[::-1] if response.data else []
    except:
        return []

def save_chat_log(user_id, role, message):
    try:
        supabase.table("chat_logs").insert({"user_id": user_id, "role": role, "message": message}).execute()
    except:
        pass

# --- AI ENGINE (DIRECT FILE ACCESS) ---
def get_ai_response(user_input, user_details, history, media_data=None, media_type=None):
    try:
        print(f"🧠 Processing Query: {user_input}")

        # 1. Message History
        history_text = "\n".join([f"{msg['role']}: {msg['message']}" for msg in history]) if history else ""

        # 2. System Instruction
        system_instruction = f"""
        You are 'My Guru', a friendly Sri Lankan O/L Teacher.
        User Language: {user_details.get('language', 'Sinhala')}
        
        TASK: You have access to the Grade 10 Health Textbook (attached).
        Find the answer strictly from this book.

        RULES:
        1. **LOOK EVERYWHERE:** The answer might be deep inside the book. Scan carefully.
        2. **TRANSLATE:** If user asks in Singlish (e.g., "gunathmakabawaya"), find the Sinhala term ("ගුණාත්මකභාවය") in the book.
        3. **EXACT LISTS:** If the book has a list (e.g., characteristics/lakshana), copy them EXACTLY.
        4. **FORMAT:** Start with "පුතේ," (Puthe). Use Bullet Points (•) and Emojis.
        5. **NO HALLUCINATIONS:** If it's not in the book, say so.

        Chat History:
        {history_text}
        
        Student Question: {user_input}
        """

        prompt_parts = [system_instruction]

        # 3. 🔥 FIX: Attach the PDF File Object DIRECTLY
        # Dictionary එකක් විදියට නෙවෙයි, කෙලින්ම Object එක දානවා
        print(f"📂 Fetching File: {HEALTH_FILE_NAME}...")
        file_obj = genai.get_file(HEALTH_FILE_NAME)
        prompt_parts.append(file_obj)

        # 4. Add User Image if exists
        if media_type == "image":
             prompt_parts.append(PIL.Image.open(io.BytesIO(media_data)))

        # 5. Generate
        print("🔍 Searching inside the FULL Health Textbook...")
        final_resp = model.generate_content(prompt_parts)
        
        print("✅ Answer Generated!")
        return final_resp.text.strip()

    except Exception as e:
        print(f"❌ AI Error: {e}")
        traceback.print_exc()
        return "පුතේ, පොඩි තාක්ෂණික දෝෂයක්. මට පොත පෙරලගන්න බැරි වුනා. 🛠️"

# --- WEBHOOKS ---
@app.post("/api/webhook")
async def handle_message(request: Request):
    try:
        data = await request.json()
        if not data.get('entry'): return {"status": "ignored"}
        entry = data['entry'][0]['changes'][0]['value']
        
        if 'messages' in entry:
            msg = entry['messages'][0]
            phone = msg['from']
            msg_type = msg['type']
            
            user_response = supabase.table("users").select("*").eq("phone_number", phone).execute()
            if not user_response.data:
                supabase.table("users").insert({"phone_number": phone, "setup_stage": "language"}).execute()
                whatsapp_utils.send_interactive_buttons(phone, "Welcome! Select Language:", {"sin": "සිංහල", "eng": "English"})
                return {"status": "ok"}

            user = user_response.data[0]
            stage = user.get('setup_stage')

            # Force Active stage for testing
            if stage != "active":
                 supabase.table("users").update({"setup_stage": "active"}).eq("phone_number", phone).execute()
            
            history = get_chat_history(user['id'])
            response = None
            user_text = ""

            if msg_type == "text":
                user_text = msg['text']['body']
                response = get_ai_response(user_text, user, history, media_type="text")
            elif msg_type == "image":
                user_text = msg['image'].get('caption', "[Image Sent]")
                media_url = whatsapp_utils.get_media_url(msg['image']['id'])
                if media_url:
                    media_data = whatsapp_utils.download_media_file(media_url)
                    response = get_ai_response(user_text, user, history, media_data=media_data, media_type="image")

            if response:
                whatsapp_utils.send_whatsapp_message(phone, response)
                save_chat_log(user['id'], "user", user_text)
                save_chat_log(user['id'], "bot", response)

    except Exception as e:
        print(f"❌ Error: {e}")

    return {"status": "ok"}

@app.get("/api/webhook")
async def verify_webhook(request: Request):
    if request.query_params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(request.query_params.get("hub.challenge"))
    raise HTTPException(status_code=403, detail="Verification failed")