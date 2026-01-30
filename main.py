import os
import io
import json
import traceback
from fastapi import FastAPI, Request, HTTPException
from supabase import create_client
import google.generativeai as genai
import whatsapp_utils
from dotenv import load_dotenv
import PIL.Image

# Load Environment Variables
load_dotenv()

app = FastAPI(docs_url=None, redoc_url=None)

# --- CONFIGURATIONS ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
VERIFY_TOKEN = "myguru_secure_token_2026"

# --- INITIALIZATION ---
print("🚀 Starting Smart Guru Brain (BRUTE FORCE MODE)...")
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
    print("✅ Services Initialized Successfully!")
except Exception as e:
    print(f"❌ Initialization Error: {e}")

# --- HELPER FUNCTIONS ---
def get_chat_history(user_id, limit=4):
    try:
        response = supabase.table("chat_logs")\
            .select("role, message")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        return response.data[::-1] if response.data else []
    except:
        return []

def save_chat_log(user_id, role, message):
    try:
        supabase.table("chat_logs").insert({"user_id": user_id, "role": role, "message": message}).execute()
    except:
        pass

# --- TRANSLATOR (Singlish -> Sinhala) ---
def optimize_search_query(history, raw_input):
    history_text = "\n".join([f"{msg['role']}: {msg['message']}" for msg in history]) if history else ""
    prompt = f"""
    Context: {history_text}
    User Input: "{raw_input}"
    TASK: Translate Input to Sinhala keywords found in Sri Lankan Textbooks.
    Example: "gunathmakabawaya" -> "ගුණාත්මකභාවය"
    OUTPUT: Only the Sinhala keywords.
    """
    try:
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except:
        return raw_input

# --- MAIN AI RESPONSE GENERATOR ---
def get_ai_response(user_input, user_details, history, media_data=None, media_type=None):
    try:
        # 1. Query හදාගැනීම
        search_query = user_input
        if media_type == "text":
            search_query = optimize_search_query(history, user_input)
        
        # 2. Image තිබේනම් විස්තර ගැනීම
        if media_type == "image":
            print("🖼️ Analyzing Image...")
            image = PIL.Image.open(io.BytesIO(media_data))
            vision_resp = model.generate_content(["Extract text.", image])
            search_query += f" {vision_resp.text}"

        print(f"🔍 Searching Database for: {search_query}")

        # 3. Retrieval (BRUTE FORCE - NO FILTERS)
        embedding = genai.embed_content(model="models/text-embedding-004", content=search_query, task_type="retrieval_query")['embedding']
        
        # 🔥 වෙනස මෙතනයි: Filter අයින් කළා, Threshold බිංදුව කළා, පිටු 40ක් කියවනවා
        rpc_params = {
            "query_embedding": embedding,
            "match_threshold": 0.0,  # 0.0 කියන්නේ පොඩි හරි ගැලපීමක් තියෙන ඕන එකක් ගන්නවා
            "match_count": 40,       # පිටු 40ක් එකපාර අදිනවා (මිස් වෙන්න විදියක් නෑ)
            "filter": {}             # විෂය Filter කරන්නෙත් නෑ. ඔක්කොම බලනවා.
        }

        response = supabase.rpc("match_documents", rpc_params).execute()
        
        source_found = False
        context_text = ""
        
        if response.data:
            source_found = True
            # Debug: මොන පිටුද අහු වුනේ කියලා බලන්න
            pages = [doc['metadata'].get('page') for doc in response.data]
            print(f"✅ Found Pages: {pages}")
            
            context_text = "\n\n".join([f"SOURCE (Page {doc['metadata'].get('page')}):\n{doc['content']}" for doc in response.data])
        else:
            print("❌ No matching pages found even with Brute Force.")

        # 4. Final Answer Generation
        system_instruction = f"""
        You are 'My Guru', a Sri Lankan O/L Teacher.
        User Language: {user_details.get('language', 'Sinhala')}
        Source Found: {source_found}

        TASK: Find the answer in the [SOURCE] text below and present it exactly as it appears.

        RULES:
        1. **LOOK DEEP:** The answer might be in the middle of the text. Read all sources carefully.
        2. **EXACT MATCH:** If you see the list (e.g., "ගුණාත්මකභාවය"), output that list exactly.
        3. **NO EXCUSES:** If the info is there, show it. Do not say "I can't find it" unless it is truly missing.
        4. **FORMAT:** Use Bullet Points (•) and Bold text.

        CONTEXT FROM DATABASE:
        {context_text}
        
        STUDENT QUESTION: {search_query}
        """
        
        prompt_parts = [system_instruction]
        if media_type == "image": prompt_parts.append(PIL.Image.open(io.BytesIO(media_data)))

        final_resp = model.generate_content(prompt_parts)
        return final_resp.text.strip()

    except Exception as e:
        print(f"❌ AI Error: {e}")
        traceback.print_exc()
        return "පුතේ, පොඩි තාක්ෂණික දෝෂයක්. ආයේ අහන්නකෝ. 🛠️"

# --- WEBHOOK HANDLER ---
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
            
            # User Check & Setup
            user_response = supabase.table("users").select("*").eq("phone_number", phone).execute()
            if not user_response.data:
                supabase.table("users").insert({"phone_number": phone, "setup_stage": "language"}).execute()
                whatsapp_utils.send_interactive_buttons(phone, "Welcome! Select Language:", {"sin": "සිංහල", "eng": "English"})
                return {"status": "ok"}

            user = user_response.data[0]
            stage = user.get('setup_stage')

            # Flow Logic
            if stage == "language":
                if msg_type == "interactive":
                    lang = "Sinhala" if msg['interactive']['button_reply']['id'] == "sin" else "English"
                    supabase.table("users").update({"language": lang, "setup_stage": "active"}).eq("phone_number", phone).execute()
                    whatsapp_utils.send_whatsapp_message(phone, "හරි පුතේ! ඕනම ප්‍රශ්නයක් අහන්න. 📚")
                else:
                    whatsapp_utils.send_interactive_buttons(phone, "Select Language:", {"sin": "සිංහල", "eng": "English"})

            elif stage == "level": # Skip level, go strictly active for now
                 supabase.table("users").update({"setup_stage": "active"}).eq("phone_number", phone).execute()
                 whatsapp_utils.send_whatsapp_message(phone, "හරි පුතේ! ඕනම ප්‍රශ්නයක් අහන්න. 📚")

            elif stage == "active":
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
                    print(f"📤 Sending: {response[:30]}...")
                    whatsapp_utils.send_whatsapp_message(phone, response)
                    save_chat_log(user['id'], "user", user_text)
                    save_chat_log(user['id'], "bot", response)

    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()

    return {"status": "ok"}

@app.get("/api/webhook")
async def verify_webhook(request: Request):
    if request.query_params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(request.query_params.get("hub.challenge"))
    raise HTTPException(status_code=403, detail="Verification failed")