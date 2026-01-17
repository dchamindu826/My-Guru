import os
import io
import traceback
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
VERIFY_TOKEN = "myguru_secure_token_2026"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash') # Speed & Accuracy

# --- SMART RAG FUNCTION ---
def get_ai_response(user_input, subject, media_data=None, media_type=None):
    try:
        context_text = ""
        prompt_parts = []
        
        # 1. Database Search (Strict)
        if media_type == "text" and user_input:
            # Query එක ටිකක් Modify කරනවා පාඩම් ගණන් අහනවද බලන්න
            search_query = user_input
            if "lessons" in user_input.lower() or "පාඩම්" in user_input:
                search_query += " content table list of lessons පටුන"

            embedding = genai.embed_content(
                model="models/text-embedding-004",
                content=search_query,
                task_type="retrieval_query"
            )['embedding']

            # Match Count එක වැඩි කරා (Lesson list එක ගන්න ලේසි වෙන්න)
            response = supabase.rpc("match_documents", {
                "query_embedding": embedding,
                "match_threshold": 0.35, # ටිකක් ලිහිල් කරා වැඩි විස්තර අහු වෙන්න
                "match_count": 6
            }).execute()
            
            if response.data:
                context_text = "\n\n".join([doc['content'] for doc in response.data])
                prompt_parts.append(f"STRICT CONTEXT FROM BOOKS:\n{context_text}")
            else:
                # ඩේටාබේස් එකේ නැත්නම් කෙලින්ම කියන්න ඕන
                return "පුතේ, මේ ප්‍රශ්නයට උත්තරේ මට දීලා තියෙන පොත්වල නෑ. වෙන එකක් අහන්න."

            prompt_parts.append(f"STUDENT QUESTION: {user_input}")

        elif media_type == "image":
            image = PIL.Image.open(io.BytesIO(media_data))
            prompt_parts.append("Analyze this textbook image.")
            prompt_parts.append(image)
            if user_input: prompt_parts.append(f"Question: {user_input}")

        elif media_type == "audio":
            prompt_parts.append({"mime_type": "audio/ogg", "data": media_data})
            prompt_parts.append("Answer this student's voice question.")

        # --- SYSTEM PROMPT (STRICT & SIMPLE) ---
        system_instruction = f"""
        You are a kind Sri Lankan teacher helping a student with {subject}.
        
        RULES:
        1. **ONLY use the provided 'STRICT CONTEXT FROM BOOKS'.** Do NOT use outside knowledge.
        2. If the answer is not in the context, say "පුතේ, ඒ ගැන පොතේ විස්තරයක් නෑ." (Don't make up answers).
        3. **Keep answers SHORT and SIMPLE.** No long paragraphs. Use bullet points if needed.
        4. Do NOT mention "According to the database" or "In the provided text". Just answer naturally like a human.
        5. If asked about "How many lessons", count them from the Table of Contents in the context and give the exact number.
        6. Language: Sinhala (Simple & Friendly). Start answers directly.
        """
        
        full_prompt = [system_instruction] + prompt_parts
        
        # Generate
        ai_resp = model.generate_content(full_prompt)
        return ai_resp.text.strip()

    except Exception as e:
        print(f"❌ AI Error: {e}")
        return "පොඩි ගැටළුවක් පුතේ. ආයේ අහන්නකෝ."

