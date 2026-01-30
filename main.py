import os
import time
import json
import traceback
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from supabase import create_client
import google.generativeai as genai
import whatsapp_utils
from dotenv import load_dotenv
import PIL.Image
import io
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, NotFound

load_dotenv()

app = FastAPI(docs_url=None, redoc_url=None)

# --- CONFIGS ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
VERIFY_TOKEN = "myguru_secure_token_2026"

# 🔥 Health Book File ID
HEALTH_FILE_NAME = "files/o21hwlhrlrfd" 

# --- INIT ---
print("🚀 Starting Smart Guru (ULTIMATE ACCURACY MODE)...")
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # 🔥 CRITICAL FIX: Using 'gemini-pro-latest'
    # This maps to the Stable 1.5 Pro model which IS in your available list.
    # PRO model is slower but MUCH more accurate than Flash.
    model = genai.GenerativeModel('models/gemini-pro-latest') 
    
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

# --- AI PROCESSING (BACKGROUND TASK) ---
def process_and_reply(user_input, phone, user, media_data=None, media_type=None):
    try:
        print(f"⏳ [PRO] Thinking about: {user_input}...")
        
        history = get_chat_history(user['id'])
        history_text = "\n".join([f"{msg['role']}: {msg['message']}" for msg in history]) if history else ""

        # 🔥 ACCURACY PROMPT
        system_instruction = f"""
        You are 'My Guru', a Sri Lankan O/L Teacher.
        User Language: {user.get('language', 'Sinhala')}
        
        TASK:
        1. **DECODE:** Convert Singlish terms to Sinhala (e.g. "Adinawa" -> "ආදීනව").
        2. **SEARCH:** Read the attached Health Textbook thoroughly.
        3. **EXTRACT:** Find the specific section and list the points exactly.
        
        RULES:
        - **NO SUMMARIES:** If the book has a list of 5 points, give all 5.
        - **STRICT TRUTH:** Only say what is in the PDF.
        - **FORMAT:** Start with "පුතේ,". Use Bullet points (•) and empty lines between them.
        
        Chat History:
        {history_text}
        
        Student Question: {user_input}
        """

        prompt_parts = [system_instruction]
        
        # Attach Book
        file_obj = genai.get_file(HEALTH_FILE_NAME)
        prompt_parts.append(file_obj)

        if media_type == "image":
             prompt_parts.append(PIL.Image.open(io.BytesIO(media_data)))

        # 🔥 ROBUST RETRY LOGIC
        bot_reply = "පුතේ, පොඩි තාක්ෂණික දෝෂයක්. 🛠️"
        
        # Try up to 3 times if server is busy
        for attempt in range(3):
            try:
                print(f"🔍 Deep Scanning (Attempt {attempt+1})...")
                final_resp = model.generate_content(prompt_parts)
                bot_reply = final_resp.text.strip()
                break # Success
            except (ResourceExhausted, ServiceUnavailable):
                print("⚠️ Server Busy. Waiting 10 seconds...")
                time.sleep(10) # Wait longer for Pro model
            except Exception as e:
                print(f"❌ Error: {e}")
                bot_reply = "පුතේ, මට පොතේ ඒ කොටස හොයාගන්න අමාරුයි. ප්‍රශ්නය තව පොඩ්ඩක් පැහැදිලි කරන්න."
                break

        print("✅ Answer Ready!")
        whatsapp_utils.send_whatsapp_message(phone, bot_reply)
        save_chat_log(user['id'], "user", user_input)
        save_chat_log(user['id'], "bot", bot_reply)

    except Exception as e:
        print(f"❌ Background Task Error: {e}")
        traceback.print_exc()

# --- WEBHOOKS ---
@app.post("/api/webhook")
async def handle_message(request: Request, background_tasks: BackgroundTasks):
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
            if user.get('setup_stage') != "active":
                 supabase.table("users").update({"setup_stage": "active"}).eq("phone_number", phone).execute()
            
            user_text = ""
            media_data = None
            
            if msg_type == "text":
                user_text = msg['text']['body']
            elif msg_type == "image":
                user_text = msg['image'].get('caption', "[Image Sent]")
                media_url = whatsapp_utils.get_media_url(msg['image']['id'])
                if media_url:
                    media_data = whatsapp_utils.download_media_file(media_url)

            if user_text:
                background_tasks.add_task(process_and_reply, user_text, phone, user, media_data, msg_type)

    except Exception as e:
        print(f"❌ Error: {e}")

    return {"status": "ok"}

@app.get("/api/webhook")
async def verify_webhook(request: Request):
    if request.query_params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(request.query_params.get("hub.challenge"))
    raise HTTPException(status_code=403, detail="Verification failed")