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
        # Reverse to get chronological order (Oldest -> Newest)
        return response.data[::-1] if response.data else []
    except Exception as e:
        print(f"⚠️ Error fetching history: {e}")
        return []

def save_chat_log(user_id, role, message):
    """Saves conversation to database."""
    try:
        supabase.table("chat_logs").insert({
            "user_id": user_id,
            "role": role,
            "message": message
        }).execute()
    except Exception:
        pass

# --- THE CORE BRAIN: REWRITE QUERY ---
def contextualize_query(history, new_query):
    """
    If user says "Explain its structure", this function looks at history 
    and rewrites it to "Explain the structure of 1910 reforms".
    """
    if not history:
        return new_query
    
    history_text = "\n".join([f"{msg['role']}: {msg['message']}" for msg in history])
    
    prompt = f"""
    Conversation History:
    {history_text}
    
    User's New Input: "{new_query}"
    
    TASK: Rewrite the User's New Input to be a standalone question that makes sense without the history. 
    Replace words like "it", "that", "ehi", "eke", "mokakda" with the actual subject from history.
    If the input is already clear, return it as is.
    ONLY return the rewritten query.
    """
    
    try:
        resp = model.generate_content(prompt)
        rewritten = resp.text.strip()
        print(f"🔄 Query Rewritten: '{new_query}' -> '{rewritten}'")
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
        # Step 1: Query Contextualization (The "Memory" Part)
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
        print(f"📚 Subject: {detected_subject} | 🔍 Search Query: {search_query}")

        # Step 4: Retrieval (RAG) using the REWRITTEN query
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

        # 🔥 Step 6: The "Marking Scheme" Personality (STRICTER VERSION)
        system_instruction = f"""
        You are 'My Guru', an expert Sri Lankan O/L Teacher.
        User Language: {user_details.get('language', 'Sinhala')}
        Source Found: {source_found}

        TASK: Answer the student's question based strictly on the provided sources, formatted like a **Model Answer (Marking Scheme)**.

        ⛔ PROHIBITIONS:
        - DO NOT say "I will tell you what I know".
        - DO NOT refer to page numbers (e.g., "Check page 132").
        - DO NOT make up facts if the source is missing.

        ✅ ANSWERING RULES:
        1. **STRICT SOURCE USAGE:** - You MUST derive your answer *primarily* from the [SOURCE] context.
           - Use the EXACT technical terms (Pari Bhashika Wachana) found in the text.
        
        2. **IF SOURCE IS MISSING:**
           - You MUST explicitly state: "පුතේ, මගේ Database එකේ (පෙළ පොත්වල) මේ ගැන කරුණු සඳහන් වෙලා නෑ. හැබැයි O/L විෂය නිර්දේශයට අනුව පිළිතුර මෙයයි:"
           - Then provide the accurate O/L standard answer from general knowledge.

        3. **FORMATTING (Marking Scheme Style):**
           - Start with a direct answer or definition.
           - Use **Bullet Points** for list items.
           - Use **Bold** for keywords.
           - Add empty lines between points for readability (Space out the answer).
           - Use emojis (📚, ✅, 🧠) to make it friendly but professional.

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
            
            # 1. Get/Create User
            user_response = supabase.table("users").select("*").eq("phone_number", phone).execute()
            if not user_response.data:
                supabase.table("users").insert({"phone_number": phone, "setup_stage": "language"}).execute()
                whatsapp_utils.send_interactive_buttons(phone, "Welcome to My Guru! 🎓\nSelect your language:", {"sin": "සිංහල", "eng": "English"})
                return {"status": "ok"}

            user = user_response.data[0]
            stage = user.get('setup_stage')

            # 2. Logic Flow
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
                
                # --- UNLIMITED QUESTIONS (No Credit Check) ---
                
                # Fetch History for Context
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
                    
                    # Save Conversation to History
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