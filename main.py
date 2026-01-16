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
model = genai.GenerativeModel('gemini-2.0-flash')

# --- RAG FUNCTION ---
def get_ai_response(user_query, language):
    # 1. Embed Query
    embedding = genai.embed_content(
        model="models/text-embedding-004",
        content=user_query,
        task_type="retrieval_query"
    )['embedding']

    # 2. Search Supabase
    response = supabase.rpc("match_documents", {
        "query_embedding": embedding,
        "match_threshold": 0.5,
        "match_count": 3
    }).execute()

    context_text = "\n\n".join([doc['content'] for doc in response.data])

    # 3. Generate Answer
    system_instruction = f"""
    You are 'My Guru', a friendly and simple AI teacher for Sri Lankan students.
    
    CONTEXT from textbook:
    {context_text}
    
    USER QUESTION: {user_query}
    SELECTED LANGUAGE: {language}
    
    INSTRUCTIONS:
    1. Answer ONLY based on the CONTEXT provided.
    2. Respond in the SELECTED LANGUAGE ({language}). 
       - If Sinhala: Use simple, natural Sinhala (not overly formal).
       - If English: Use simple English.
    3. Be kind and helpful. Keep answers short and clear.
    4. If the answer is not in the context, say "Sorry, that isn't in the lesson I learned yet." in the selected language.
    """
    
    ai_resp = model.generate_content(system_instruction)
    return ai_resp.text

# --- WEBHOOK ---
@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)
    return {"status": "error"}

@app.post("/webhook")
async def handle_message(request: Request):
    data = await request.json()
    
    try:
        entry = data['entry'][0]['changes'][0]['value']
        
        if 'messages' in entry:
            msg = entry['messages'][0]
            phone_number = msg['from']
            msg_type = msg['type']
            
            # 1. Check User State in Database
            user_data = supabase.table("users").select("*").eq("phone_number", phone_number).execute()
            
            if not user_data.data:
                # New User -> Register & Ask Language
                supabase.table("users").insert({"phone_number": phone_number, "setup_stage": "new"}).execute()
                whatsapp_utils.send_buttons(phone_number, "ආයුබෝවන්! My Guru වෙත සාදරයෙන් පිළිගනිමු. \nභාෂාවක් තෝරන්න / Select Language:", 
                                            {"sin": "Sinhala", "eng": "English"})
                return {"status": "ok"}

            user = user_data.data[0]
            stage = user['setup_stage']

            # --- HANDLE BUTTON CLICKS ---
            if msg_type == "interactive":
                selection_id = msg['interactive']['button_reply']['id']
                
                if stage == "new":
                    # Language Selected -> Ask Exam
                    lang = "Sinhala" if selection_id == "sin" else "English"
                    supabase.table("users").update({"language": lang, "setup_stage": "language_set"}).eq("phone_number", phone_number).execute()
                    
                    msg_text = "නියමයි! ඔයාගේ විභාගය මොකක්ද?" if lang == "Sinhala" else "Great! What is your exam?"
                    whatsapp_utils.send_buttons(phone_number, msg_text, {"ol": "O/L", "al": "A/L"})
                
                elif stage == "language_set":
                    # Exam Selected -> Ask Subject
                    exam = "O/L" if selection_id == "ol" else "A/L"
                    supabase.table("users").update({"exam_level": exam, "setup_stage": "exam_set"}).eq("phone_number", phone_number).execute()
                    
                    lang = user['language']
                    msg_text = "දැන් විෂය තෝරන්න:" if lang == "Sinhala" else "Now select the subject:"
                    # දැනට අපිට තියෙන්නේ Elec Tech විතරයි
                    whatsapp_utils.send_buttons(phone_number, msg_text, {"et": "Electrical Tech"})

                elif stage == "exam_set":
                    # Subject Selected -> Finish Setup
                    subject = "Electrical Technology"
                    supabase.table("users").update({"subject": subject, "setup_stage": "completed"}).eq("phone_number", phone_number).execute()
                    
                    lang = user['language']
                    welcome_msg = "හරි! දැන් ඔයාට පුළුවන් පාඩමේ ඕනෑම දෙයක් මගෙන් අහන්න. මම ලෑස්තියි! 😊" if lang == "Sinhala" else "Done! You can now ask me anything from the lesson. I'm ready! 😊"
                    whatsapp_utils.send_whatsapp_message(phone_number, welcome_msg)

            # --- HANDLE TEXT MESSAGES (Q&A) ---
            elif msg_type == "text":
                if stage != "completed":
                    # If user types something before setup finishes
                    whatsapp_utils.send_whatsapp_message(phone_number, "Please select an option from the buttons above first.")
                else:
                    # RAG Process
                    user_query = msg['text']['body']
                    response = get_ai_response(user_query, user['language'])
                    whatsapp_utils.send_whatsapp_message(phone_number, response)

    except Exception as e:
        print(f"Error: {e}")

    return {"status": "ok"}