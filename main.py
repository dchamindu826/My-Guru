import os
import io
from fastapi import FastAPI, Request, HTTPException
from supabase import create_client
import google.generativeai as genai
import whatsapp_utils
from dotenv import load_dotenv
import PIL.Image

load_dotenv()

app = FastAPI(docs_url=None, redoc_url=None)

# Configs
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Make sure this matches EXACTLY with what you put in Meta Dashboard
VERIFY_TOKEN = "myguru_secure_token_2026" 

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)

# Gemini Model Setup
model = genai.GenerativeModel('gemini-2.0-flash')

# --- RAG FUNCTION (SMART) ---
def get_ai_response(user_input, language, subject, media_data=None, media_type=None):
    
    context_text = ""
    prompt_parts = []
    
    # 1. Text Query
    if media_type == "text" and user_input:
        embedding = genai.embed_content(
            model="models/text-embedding-004",
            content=user_input,
            task_type="retrieval_query"
        )['embedding']

        response = supabase.rpc("match_documents", {
            "query_embedding": embedding,
            "match_threshold": 0.4,
            "match_count": 4
        }).execute()
        
        # Check if data exists
        if response.data:
            context_text = "\n\n".join([doc['content'] for doc in response.data])
            prompt_parts.append(f"CONTEXT FROM TEXTBOOK:\n{context_text}")
        
        prompt_parts.append(f"USER QUESTION: {user_input}")

    # 2. Image
    elif media_type == "image":
        image = PIL.Image.open(io.BytesIO(media_data))
        prompt_parts.append("Analyze this image given by the student.")
        prompt_parts.append(image)
        if user_input: prompt_parts.append(f"User Question about image: {user_input}")

    # 3. Audio
    elif media_type == "audio":
        prompt_parts.append({"mime_type": "audio/ogg", "data": media_data})
        prompt_parts.append("Listen to this student's question and answer it.")

    # System Prompt
    system_instruction = f"""
    You are 'My Guru', a friendly AI teacher for Sri Lankan {subject} students.
    Language Mode: {language}
    
    INSTRUCTIONS:
    1. Answer accurately based on the Sri Lankan School Syllabus.
    2. If context is provided, prioritize it.
    3. If it's an image/voice, analyze it and give a helpful explanation.
    4. Keep answers clear, encouraging, and simple.
    """
    
    full_prompt = [system_instruction] + prompt_parts
    ai_resp = model.generate_content(full_prompt)
    return ai_resp.text

# --- ROUTES ---

@app.get("/")
async def home():
    return {"status": "Active", "message": "My Guru V2 is Ready!"}

# --- MEKA THAMA WENAS KARA PART EKA (/api/webhook) ---
@app.get("/api/webhook")
async def verify_webhook(request: Request):
    # Verify Token check
    hub_mode = request.query_params.get("hub.mode")
    hub_token = request.query_params.get("hub.verify_token")
    hub_challenge = request.query_params.get("hub.challenge")

    if hub_mode == "subscribe" and hub_token == VERIFY_TOKEN:
        print("WEBHOOK_VERIFIED")
        return int(hub_challenge)
    
    raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/api/webhook")
