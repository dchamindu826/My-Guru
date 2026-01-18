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

# --- RAG FUNCTION (FORMATTING UPDATED 💅) ---
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
                "match_count": 8
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
                "match_count": 5
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
                "match_count": 8
            }).execute()

            if response.data:
                context_text = "\n\n".join([doc['content'] for doc in response.data])
                prompt_parts.append(f"BOOK CONTEXT:\n{context_text}")

            prompt_parts.append(f"STUDENT VOICE QUESTION (Transcribed): {audio_text}")
            prompt_parts.append("Answer this question using the BOOK CONTEXT.")

        # --- SYSTEM PROMPT (LASSANA FORMATTING ✨) ---
        system_instruction = f"""
        You are 'My Guru', a friendly and engaging Sri Lankan teacher for {subject}.
        
        INSTRUCTIONS:
        1. **Content:** Answer primarily based on the 'BOOK CONTEXT'.
        2. **Language:** Sinhala.
        
        FORMATTING RULES (Make it readable & fun!):
        1. **Use Emojis:** Use relevant emojis (e.g., 📚, ✅, 📌, 🏐, 💡) to make the text lively.
        2. **Bullet Points:** Use symbols like 🔹, 🔸, or ▫️ for lists. Avoid plain dashes.
        3. **Spacing:** Keep paragraphs **short**. MUST leave an empty line between paragraphs.
        4. **Conciseness:** Give a **simple and direct** answer first. Do not write long essays.
        5. **Tone:** Warm, encouraging, and helpful (e.g., "හරි පුතේ...", "වැදගත් කරුණක් තමයි...").

        EXAMPLE OUTPUT:
        "හරි පුතේ, ඔයා අහපු දේ ගැන පොතේ තියෙන්නේ මෙහෙමයි. 👇

        🏐 *වොලිබෝල් ක්‍රීඩාවේ ප්‍රහාරය*

        මේකෙදි වැදගත් කරුණු කිහිපයක් තියෙනවා:

        🔹 පන්දුවට පහර දෙන්න ඕන දැලට උඩින්.
        🔹 වේගයෙන් ප්‍රතිවාදී පිලට යවන්න ඕන.

        තව විස්තර දැනගන්න ඕන නම් අහන්න! 😊"
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
                whatsapp_utils.send_interactive_buttons(phone, "කොහොමද පුතේ? 😊\nවිභාගය තෝරන්න:", {"ol": "O/L", "al": "A/L"})
                return {"status": "ok"}

            user = user_data.data[0]
            stage = user['setup_stage']

            if stage == "exam_select":
                if msg_type == "interactive":
                    if msg['interactive']['button_reply']['id'] == "ol":
                        supabase.table("users").update({"exam_level": "O/L", "setup_stage": "subject_select"}).eq("phone_number", phone).execute()
                        whatsapp_utils.send_whatsapp_message(phone, "O/L විෂයක් තෝරන්න අංකය එවන්න 👇\n\n1️⃣ සෞඛ්‍යය (Health)\n2️⃣ විද්‍යාව (Science)")
            
            elif stage == "subject_select":
                if msg_type == "text" and msg['text']['body'].strip() == "1":
                    supabase.table("users").update({"subject": "Health Science", "setup_stage": "completed"}).eq("phone_number", phone).execute()
                    whatsapp_utils.send_whatsapp_message(phone, "හරි! දැන් සෞඛ්‍යය ගැන ඕන දෙයක් අහන්න. 📚")

            elif stage == "completed":
                if msg_type == "text":
                    response = get_ai_response(msg['text']['body'], user['subject'], media_type="text")
                    whatsapp_utils.send_whatsapp_message(phone, response)
                elif msg_type == "image":
                    media_url = whatsapp_utils.get_media_url(msg['image']['id'])
                    if media_url:
                        media_data = whatsapp_utils.download_media_file(media_url)
                        response = get_ai_response(msg['image'].get('caption', ""), user['subject'], media_data=media_data, media_type="image")
                        whatsapp_utils.send_whatsapp_message(phone, response)
                elif msg_type == "audio":
                    media_url = whatsapp_utils.get_media_url(msg['audio']['id'])
                    if media_url:
                        media_data = whatsapp_utils.download_media_file(media_url)
                        response = get_ai_response("", user['subject'], media_data=media_data, media_type="audio")
                        whatsapp_utils.send_whatsapp_message(phone, response)

    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()

    return {"status": "ok"}