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
print("🚀 Starting Smart Guru Brain (Global Search Mode)...")
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
    print("✅ Services Initialized Successfully!")
except Exception as e:
    print(f"❌ Initialization Error: {e}")

# --- HELPER: CONTEXT MEMORY ---
def get_chat_history(user_id, limit=4):
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

# --- 🔥 TRANSLATOR (Singlish -> Sinhala) ---
def optimize_search_query(history, raw_input):
    """
    Translates Singlish to Sinhala to ensure Vector Search hits the correct page.
    """
    history_text = "\n".join([f"{msg['role']}: {msg['message']}" for msg in history]) if history else ""
    
    prompt = f"""
    Context: {history_text}
    User Input: "{raw_input}"
    
    TASK: Translate the input to 'Sinhala' (Textbook Terms) for database searching.
    
    Rules:
    1. "gunathmakabawaya" -> "ගුණාත්මකභාවය"
    2. "lakshana" -> "ලක්ෂණ"
    3. Keep English terms if they are technical (e.g., "Neurone").
    
    OUTPUT: Only the translated query.
    """
    
    try:
        resp = model.generate_content(prompt)
        optimized_query = resp.text.strip()
        print(f"🔄 Search Query Optimized: '{raw_input}' \n➡️ '{optimized_query}'")
        return optimized_query
    except:
        return raw_input

# --- SMART ROUTER ---
def detect_subject(query):
    if any(x in query.lower() for x in ['sin', 'සිංහල']): return 'Sinhala'
    if any(x in query.lower() for x in ['sci', 'විද්‍යා']): return 'Science'
    if any(x in query.lower() for x in ['his', 'ඉතිහාස']): return 'History'
    if any(x in query.lower() for x in ['hea', 'සෞඛ්‍ය', 'health']): return 'Health'
    
    prompt = f"""
    Identify O/L Subject: "{query}"
    Options: ['Sinhala', 'Science', 'History', 'Health', 'Mathematics', 'English'].
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
        # Step 1: Optimize Query
        search_query = user_input
        if media_type == "text":
            search_query = optimize_search_query(history, user_input)
        
        # Step 2: Handle Images
        if media_type == "image":
            print("🖼️ Analyzing Image...")
            image = PIL.Image.open(io.BytesIO(media_data))
            vision_resp = model.generate_content(["Extract text and explain diagrams.", image])
            search_query += f" [Image Context: {vision_resp.text}]"

        # Step 3: Subject Detection
        detected_subject = detect_subject(search_query)
        print(f"📚 Subject: {detected_subject}")

        # Step 4: Retrieval (RAG) - DUAL STRATEGY
        embedding = genai.embed_content(model="models/text-embedding-004", content=search_query, task_type="retrieval_query")['embedding']
        
        # Attempt 1: Specific Subject Search
        rpc_params = {
            "query_embedding": embedding,
            "match_threshold": 0.20, # Low threshold to catch more
            "match_count": 15,       # Get top 15 matches (anywhere in the book)
            "filter": {"subject": detected_subject}
        }
        if detected_subject == "General": del rpc_params["filter"]

        print("🔍 Attempt 1: Subject Search...")
        response = supabase.rpc("match_documents", rpc_params).execute()
        
        # Attempt 2: GLOBAL FALLBACK (If Subject Search fails)
        if not response.data and detected_subject != "General":
            print("🔄 Attempt 2: Global Search (Searching ALL books)...")
            if "filter" in rpc_params: del rpc_params["filter"]
            response = supabase.rpc("match_documents", rpc_params).execute()

        # Step 5: Construct Context
        source_found = False
        context_text = ""
        if response.data:
            source_found = True
            # Debug Print: Show which pages were found
            found_pages = [doc['metadata'].get('page') for doc in response.data]
            print(f"✅ Found Pages: {found_pages}") 
            
            context_text = "\n\n".join([f"SOURCE (Page {doc['metadata'].get('page')}):\n{doc['content']}" for doc in response.data])

        # Step 6: Marking Scheme Prompt
        system_instruction = f"""
        You are 'My Guru', an expert Sri Lankan O/L Teacher.
        User Language: {user_details.get('language', 'Sinhala')}
        Source Found: {source_found}

        TASK: Answer strictly based on the [SOURCE].
        
        RULES:
        1. **EXACTNESS:** Use the points exactly as listed in the source text.
        2. **NO HALLUCINATIONS:** If the info is missing, say so.
        3. **FORMAT:** Bullet points, Bold keys, clean spacing.

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

# --- WEBHOOK HANDLER (No Changes Needed Here) ---
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
                whatsapp_utils.send_interactive_buttons(phone, "Welcome to My Guru! 🎓\nSelect your language:", {"sin": "සිංහල", "eng": "English"})
                return {"status": "ok"}

            user = user_response.data[0]
            stage = user.get('setup_stage')

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