# --- WEBHOOK ROUTES ---
@app.get("/api/webhook")
async def verify_webhook(request: Request):
    hub_mode = request.query_params.get("hub.mode")
    hub_token = request.query_params.get("hub.verify_token")
    hub_challenge = request.query_params.get("hub.challenge")

    if hub_mode == "subscribe" and hub_token == VERIFY_TOKEN:
        return int(hub_challenge)
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
            
            # 1. User Status Check
            user_data = supabase.table("users").select("*").eq("phone_number", phone).execute()
            
            if not user_data.data:
                # --- STEP 1: WELCOME & EXAM SELECTION ---
                supabase.table("users").insert({"phone_number": phone, "setup_stage": "exam_select"}).execute()
                whatsapp_utils.send_interactive_buttons(
                    phone, 
                    "කොහොමද පුතේ? 😊\nඔයා ඉගෙන ගන්න විභාගය තෝරන්නකෝ:",
                    {"ol": "O/L (සාමාන්‍ය පෙළ)", "al": "A/L (උසස් පෙළ)"}
                )
                return {"status": "ok"}

            user = user_data.data[0]
            stage = user['setup_stage']

            # --- STEP 2: HANDLE EXAM SELECTION -> SHOW SUBJECTS ---
            if stage == "exam_select":
                if msg_type == "interactive":
                    selection_id = msg['interactive']['button_reply']['id']
                    
                    if selection_id == "ol":
                        # O/L තේරුවාම විෂයන් පෙන්වීම
                        supabase.table("users").update({"exam_level": "O/L", "setup_stage": "subject_select"}).eq("phone_number", phone).execute()
                        
                        # සරල ලිස්ට් එකක් (Text Message එකක් විදියට)
                        subject_msg = (
                            "හරි පුතේ, O/L විෂයක් තෝරන්න අංකය එවන්න 👇\n\n"
                            "1️⃣ සෞඛ්‍යය හා ශාරීරික අධ්‍යාපනය (Health)\n"
                            "2️⃣ විද්‍යාව (Science)\n"
                            "3️⃣ ඉතිහාසය (History)"
                        )
                        whatsapp_utils.send_whatsapp_message(phone, subject_msg)
                    
                    else:
                        whatsapp_utils.send_whatsapp_message(phone, "පුතේ, දැනට අපි O/L විතරයි කරන්නේ. O/L තෝරන්න.")
                        # (A/L ඕන නම් මෙතනට දාන්න පුළුවන්)

            # --- STEP 3: HANDLE SUBJECT SELECTION ---
            elif stage == "subject_select":
                if msg_type == "text":
                    text = msg['text']['body'].strip()
                    
                    if text == "1":
                        supabase.table("users").update({"subject": "Health Science", "setup_stage": "completed"}).eq("phone_number", phone).execute()
                        whatsapp_utils.send_whatsapp_message(phone, "නියමයි! දැන් සෞඛ්‍යය පාඩමේ ඕන දෙයක් අහන්න පුතේ. මම ලෑස්තියි! 📚")
                    elif text in ["2", "3"]:
                        whatsapp_utils.send_whatsapp_message(phone, "පුතේ ඒ විෂය තාම ලෑස්ති නෑ. අංක 1 (Health) තෝරන්නකෝ.")
                    else:
                        whatsapp_utils.send_whatsapp_message(phone, "පුතේ අදාල අංකය (1) එවන්න.")

            # --- STEP 4: Q&A MODE (STRICT) ---
            elif stage == "completed":
                # Text Message
                if msg_type == "text":
                    user_query = msg['text']['body']
                    # Loading Message (Optional)
                    # whatsapp_utils.send_whatsapp_message(phone, "පොඩ්ඩක් ඉන්න පුතේ...") 
                    response = get_ai_response(user_query, user['subject'], media_type="text")
                    whatsapp_utils.send_whatsapp_message(phone, response)

                # Image
                elif msg_type == "image":
                    image_id = msg['image']['id']
                    caption = msg['image'].get('caption', "")
                    media_url = whatsapp_utils.get_media_url(image_id)
                    if media_url:
                        media_data = whatsapp_utils.download_media_file(media_url)
                        response = get_ai_response(caption, user['subject'], media_data=media_data, media_type="image")
                        whatsapp_utils.send_whatsapp_message(phone, response)
                
                # Audio
                elif msg_type == "audio":
                    audio_id = msg['audio']['id']
                    media_url = whatsapp_utils.get_media_url(audio_id)
                    if media_url:
                        media_data = whatsapp_utils.download_media_file(media_url)
                        response = get_ai_response("", user['subject'], media_data=media_data, media_type="audio")
                        whatsapp_utils.send_whatsapp_message(phone, response)

    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()

    return {"status": "ok"}