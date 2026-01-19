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
model = genai.GenerativeModel('gemini-2.0-flash')

# --- RAG FUNCTION (UPDATED PROMPT FOR TONE) ---
def get_ai_response(user_input, subject, media_data=None, media_type=None):
    try:
        context_text = ""
        prompt_parts = []
        
        # ---------------------------------------------------------
        # SCENARIO 1: TEXT MESSAGE
        # ---------------------------------------------------------
        if media_type == "text" and user_input:
            embedding = genai.embed_content(
                model="models/text-embedding-004",
                content=user_input,
                task_type="retrieval_query"
            )['embedding']

            response = supabase.rpc("match_documents", {
                "query_embedding": embedding,
                "match_threshold": 0.25, 
                "match_count": 10
            }).execute()
            
            if response.data:
                context_text = "\n\n".join([doc['content'] for doc in response.data])
                prompt_parts.append(f"BOOK CONTEXT:\n{context_text}")
            
            prompt_parts.append(f"STUDENT QUESTION: {user_input}")

        # ---------------------------------------------------------
        # SCENARIO 2: IMAGE MESSAGE
        # ---------------------------------------------------------
        elif media_type == "image":
            image = PIL.Image.open(io.BytesIO(media_data))
            
            vision_prompt = "Describe this image in detail (Sinhala/English). Focus on diagrams/text."
            vision_response = model.generate_content([vision_prompt, image])
            img_desc = vision_response.text

            embedding = genai.embed_content(
                model="models/text-embedding-004",
                content=img_desc,
                task_type="retrieval_query"
            )['embedding']

            response = supabase.rpc("match_documents", {
                "query_embedding": embedding,
                "match_threshold": 0.25,
                "match_count": 8
            }).execute()

            if response.data:
                context_text = "\n\n".join([doc['content'] for doc in response.data])
                prompt_parts.append(f"BOOK CONTEXT:\n{context_text}")

            prompt_parts.append("INSTRUCTION: Explain this image using the BOOK CONTEXT.")
            prompt_parts.append(image)
            if user_input: prompt_parts.append(f"Question: {user_input}")

        # ---------------------------------------------------------
        # SCENARIO 3: AUDIO MESSAGE
        # ---------------------------------------------------------
        elif media_type == "audio":
            audio_prompt = "Listen to this audio and write down EXACTLY what the student is asking in Sinhala/English."
            audio_resp = model.generate_content([audio_prompt, {"mime_type": "audio/ogg", "data": media_data}])
            audio_text = audio_resp.text
            
            embedding = genai.embed_content(
                model="models/text-embedding-004",
                content=audio_text,
                task_type="retrieval_query"
            )['embedding']

            response = supabase.rpc("match_documents", {
                "query_embedding": embedding,
                "match_threshold": 0.25,
                "match_count": 10
            }).execute()

            if response.data:
                context_text = "\n\n".join([doc['content'] for doc in response.data])
                prompt_parts.append(f"BOOK CONTEXT:\n{context_text}")

            prompt_parts.append(f"STUDENT VOICE QUESTION (Transcribed): {audio_text}")
            prompt_parts.append("Answer this question using the BOOK CONTEXT.")

        # --- SYSTEM PROMPT (TONE UPDATE: Puthe NOT Machan) ---
        system_instruction = f"""
        You are 'My Guru', a friendly and wise Sri Lankan teacher for {subject}.
        
        INSTRUCTIONS:
        1. **Content:** Answer based on 'BOOK CONTEXT'.
        2. **Completeness:** If there's a list, give ALL items.
        3. **Language:** Sinhala.
        
        TONE RULES (VERY IMPORTANT):
        1. **Address the student as 'Puthe' (පුතේ).** 2. **NEVER use words like 'Machan', 'Yaluwa', 'Macho'.** You are a Teacher.
        3. Be kind, encouraging, and respectful.

        FORMATTING:
        - Use Emojis (📚, ✅, 🏐).
        - Use Bullet Points (🔹).
        - Leave empty lines between paragraphs.
        """
        
        full_prompt = [system_instruction] + prompt_parts
        
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
            
            user_data = supabase.table("users").select("*").eq("phone_number", phone).execute()
            
            if not user_data.data:
                supabase.table("users").insert({"phone_number": phone, "setup_stage": "exam_select"}).execute()
                whatsapp_utils.send_interactive_buttons(phone, "ආයුබෝවන් පුතේ! 😊\nවිභාගය තෝරන්න:", {"ol": "O/L", "al": "A/L"})
                return {"status": "ok"}

            user = user_data.data[0]
            stage = user['setup_stage']

            # --- INTERACTIVE BUTTON HANDLING (MENU & FEEDBACK) ---
            if msg_type == "interactive":
                btn_id = msg['interactive']['button_reply']['id']

                # 1. Exam Selection
                if stage == "exam_select":
                    if btn_id == "ol":
                        supabase.table("users").update({"exam_level": "O/L", "setup_stage": "subject_select"}).eq("phone_number", phone).execute()
                        whatsapp_utils.send_whatsapp_message(phone, "O/L විෂයක් තෝරන්න අංකය එවන්න 👇\n\n1️⃣ සෞඛ්‍යය (Health)\n2️⃣ විද්‍යාව (Science)")
                
                # 2. Feedback Handling (NEW)
                elif stage == "completed":
                    if btn_id == "fb_yes":
                        whatsapp_utils.send_whatsapp_message(phone, "ගොඩක් සතුටුයි පුතේ! දිගටම ඉගෙන ගමු. 📚✨")
                    elif btn_id == "fb_no":
                        whatsapp_utils.send_whatsapp_message(phone, "අයියෝ! සමාවෙන්න පුතේ. 😔\nප්‍රශ්නය තව ටිකක් පැහැදිලිව අහන්නකෝ, මම උත්සාහ කරන්නම්.")
            
            # --- SUBJECT SELECTION ---
            elif stage == "subject_select":
                if msg_type == "text" and msg['text']['body'].strip() == "1":
                    supabase.table("users").update({"subject": "Health Science", "setup_stage": "completed"}).eq("phone_number", phone).execute()
                    whatsapp_utils.send_whatsapp_message(phone, "හරි පුතේ! දැන් සෞඛ්‍යය පාඩම ගැන ඕන දෙයක් අහන්න. 📚\n(වෙන විෂයකට යන්න ඕන නම් 'Menu' කියලා එවන්න)")

            # --- Q&A MODE ---
            elif stage == "completed":
                
                # 1. MENU / RESET COMMAND (NEW FEATURE)
                if msg_type == "text":
                    text_body = msg['text']['body'].strip().lower()
                    if text_body in ["menu", "list", "change", "මුලට", "විෂයන්", "subject","wenath"]:
                        supabase.table("users").update({"setup_stage": "exam_select"}).eq("phone_number", phone).execute()
                        whatsapp_utils.send_interactive_buttons(phone, "මුලට පැමිණියා. විභාගය තෝරන්න පුතේ: 👇", {"ol": "O/L", "al": "A/L"})
                        return {"status": "ok"}

                # 2. AI PROCESSING
                response = None
                if msg_type == "text":
                    response = get_ai_response(msg['text']['body'], user['subject'], media_type="text")
                elif msg_type == "image":
                    media_url = whatsapp_utils.get_media_url(msg['image']['id'])
                    if media_url:
                        media_data = whatsapp_utils.download_media_file(media_url)
                        caption = msg['image'].get('caption', "")
                        response = get_ai_response(caption, user['subject'], media_data=media_data, media_type="image")
                elif msg_type == "audio":
                    media_url = whatsapp_utils.get_media_url(msg['audio']['id'])
                    if media_url:
                        media_data = whatsapp_utils.download_media_file(media_url)
                        response = get_ai_response("", user['subject'], media_data=media_data, media_type="audio")

                # 3. SEND RESPONSE + FEEDBACK REQUEST
                if response:
                    whatsapp_utils.send_whatsapp_message(phone, response)
                    # Ask for Feedback (New)
                    whatsapp_utils.send_interactive_buttons(phone, "පුතේ, මේ පිළිතුර පැහැදිලිද? 👇", {"fb_yes": "ඔව් (Yes)", "fb_no": "නෑ (No)"})

    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()

    return {"status": "ok"}