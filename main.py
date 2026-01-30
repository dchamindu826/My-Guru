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

# Credit System: REMOVED (Unlimited Access) 🚀

# --- INITIALIZATION ---
print("🚀 Starting Smart Guru Brain...")
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
    print("✅ Services Initialized Successfully!")
except Exception as e:
    print(f"❌ Initialization Error: {e}")

# --- HELPER: CONTEXT MEMORY ---
def get_chat_history(user_id, limit=4):
    """Fetches the last few messages to understand context."""
    try:
        response = supabase.table("chat_logs")\
            .select("role, message")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        return response.data[::-1] if response.data else []
    except Exception as e:
        print(f"⚠️ Error fetching history: {e}")
        return []

def save_chat_log(user_id, role, message):
    try:
        supabase.table("chat_logs").insert({
            "user_id": user_id,
            "role": role,
            "message": message
        }).execute()
    except Exception:
        pass

# --- 🔥 THE NEW BRAIN: SINGLISH TO SINHALA CONVERTER ---
def contextualize_query(history, new_query):
    """
    1. Understands context (e.g., "eke" -> "1910 reforms").
    2. TRANSLATES Singlish to Sinhala for better database searching.
    """
    history_text = "\n".join([f"{msg['role']}: {msg['message']}" for msg in history]) if history else ""
    
    prompt = f"""
    Conversation History:
    {history_text}
    
    User's Input: "{new_query}"
    
    TASK: 
    1. If the input relies on history (e.g., "eke", "e gena"), rewrite it as a full standalone question.
    2. **CRITICAL:** If the input is in "Singlish" (Sinhala words in English letters), **TRANSLATE IT TO SINHALA** script.
       - Example: "cell wala kriyakarithwaya" -> "සෛල වල ක්‍රියාකාරීත්වය"
       - Example: "gunathmakabawaya" -> "ගුණාත්මකභාවය"
    3. If the input is in English, keep it in English.

    OUTPUT: Only the rewritten/translated query.
    """
    
    try:
        resp = model.generate_content(prompt)
        rewritten = resp.text.strip()
        print(f"🔄 Search Query Optimized: '{new_query}' -> '{rewritten}'")
        return rewritten
    except:
        return new_query

# --- SMART ROUTER ---
def detect_subject(query):
    prompt = f"""
    Analyze query: "{query}"
    Identify subject from: ['Sinhala', 'Science', 'History', 'Health', 'Mathematics', 'English'].
    If unsure, return 'General'.
    Return JSON: {{"subject": "..."}}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(text).get("subject", "General")
    except:
        return "General"

# --- MAIN AI RESPONSE GENERATOR ---
def get_ai_response(user_input, user_details, history, media_data=None, media_type=None):
    try:
        # Step 1: Optimize Query (Singlish -> Sinhala)
        search_query = user_input
        if media_type == "text":
            search_query = contextualize_query(history, user_input)
        
        # Step 2: Handle Images
        if media_type == "image":
            print("🖼️ Analyzing Image...")
            image = PIL.Image.open(io.BytesIO(media_data))
            vision_resp = model.generate_content(["Extract all educational text and diagrams from this image.", image])
            search_query += f" [Image Context: {vision_resp.text}]"

        # Step 3: Subject Detection
        detected_subject = detect_subject(search_query)
        print(f"📚 Subject: {detected_subject} | 🔍 Optimized Query: {search_query}")

        # Step 4: Retrieval (RAG)
        embedding = genai.embed_content(model="models/text-embedding-004", content=search_query, task_type="retrieval_query")['embedding']
        
        rpc_params = {
            "query_embedding": embedding,
            "match_threshold": 0.28,
            "match_count": 8,
            "filter": {"subject": detected_subject}
        }
        if detected_subject == "General": del rpc_params["filter"]

        response = supabase.rpc("match_documents", rpc_params).execute()
        
        # Fallback Global Search
        if not response.data and detected_subject != "General":
            print("🔄 Global Search Fallback...")
            if "filter" in rpc_params: del rpc_params["filter"]
            response = supabase.rpc("match_documents", rpc_params).execute()

        # Step 5: Construct Context
        source_found = False
        context_text = ""
        if response.data:
            source_found = True
            context_text = "\n\n".join([f"[SOURCE START]\n{doc['content']}\n[SOURCE END]" for doc in response.data])

        # Step 6: The "Marking Scheme" Personality
        system_instruction = f"""
        You are 'My Guru', an expert Sri Lankan O/L Teacher.
        User Language: {user_details.get('language', 'Sinhala')}
        Source Found: {source_found}

        TASK: Answer strictly based on the [SOURCE] context like an **Exam Marking Scheme**.

        RULES:
        1. **STRICT SOURCE USAGE:** You MUST derive your answer *primarily* from the [SOURCE] context.
        2. **STRICT TERMINOLOGY:** Use the EXACT technical terms (Pari Bhashika Wachana) found in the text.
        3. **FORMATTING:** - Use Bullet Points (•).
           - **Bold** key terms.
           - Add empty lines between points.
        4. **MISSING INFO:**
           - If 'Source Found' is False, explicitly say: "පුතේ, මගේ Database එකේ (පෙළ පොත්වල) මේ ගැන කරුණු සඳහන් වෙලා නෑ. නමුත් O/L විෂය නිර්දේශයට අනුව පිළිතුර මෙයයි:" and then provide the answer.

        CONTEXT FROM DATABASE:
        {context_text}
        """
        
        prompt_parts = [system_instruction]
        if media_type == "image": prompt_parts.append(PIL.Image.open(io.BytesIO(media_data)))
        prompt_parts.append(f"Student Question: {search_query}") 

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
            
            # User Management
            user_response = supabase.table("users").select("*").eq("phone_number", phone).execute()
            if not user_response.data:
                supabase.table("users").insert({"phone_number": phone, "setup_stage": "language"}).execute()
                whatsapp_utils.send_interactive_buttons(phone, "Welcome to My Guru! 🎓\nSelect your language:", {"sin": "සිංහල", "eng": "English"})
                return {"status": "ok"}

            user = user_response.data[0]
            stage = user.get('setup_stage')

            # Stage Logic
            if stage == "language":
                if msg_type == "interactive":
                    sel = msg['interactive']['button_reply']['id']
                    lang = "Sinhala" if sel == "sin" else "English"
                    supabase.table("users").update({"language": lang, "setup_stage": "level"}).eq("phone_number", phone).execute()
                    whatsapp_utils.send_interactive_buttons(phone, "Select Exam:", {"ol": "O/L", "al": "A/L"})
                else:
                    whatsapp_utils.send_interactive_buttons(phone, "Select Language:", {"sin": "සිංහල", "eng": "English"})

            elif stage == "level":
                if msg_type == "interactive":
                    if msg['interactive']['button_reply']['id'] == "ol":
                        supabase.table("users").update({"grade": "O/L", "setup_stage": "active"}).eq("phone_number", phone).execute()
                        whatsapp_utils.send_whatsapp_message(phone, "හරි පුතේ! O/L පටන් ගමු. කැමති ප්‍රශ්නයක් අහන්න. 📚")
                    else:
                        whatsapp_utils.send_whatsapp_message(phone, "Sorry, O/L only for now.")

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
                    print(f"📤 Sending Reply...")
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