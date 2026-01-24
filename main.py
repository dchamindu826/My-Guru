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

load_dotenv()

app = FastAPI(docs_url=None, redoc_url=None)

# --- CONFIGURATIONS ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
VERIFY_TOKEN = "myguru_secure_token_2026"

# Credit System Config
FREE_LIMIT = 10 

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# Subject Mapping (අංකයට අදාල විෂය)
SUBJECT_MAP = {
    "1": "Sinhala",
    "2": "Mathematics",
    "3": "Science",
    "4": "History",
    "5": "Health",
    "6": "English"
}

# --- SMART ROUTER (විෂය හඳුනාගැනීම) ---
def detect_subject_and_query(user_input):
    prompt = f"""
    Analyze query: "{user_input}"
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

# --- AI RESPONSE GENERATOR ---
def get_ai_response(user_input, user_details, media_data=None, media_type=None):
    try:
        query_text = user_input
        language = user_details.get('language', 'Sinhala')
        
        # 1. Handle Media
        if media_type == "image":
            image = PIL.Image.open(io.BytesIO(media_data))
            vision_resp = model.generate_content(["Describe this educational image in detail.", image])
            query_text = vision_resp.text
        elif media_type == "audio":
            audio_resp = model.generate_content(["Transcribe audio to text.", {"mime_type": "audio/ogg", "data": media_data}])
            query_text = audio_resp.text

        # 2. Smart Search (Auto-detect Subject)
        detected_subject = detect_subject_and_query(query_text)
        print(f"🧠 Question Subject: {detected_subject}")

        # 3. Database Search (Prioritize Detected Subject)
        embedding = genai.embed_content(model="models/text-embedding-004", content=query_text, task_type="retrieval_query")['embedding']
        
        # A. Try searching within the DETECTED subject first
        rpc_params = {
            "query_embedding": embedding,
            "match_threshold": 0.28,
            "match_count": 8,
            "filter": {"subject": detected_subject}
        }
        
        if detected_subject == "General": del rpc_params["filter"] # General නම් ෆිල්ටර් එපා

        response = supabase.rpc("match_documents", rpc_params).execute()
        
        # B. If no results, Search GLOBALLY (Any subject)
        if not response.data and detected_subject != "General":
            print("🔄 Switching to Global Search...")
            del rpc_params["filter"]
            response = supabase.rpc("match_documents", rpc_params).execute()

        # 4. Prepare Context
        context_text = ""
        source_found = False
        if response.data:
            source_found = True
            context_text = "\n\n".join([f"[SOURCE: {doc['metadata'].get('source')}] {doc['content']}" for doc in response.data])

        # 5. Generate Answer (The Teacher Persona)
        system_instruction = f"""
        You are 'My Guru', a kind Sri Lankan O/L teacher.
        User Language: {language}
        Source Found: {source_found}

        RULES:
        1. **Tone:** Always address the student as "පුතේ" (Puthe). Be kind & guiding. NEVER use "Machan".
        2. **Syllabus:** Answer strictly within Sri Lankan O/L syllabus scope.
        3. **Source Usage:** - If 'Source Found' is True: Base answer on [SOURCE] context.
           - If 'Source Found' is False: Say "පුතේ, මේ කරුණු මගේ පොත්වල නම් නෑ. නමුත් මම දන්න විදියට..." (Son, not in books, but here is the answer...) and give a correct O/L level answer from general knowledge.
        4. **Bad Behavior:** If user is rude, gently correct them: "පුතේ, අපි ගුරුවරුන්ට එහෙම කතා කරන්නේ නෑ නේද? වැදගත් විදියට ප්‍රශ්නය අහන්න."
        5. **Formatting:** Use Emojis (📚, ✅). Keep it short (max 150 words). Use bullet points.

        CONTEXT:
        {context_text}
        """
        
        prompt_parts = [system_instruction]
        if media_type == "image": prompt_parts.append(PIL.Image.open(io.BytesIO(media_data)))
        prompt_parts.append(f"Question: {query_text}")

        final_resp = model.generate_content(prompt_parts)
        return final_resp.text.strip()

    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return "පුතේ, පොඩි තාක්ෂණික දෝෂයක්. ආයේ අහන්නකෝ. 🛠️"

# --- WEBHOOK ROUTES ---
@app.get("/api/webhook")
async def verify_webhook(request: Request):
    if request.query_params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(request.query_params.get("hub.challenge"))
    raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/api/webhook")
async def handle_message(request: Request):
    data = await request.json()
    try:
        if not data.get('entry'): return {"status": "ignored"}
        entry = data['entry'][0]['changes'][0]['value']
        
        if 'messages' in entry:
            msg = entry['messages'][0]
            phone = msg['from']
            msg_type = msg['type']
            
            # 1. User Fetch / Create
            user_response = supabase.table("users").select("*").eq("phone_number", phone).execute()
            
            if not user_response.data:
                # New User -> Start with Language Selection
                supabase.table("users").insert({
                    "phone_number": phone, 
                    "setup_stage": "language",
                    "question_count": 0,
                    "is_paid": False
                }).execute()
                whatsapp_utils.send_interactive_buttons(phone, "Welcome to My Guru! 🎓\nSelect your language:", {"sin": "සිංහල", "eng": "English"})
                return {"status": "ok"}

            user = user_response.data[0]
            stage = user.get('setup_stage')
            
            # --- ONBOARDING FLOW ---
            
            # Step 1: Language Selection
            if stage == "language":
                if msg_type == "interactive":
                    selection = msg['interactive']['button_reply']['id']
                    lang = "Sinhala" if selection == "sin" else "English"
                    supabase.table("users").update({"language": lang, "setup_stage": "level"}).eq("phone_number", phone).execute()
                    
                    msg_text = "හොඳයි පුතේ! ඔයා සූදානම් වෙන්නේ මොන විභාගයටද?" if lang == "Sinhala" else "Great! Which exam are you preparing for?"
                    whatsapp_utils.send_interactive_buttons(phone, msg_text, {"ol": "O/L", "al": "A/L"})
                else:
                    whatsapp_utils.send_whatsapp_message(phone, "Please select a language button. 👇")

            # Step 2: Level Selection
            elif stage == "level":
                if msg_type == "interactive":
                    level = msg['interactive']['button_reply']['id']
                    if level == "ol":
                        supabase.table("users").update({"grade": "O/L", "setup_stage": "subject_select"}).eq("phone_number", phone).execute()
                        
                        # Show Subject List
                        sub_msg = "පුතේ, ඔයාට අවශ්‍ය විෂය අංකය එවන්න:\n\n1️⃣ සිංහල (Sinhala)\n2️⃣ ගණිතය (Mathematics)\n3️⃣ විද්‍යාව (Science)\n4️⃣ ඉතිහාසය (History)\n5️⃣ සෞඛ්‍යය (Health)\n6️⃣ ඉංග්‍රීසි (English)"
                        whatsapp_utils.send_whatsapp_message(phone, sub_msg)
                    else:
                        whatsapp_utils.send_whatsapp_message(phone, "සමාවෙන්න පුතේ, දැනට අපි උදව් කරන්නේ O/L වලට විතරයි. 🔜")

            # Step 3: Subject Selection
            elif stage == "subject_select":
                if msg_type == "text":
                    selection = msg['text']['body'].strip()
                    subject = SUBJECT_MAP.get(selection)
                    
                    if subject:
                        supabase.table("users").update({"current_subject": subject, "setup_stage": "active"}).eq("phone_number", phone).execute()
                        whatsapp_utils.send_whatsapp_message(phone, f"හරි! අපි {subject} පාඩම් පටන් ගමු. 📚\n(ඕනෑම වෙලාවක වෙනත් විෂයක ප්‍රශ්නයක් වුනත් අහන්න පුළුවන්).")
                    else:
                        whatsapp_utils.send_whatsapp_message(phone, "පුතේ, අදාල අංකය (1-6) පමණක් එවන්න. 👇")

            # --- ACTIVE Q&A MODE ---
            elif stage == "active":
                
                # 1. Credit Check 💳
                if not user['is_paid'] and user['question_count'] >= FREE_LIMIT:
                    whatsapp_utils.send_whatsapp_message(phone, "පුතේ, ඔයාගේ Free ප්‍රශ්න ගණන (10) ඉවරයි. 😔\nදිගටම ඉගෙන ගන්න අපේ පැකේජ් එක Active කරගන්න.")
                    return {"status": "ok"}

                # 2. Process Input
                response = None
                if msg_type == "text":
                    response = get_ai_response(msg['text']['body'], user, media_type="text")
                elif msg_type == "image":
                    media_url = whatsapp_utils.get_media_url(msg['image']['id'])
                    if media_url:
                        media_data = whatsapp_utils.download_media_file(media_url)
                        response = get_ai_response(msg['image'].get('caption', ""), user, media_data=media_data, media_type="image")
                elif msg_type == "audio":
                    media_url = whatsapp_utils.get_media_url(msg['audio']['id'])
                    if media_url:
                        media_data = whatsapp_utils.download_media_file(media_url)
                        response = get_ai_response("", user, media_data=media_data, media_type="audio")

                # 3. Send & Update Count
                if response:
                    whatsapp_utils.send_whatsapp_message(phone, response)
                    # Increment Question Count
                    new_count = user['question_count'] + 1
                    supabase.table("users").update({"question_count": new_count}).eq("phone_number", phone).execute()

    except Exception as e:
        print(f"❌ Main Error: {e}")
        traceback.print_exc()

    return {"status": "ok"}