async def handle_message(request: Request):
    data = await request.json()
    try:
        # Check if valid entry exists
        if not data.get('entry'):
             return {"status": "ignored"}

        entry = data['entry'][0]['changes'][0]['value']
        
        if 'messages' in entry:
            msg = entry['messages'][0]
            phone = msg['from']
            msg_type = msg['type']
            
            # User Status Check
            user_data = supabase.table("users").select("*").eq("phone_number", phone).execute()
            
            if not user_data.data:
                # 1. New User -> Welcome
                supabase.table("users").insert({"phone_number": phone, "setup_stage": "new"}).execute()
                whatsapp_utils.send_interactive_buttons(
                    phone, 
                    "ආයුබෝවන්! මම My Guru. 🎓\nඔයාගේ ඉගෙනුම් සහායකයා.\n\nකරුණාකර භාෂාවක් තෝරන්න:",
                    {"sin": "සිංහල", "eng": "English"}
                )
                return {"status": "ok"}

            user = user_data.data[0]
            stage = user['setup_stage']
            
            # --- INTERACTIVE BUTTON/LIST RESPONSES ---
            if msg_type == "interactive":
                inter_type = msg['interactive']['type']
                selection_id = ""
                
                if inter_type == "button_reply":
                    selection_id = msg['interactive']['button_reply']['id']
                elif inter_type == "list_reply":
                    selection_id = msg['interactive']['list_reply']['id']

                # Stage 1: Language Selected -> Ask Exam
                if stage == "new":
                    lang = "Sinhala" if selection_id == "sin" else "English"
                    supabase.table("users").update({"language": lang, "setup_stage": "language_set"}).eq("phone_number", phone).execute()
                    
                    text_msg = "නියමයි! ඔයාගේ විභාගය මොකක්ද?" if lang == "Sinhala" else "Great! Select your Exam:"
                    whatsapp_utils.send_interactive_buttons(phone, text_msg, {"ol": "O/L (සාමාන්‍ය පෙළ)", "al": "A/L (උසස් පෙළ)"})

                # Stage 2: Exam Selected -> Ask Subject (LIST MESSAGE)
                elif stage == "language_set":
                    exam = "O/L" if selection_id == "ol" else "A/L"
                    supabase.table("users").update({"exam_level": exam, "setup_stage": "exam_set"}).eq("phone_number", phone).execute()
                    
                    sections = [{
                        "title": "ප්‍රධාන විෂයන්",
                        "rows": [
                            {"id": "sci", "title": "Science (විද්‍යාව)"},
                            {"id": "math", "title": "Mathematics (ගණිතය)"},
                            {"id": "sin", "title": "Sinhala (සිංහල)"},
                            {"id": "eng", "title": "English (ඉංග්‍රීසි)"},
                            {"id": "hist", "title": "History (ඉතිහාසය)"},
                            {"id": "bud", "title": "Buddhism (බුද්ධාගම)"},
                            {"id": "tech", "title": "Elec. Technology"},
                            {"id": "ict", "title": "ICT"},
                            {"id": "comm", "title": "Commerce"},
                            {"id": "art", "title": "Arts"}
                        ]
                    }]
                    
                    msg_text = "කරුණාකර ඔයාගේ විෂය තෝරන්න 👇"
                    btn_text = "විෂයන් ලැයිස්තුව"
                    whatsapp_utils.send_interactive_list(phone, msg_text, btn_text, sections)

                # Stage 3: Subject Selected -> Ready
                elif stage == "exam_set":
                    subject_map = {"sci": "Science", "math": "Mathematics", "tech": "Electrical Technology"} 
                    subject = subject_map.get(selection_id, "General Subject")
                    
                    supabase.table("users").update({"subject": subject, "setup_stage": "completed"}).eq("phone_number", phone).execute()
                    
                    welcome_txt = f"අපි {subject} ඉගෙන ගමු! 📚\nදැන් ඔයාට:\n✅ ප්‍රශ්න Type කරන්න\n✅ ගණන් වල ෆොටෝ එවන්න\n✅ Voice මැසේජ් එවන්න පුළුවන්."
                    whatsapp_utils.send_whatsapp_message(phone, welcome_txt)

            # --- Q&A MODE (TEXT / IMAGE / AUDIO) ---
            elif stage == "completed":
                
                # 1. Text Message
                if msg_type == "text":
                    user_query = msg['text']['body']
                    response = get_ai_response(user_query, user['language'], user['subject'], media_type="text")
                    whatsapp_utils.send_whatsapp_message(phone, response)

                # 2. Image Message
                elif msg_type == "image":
                    whatsapp_utils.send_whatsapp_message(phone, "බලමින් පවතී... 🖼️")
                    image_id = msg['image']['id']
                    caption = msg['image'].get('caption', "") 
                    
                    media_url = whatsapp_utils.get_media_url(image_id)
                    if media_url:
                        media_data = whatsapp_utils.download_media_file(media_url)
                        response = get_ai_response(caption, user['language'], user['subject'], media_data=media_data, media_type="image")
                        whatsapp_utils.send_whatsapp_message(phone, response)

                # 3. Audio Message (Voice Note)
                elif msg_type == "audio":
                    whatsapp_utils.send_whatsapp_message(phone, "අහමින් පවතී... 🎧")
                    audio_id = msg['audio']['id']
                    
                    media_url = whatsapp_utils.get_media_url(audio_id)
                    if media_url:
                        media_data = whatsapp_utils.download_media_file(media_url)
                        response = get_ai_response("", user['language'], user['subject'], media_data=media_data, media_type="audio")
                        whatsapp_utils.send_whatsapp_message(phone, response)

    except Exception as e:
        print(f"Error: {e}")
        # Error ekak awoth 200 ma yawanna one, nathnam WhatsApp retry karanawa digatama
        return {"status": "error", "message": str(e)}

    return {"status": "ok"}