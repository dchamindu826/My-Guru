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
print("🚀 Starting Smart Guru Brain (Marking Scheme Mode)...")
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

# --- 🔥 THE TRANSLATOR BRAIN (Singlish -> Textbook Sinhala) ---
def optimize_search_query(history, raw_input):
    """
    Translates Singlish/English input into EXACT Sinhala Textbook terminology.
    """
    history_text = "\n".join([f"{msg['role']}: {msg['message']}" for msg in history]) if history else ""
    
    prompt = f"""
    Context: {history_text}
    User Input: "{raw_input}"
    
    TASK: Convert the User Input into a search query that matches a Sri Lankan O/L Textbook.
    
    RULES:
    1. If the input is in "Singlish" (e.g., "gunathmakabawaya"), TRANSLATE it to the official "Sinhala" term (e.g., "ගුණාත්මකභාවය").
    2. If the input asks for a list/features (e.g., "lakshana"), include the Sinhala word for it (e.g., "ලක්ෂණ").
    3. Remove unnecessary chat words ("mata kiyanna", "ane"). Keep only the KEYWORDS.
    
    Example:
    Input: "Mata kiynn health wala gunathmakabawaya ihala prajawaka dakiya haki lakshana"
    Output: "සෞඛ්‍යයේ ගුණාත්මකභාවය ඉහළ ප්‍රජාවක දැකිය හැකි ලක්ෂණ"

    RETURN ONLY THE TRANSLATED SINHALA QUERY.
    """
    
    try:
        resp = model.generate_content(prompt)
        optimized_query = resp.text.strip()
        print(f"🔄 Singlish: '{raw_input}' \n➡️ Sinhala Search: '{optimized_query}'")
        return optimized_query
    except:
        return raw_input

# --- SMART ROUTER ---
def detect_subject(query):
    # Shorten check for speed
    if any(x in query.lower() for x in ['sin', 'සිංහල']): return 'Sinhala'
    if any(x in query.lower() for x in ['sci', 'විද්‍යා']): return 'Science'
    if any(x in query.lower() for x in ['his', 'ඉතිහාස']): return 'History'
    
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
        # Step 1: Optimize Query (This fixes the Singlish issue)
        search_query = user_input
        if media_type == "text":
            search_query = optimize_search_query(history, user_input)
        
        # Step 2: Handle Images
        if media_type == "image":
            print("🖼️ Analyzing Image...")
            image = PIL.Image.open(io.BytesIO(media_data))
            vision_resp = model.generate_content(["Extract all text and explain diagrams in this image.", image])
            search_query += f" [Image Context: {vision_resp.text}]"

        # Step 3: Subject Detection
        detected_subject = detect_subject(search_query)
        print(f"📚 Subject: {detected_subject}")

        # Step 4: Retrieval (RAG)
        embedding = genai.embed_content(model="models/text-embedding-004", content=search_query, task_type="retrieval_query")['embedding']
        
        # Lower threshold slightly to catch more results
        rpc_params = {
            "query_embedding": embedding,
            "match_threshold": 0.25, 
            "match_count": 8,
            "filter": {"subject": detected_subject}
        }
        if detected_subject == "General": del rpc_params["filter"]

        response = supabase.rpc("match_documents", rpc_params).execute()
        
        # Fallback
        if not response.data and detected_subject != "General":
            print("🔄 Global Search Fallback...")
            if "filter" in rpc_params: del rpc_params["filter"]
            response = supabase.rpc("match_documents", rpc_params).execute()

        # Step 5: Construct Context
        source_found = False
        context_text = ""
        if response.data:
            source_found = True
            # Extract content clearly
            context_text = "\n\n".join([f"SOURCE ({doc.get('id')}):\n{doc['content']}" for doc in response.data])

        # 🔥 Step 6: THE MARKING SCHEME EXAMINER PROMPT
        system_instruction = f"""
        You are an expert Sri Lankan O/L Teacher behaving like a **Marking Scheme**.
        User Language: {user_details.get('language', 'Sinhala')}
        Source Found: {source_found}

        TASK: Answer the student's question based STRICTLY on the provided [SOURCE].

        ⛔ STRICT RULES:
        1. **NO FLUFF:** Do not say "Here is what I found" or "Check the book".
        2. **EXACT MATCH:** If the source lists points (e.g., features, reasons), you MUST list them exactly as they appear.
        3. **FORMATTING:** - Use **Bullet Points** (•) for every list item.
           - **Bold** the key terms.
           - Keep it clean and spaced out.
        4. **MISSING SOURCE:** - If source is NOT found, say: "පුතේ, පෙළ පොතේ (Database) මේ කොටස සොයාගැනීමට නොහැකි විය. නමුත් විෂය නිර්දේශයට අනුව පිළිතුර මෙයයි:" 
           - Then provide the accurate O/L answer from general knowledge.

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
            
            # User Check
            user_response = supabase.table("users").select("*").eq("phone_number", phone).execute()
            if not user_response.data:
                supabase.table("users").insert({"phone_number": phone, "setup_stage": "language"}).execute()
                whatsapp_utils.send_interactive_buttons(phone, "Welcome to My Guru! 🎓\nSelect your language:", {"sin": "සිංහල", "eng": "English"})
                return {"status": "ok"}

            user = user_response.data[0]
            stage = user.get('setup_stage')

            # Stage Handling
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
                    # Send straight to brain
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