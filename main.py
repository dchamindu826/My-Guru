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

# Credit System Config
FREE_LIMIT = 10 

# --- INITIALIZATION LOGS ---
print("🚀 Starting Server...")
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
    print("✅ Services Initialized Successfully!")
except Exception as e:
    print(f"❌ Initialization Error: {e}")

SUBJECT_MAP = {
    "1": "Sinhala", "2": "Mathematics", "3": "Science",
    "4": "History", "5": "Health", "6": "English"
}

# --- SMART ROUTER ---
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
        print(f"🧠 AI Processing: {user_input[:20]}...")
        query_text = user_input
        language = user_details.get('language', 'Sinhala')
        
        if media_type == "image":
            print("🖼️ Analyzing Image...")
            image = PIL.Image.open(io.BytesIO(media_data))
            vision_resp = model.generate_content(["Describe this educational image in detail using strict academic terminology.", image])
            query_text = vision_resp.text
        
        detected_subject = detect_subject_and_query(query_text)
        print(f"📚 Detected Subject: {detected_subject}")

        # Search
        embedding = genai.embed_content(model="models/text-embedding-004", content=query_text, task_type="retrieval_query")['embedding']
        
        rpc_params = {
            "query_embedding": embedding,
            "match_threshold": 0.28,
            "match_count": 8,
            "filter": {"subject": detected_subject}
        }
        if detected_subject == "General": del rpc_params["filter"]

        response = supabase.rpc("match_documents", rpc_params).execute()
        
        if not response.data and detected_subject != "General":
            print("🔄 Switching to Global Search...")
            del rpc_params["filter"]
            response = supabase.rpc("match_documents", rpc_params).execute()

        context_text = ""
        source_found = False
        if response.data:
            source_found = True
            context_text = "\n\n".join([f"[SOURCE START]\n{doc['content']}\n[SOURCE END]" for doc in response.data])

        # 🔥 UPDATED SYSTEM INSTRUCTION (Strict Textbook Terminology)
        system_instruction = f"""
        You are 'My Guru', a friendly and expert Sri Lankan O/L teacher.
        User Language: {language}
        Source Found: {source_found}

        RULES FOR ANSWERING:
        1. **STRICT TEXTBOOK TERMINOLOGY:** You MUST use the exact technical terms (පාරිභාෂික වචන) found in the [SOURCE] context. 
           - Do NOT use synonyms or direct translations if they differ from the source.
           - Example: If source says "අන්තර්හාර නියුරෝන", use THAT. Do NOT use "අන්තර් ස්නායු සෛල".
        
        2. **TONE & STYLE:** - Always address the student as "පුතේ" (Puthe).
           - Be encouraging and kind. 
           - Use relevant Emojis (📚, 🧠, ✅, 🔬) to make the message attractive.
           - Structure the answer with Bullet Points for readability.

        3. **CONTENT FIDELITY:** - Base your answer ONLY on the provided [SOURCE] context.
           - If the user's question is unclear/Singlish, understand the INTENT but reply in correct Sinhala/English based on the textbook.

        4. **MISSING INFO:**
           - If 'Source Found' is False, politely say: "පුතේ, මේ කරුණු මගේ පොත්වල (Database) දැනට සටහන් වෙලා නෑ. හැබැයි මම දන්න විදියට..." and then give a general correct answer.

        CONTEXT FROM TEXTBOOK:
        {context_text}
        """
        
        prompt_parts = [system_instruction]
        if media_type == "image": prompt_parts.append(PIL.Image.open(io.BytesIO(media_data)))
        prompt_parts.append(f"Student Question: {query_text}")

        final_resp = model.generate_content(prompt_parts)
        print("✅ Answer Generated!")
        return final_resp.text.strip()

    except Exception as e:
        print(f"❌ AI Error: {e}")
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
    try:
        data = await request.json()
        print(f"🔔 Webhook Data: {json.dumps(data)}")

        if not data.get('entry'): return {"status": "ignored"}
        entry = data['entry'][0]['changes'][0]['value']
        
        if 'messages' in entry:
            msg = entry['messages'][0]
            phone = msg['from']
            msg_type = msg['type']
            print(f"📩 Message from {phone} | Type: {msg_type}")
            
            # 1. User Check
            user_response = supabase.table("users").select("*").eq("phone_number", phone).execute()
            
            if not user_response.data:
                print("🆕 New User Detected!")
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
            print(f"👤 User Stage: {stage}")

            # --- LOGIC FLOW ---
            if stage == "language":
                if msg_type == "interactive":
                    selection = msg['interactive']['button_reply']['id']
                    lang = "Sinhala" if selection == "sin" else "English"
                    supabase.table("users").update({"language": lang, "setup_stage": "level"}).eq("phone_number", phone).execute()
                    
                    msg_text = "හොඳයි පුතේ! ඔයා සූදානම් වෙන්නේ මොන විභාගයටද?" if lang == "Sinhala" else "Great! Which exam are you preparing for?"
                    whatsapp_utils.send_interactive_buttons(phone, msg_text, {"ol": "O/L", "al": "A/L"})
                else:
                    # Fix: Re-send buttons if text is sent
                    whatsapp_utils.send_interactive_buttons(phone, "Welcome to My Guru! 🎓\nSelect your language:", {"sin": "සිංහල", "eng": "English"})

            elif stage == "level":
                if msg_type == "interactive":
                    level = msg['interactive']['button_reply']['id']
                    if level == "ol":
                        supabase.table("users").update({"grade": "O/L", "setup_stage": "subject_select"}).eq("phone_number", phone).execute()
                        sub_msg = "පුතේ, ඔයාට අවශ්‍ය විෂය අංකය එවන්න:\n\n1️⃣ සිංහල (Sinhala)\n2️⃣ ගණිතය (Mathematics)\n3️⃣ විද්‍යාව (Science)\n4️⃣ ඉතිහාසය (History)\n5️⃣ සෞඛ්‍යය (Health)\n6️⃣ ඉංග්‍රීසි (English)"
                        whatsapp_utils.send_whatsapp_message(phone, sub_msg)
                    else:
                        whatsapp_utils.send_whatsapp_message(phone, "සමාවෙන්න පුතේ, දැනට අපි උදව් කරන්නේ O/L වලට විතරයි. 🔜")
                else:
                    whatsapp_utils.send_interactive_buttons(phone, "Select your exam:", {"ol": "O/L", "al": "A/L"})

            elif stage == "subject_select":
                if msg_type == "text":
                    selection = msg['text']['body'].strip()
                    subject = SUBJECT_MAP.get(selection)
                    if subject:
                        supabase.table("users").update({"current_subject": subject, "setup_stage": "active"}).eq("phone_number", phone).execute()
                        whatsapp_utils.send_whatsapp_message(phone, f"හරි! අපි {subject} පාඩම් පටන් ගමු. 📚")
                    else:
                        whatsapp_utils.send_whatsapp_message(phone, "පුතේ, අදාල අංකය (1-6) පමණක් එවන්න. 👇")

            elif stage == "active":
                print("🎓 Processing Question...")
                
                # Credit Check
                if not user.get('is_paid', False) and user.get('question_count', 0) >= FREE_LIMIT:
                     whatsapp_utils.send_whatsapp_message(phone, "පුතේ, ඔයාගේ Free ප්‍රශ්න ගණන ඉවරයි. 😔")
                     return {"status": "ok"}

                response = None
                if msg_type == "text":
                    response = get_ai_response(msg['text']['body'], user, media_type="text")
                # Image/Audio logic here if needed

                if response:
                    print(f"📤 Sending Reply: {response[:20]}...")
                    whatsapp_utils.send_whatsapp_message(phone, response)
                    new_count = user.get('question_count', 0) + 1
                    supabase.table("users").update({"question_count": new_count}).eq("phone_number", phone).execute()

    except Exception as e:
        print(f"❌ Critical Error in handle_message: {e}")
        traceback.print_exc()

    return {"status": "ok"}