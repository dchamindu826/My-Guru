import os
from fastapi import FastAPI, Request
from supabase import create_client
import google.generativeai as genai
import whatsapp_utils
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Configs
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
VERIFY_TOKEN = "my_guru_secret_token_2026"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- RAG FUNCTION ---
def get_ai_response(user_query, language):
    embedding = genai.embed_content(
        model="models/text-embedding-004",
        content=user_query,
        task_type="retrieval_query"
    )['embedding']

    response = supabase.rpc("match_documents", {
        "query_embedding": embedding,
        "match_threshold": 0.5,
        "match_count": 3
    }).execute()

    context_text = "\n\n".join([doc['content'] for doc in response.data])

    system_instruction = f"""
    You are 'My Guru', a friendly AI teacher for Sri Lankan students.
    CONTEXT: {context_text}
    QUESTION: {user_query}
    LANGUAGE: {language}
    
    INSTRUCTIONS:
    1. Answer ONLY from context.
    2. Respond in {language} (Sinhala/English).
    3. Keep it simple and short.
    """
    ai_resp = model.generate_content(system_instruction)
    return ai_resp.text

@app.get("/")
async def home():
    return {"status": "Active", "message": "My Guru is Running!"}

@app.get("/webhook")
async def verify_webhook(request: Request):
    if request.query_params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(request.query_params.get("hub.challenge"))
    return {"status": "error"}

@app.post("/webhook")
async def handle_message(request: Request):
    data = await request.json()
    try:
        entry = data['entry'][0]['changes'][0]['value']
        if 'messages' in entry:
            msg = entry['messages'][0]
            phone = msg['from']
            text = msg['text']['body'].strip() if 'text' in msg else ""
            
            # User Status Check
            user_data = supabase.table("users").select("*").eq("phone_number", phone).execute()
            
            if not user_data.data:
                # 1. New User -> Ask Language
                supabase.table("users").insert({"phone_number": phone, "setup_stage": "new"}).execute()
                whatsapp_utils.send_whatsapp_message(phone, 
                    "ආයුබෝවන්! My Guru වෙත සාදරයෙන් පිළිගනිමු. 🙏\n\nභාෂාවක් තෝරා ගැනීමට අංකය එවන්න:\n1️⃣ සිංහල\n2️⃣ English")
                return {"status": "ok"}

            user = user_data.data[0]
            stage = user['setup_stage']

            # --- SETUP FLOW (By Numbers) ---
            if stage == "new":
                if text == "1":
                    supabase.table("users").update({"language": "Sinhala", "setup_stage": "language_set"}).eq("phone_number", phone).execute()
                    whatsapp_utils.send_whatsapp_message(phone, "නියමයි! ඔයාගේ විභාගය තෝරන්න:\n\n1️⃣ සාමාන්‍ය පෙළ (O/L)\n2️⃣ උසස් පෙළ (A/L)")
                elif text == "2":
                    supabase.table("users").update({"language": "English", "setup_stage": "language_set"}).eq("phone_number", phone).execute()
                    whatsapp_utils.send_whatsapp_message(phone, "Great! Select your exam:\n\n1️⃣ O/L\n2️⃣ A/L")
                else:
                    whatsapp_utils.send_whatsapp_message(phone, "කරුණාකර 1 හෝ 2 අංකය එවන්න.\nPlease reply with 1 or 2.")

            elif stage == "language_set":
                # Exam Selection
                if text == "1":
                    exam = "O/L"
                    supabase.table("users").update({"exam_level": exam, "setup_stage": "exam_set"}).eq("phone_number", phone).execute()
                    msg = "දැන් විෂය තෝරන්න:\n\n1️⃣ විදුලි තාක්ෂණවේදය (Electrical Tech)" if user['language'] == "Sinhala" else "Select Subject:\n\n1️⃣ Electrical Technology"
                    whatsapp_utils.send_whatsapp_message(phone, msg)
                elif text == "2":
                    exam = "A/L"
                    supabase.table("users").update({"exam_level": exam, "setup_stage": "exam_set"}).eq("phone_number", phone).execute()
                    msg = "දැන් විෂය තෝරන්න:\n\n1️⃣ විදුලි තාක්ෂණවේදය (Electrical Tech)" if user['language'] == "Sinhala" else "Select Subject:\n\n1️⃣ Electrical Technology"
                    whatsapp_utils.send_whatsapp_message(phone, msg)
                else:
                    whatsapp_utils.send_whatsapp_message(phone, "1 හෝ 2 එවන්න. / Reply 1 or 2.")

            elif stage == "exam_set":
                # Subject Selection
                if text == "1":
                    supabase.table("users").update({"subject": "Electrical Technology", "setup_stage": "completed"}).eq("phone_number", phone).execute()
                    msg = "සැකසුම් අවසන්! ✅\nදැන් ඔයාට පාඩමේ ඕනෑම දෙයක් මගෙන් අහන්න පුළුවන්." if user['language'] == "Sinhala" else "Setup Complete! ✅\nYou can now ask me anything from the lesson."
                    whatsapp_utils.send_whatsapp_message(phone, msg)
                else:
                    whatsapp_utils.send_whatsapp_message(phone, "1 එවන්න. / Reply 1.")

            elif stage == "completed":
                # --- Q&A MODE ---
                response = get_ai_response(text, user['language'])
                whatsapp_utils.send_whatsapp_message(phone, response)

    except Exception as e:
        print(f"Error: {e}")

    return {"status": "ok"}