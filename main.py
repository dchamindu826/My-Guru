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
print("🚀 Starting Smart Guru Brain (HYBRID SEARCH MODE)...")
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
        response = supabase.table("chat_logs").select("role, message").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
        return response.data[::-1] if response.data else []
    except:
        return []

def save_chat_log(user_id, role, message):
    try:
        supabase.table("chat_logs").insert({"user_id": user_id, "role": role, "message": message}).execute()
    except:
        pass

# --- TRANSLATOR & KEYWORD EXTRACTOR ---
def optimize_search_query(history, raw_input):
    """
    Translates Singlish to Sinhala AND extracts specific keywords for SQL search.
    """
    history_text = "\n".join([f"{msg['role']}: {msg['message']}" for msg in history]) if history else ""
    prompt = f"""
    Context: {history_text}
    User Input: "{raw_input}"
    
    TASK: 
    1. Translate user input to 'Sinhala' (Textbook Terms).
    2. Identify the MOST IMPORTANT specific keyword for a strict search (e.g. "ගුණාත්මකභාවය").
    
    OUTPUT JSON: {{"translated": "...", "keyword": "..."}}
    """
    try:
        resp = model.generate_content(prompt)
        text = resp.text.strip().replace("```json", "").replace("```", "")
        return json.loads(text)
    except:
        return {"translated": raw_input, "keyword": ""}

# --- MAIN AI RESPONSE GENERATOR ---
def get_ai_response(user_input, user_details, history, media_data=None, media_type=None):
    try:
        # 1. Query Processing
        optimized_data = {"translated": user_input, "keyword": ""}
        if media_type == "text":
            optimized_data = optimize_search_query(history, user_input)
        
        search_query = optimized_data["translated"]
        strict_keyword = optimized_data["keyword"]
        
        print(f"🔍 Vector Search: '{search_query}'")
        print(f"🔑 Keyword Search: '{strict_keyword}'")

        if media_type == "image":
            image = PIL.Image.open(io.BytesIO(media_data))
            vision_resp = model.generate_content(["Extract text.", image])
            search_query += f" {vision_resp.text}"

        # 2. HYBRID SEARCH STRATEGY
        unique_docs = {}

        # A. Vector Search (Semantic)
        embedding = genai.embed_content(model="models/text-embedding-004", content=search_query, task_type="retrieval_query")['embedding']
        vector_res = supabase.rpc("match_documents", {
            "query_embedding": embedding,
            "match_threshold": 0.1, # Very low threshold to catch everything
            "match_count": 20,
            "filter": {}
        }).execute()
        
        for doc in vector_res.data:
            unique_docs[doc['id']] = doc

        # B. Keyword Search (Exact Match - The Fix!)
        # If we have a strong keyword like "ගුණාත්මකභාවය", we force a search for it.
        if strict_keyword and len(strict_keyword) > 2:
            print(f"🚀 Running Strict Search for: {strict_keyword}")
            keyword_res = supabase.table("documents").select("*").ilike("content", f"%{strict_keyword}%").limit(10).execute()
            
            for doc in keyword_res.data:
                # Add to list if not already there
                if doc['id'] not in unique_docs:
                    print(f"➕ Added Page {doc['metadata'].get('page')} via Keyword Search")
                    unique_docs[doc['id']] = doc

        # 3. Construct Context
        docs_list = list(unique_docs.values())
        source_found = False
        context_text = ""
        
        if docs_list:
            source_found = True
            # Sort by page number to make reading logical
            docs_list.sort(key=lambda x: x['metadata'].get('page', 0))
            
            found_pages = [d['metadata'].get('page') for d in docs_list]
            print(f"✅ Final Pages Used: {found_pages}")
            
            context_text = "\n\n".join([f"SOURCE (Page {d['metadata'].get('page')}):\n{d['content']}" for d in docs_list])

        # 4. Generate Answer
        system_instruction = f"""
        You are 'My Guru', a Sri Lankan O/L Teacher.
        User Language: {user_details.get('language', 'Sinhala')}
        Source Found: {source_found}

        TASK: Answer strictly based on the [SOURCE] text provided.

        RULES:
        1. **SCAN ALL PAGES:** The answer might be in a page added via keyword search (e.g. Page 10-20). Look closely.
        2. **LISTS:** If the user asks for "Lakshana" (Characteristics) and there is a bulleted list in the source, COPY IT EXACTLY.
        3. **NO HALLUCINATIONS:** Only use provided text.
        4. **FORMAT:** Bullet points, Bold keys.

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
            
            user_response = supabase.table("users").select("*").eq("phone_number", phone).execute()
            if not user_response.data:
                supabase.table("users").insert({"phone_number": phone, "setup_stage": "language"}).execute()
                whatsapp_utils.send_interactive_buttons(phone, "Welcome! Select Language:", {"sin": "සිංහල", "eng": "English"})
                return {"status": "ok"}

            user = user_response.data[0]
            stage = user.get('setup_stage')

            if stage == "language":
                if msg_type == "interactive":
                    lang = "Sinhala" if msg['interactive']['button_reply']['id'] == "sin" else "English"
                    supabase.table("users").update({"language": lang, "setup_stage": "active"}).eq("phone_number", phone).execute()
                    whatsapp_utils.send_whatsapp_message(phone, "හරි පුතේ! O/L පටන් ගමු. කැමති ප්‍රශ්නයක් අහන්න. 📚")
                else:
                    whatsapp_utils.send_interactive_buttons(phone, "Select Language:", {"sin": "සිංහල", "eng": "English"})
            elif stage == "level":
                 supabase.table("users").update({"setup_stage": "active"}).eq("phone_number", phone).execute()
                 whatsapp_utils.send_whatsapp_message(phone, "හරි පුතේ! O/L පටන් ගමු. කැමති ප්‍රශ්නයක් අහන්න. 📚")
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