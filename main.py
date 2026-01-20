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

# --- SMART RAG FUNCTION (AUTO DETECT SUBJECT) ---
def get_ai_response(user_input, media_data=None, media_type=None):
    try:
        context_text = ""
        prompt_parts = []
        
        # 1. TEXT SEARCH (Global Search across ALL Subjects)
        if media_type == "text" and user_input:
            embedding = genai.embed_content(
                model="models/text-embedding-004",
                content=user_input,
                task_type="retrieval_query"
            )['embedding']

            # Match count එක 10-12 වගේ තියන්න. මොකද පොත් ගොඩක් තියෙන නිසා.
            # Threshold එක 0.28 වගේ තිබ්බාම කුණු එන එක අඩුයි.
            response = supabase.rpc("match_documents", {
                "query_embedding": embedding,
                "match_threshold": 0.28, 
                "match_count": 12 
            }).execute()
            
            if response.data:
                # Context එක හදනකොට ඒක කොයි පොතෙන්ද කියලත් බොට්ට කියනවා
                context_text = "\n\n".join([f"[SOURCE: {doc['metadata'].get('source', 'Unknown')}] {doc['content']}" for doc in response.data])
                prompt_parts.append(f"ALL TEXTBOOK DATA:\n{context_text}")
            
            prompt_parts.append(f"STUDENT QUESTION: {user_input}")

        # 2. IMAGE SEARCH
        elif media_type == "image":
            image = PIL.Image.open(io.BytesIO(media_data))
            vision_prompt = "Describe this image in detail (Sinhala/English). Identify diagrams, text, or figures."
            vision_response = model.generate_content([vision_prompt, image])
            img_desc = vision_response.text

            embedding = genai.embed_content(
                model="models/text-embedding-004",
                content=img_desc,
                task_type="retrieval_query"
            )['embedding']

            response = supabase.rpc("match_documents", {
                "query_embedding": embedding,
                "match_threshold": 0.28,
                "match_count": 10 
            }).execute()

            if response.data:
                context_text = "\n\n".join([f"[SOURCE: {doc['metadata'].get('source', 'Unknown')}] {doc['content']}" for doc in response.data])
                prompt_parts.append(f"ALL TEXTBOOK DATA:\n{context_text}")

            prompt_parts.append("INSTRUCTION: Explain this image using the provided TEXTBOOK DATA.")
            prompt_parts.append(image)
            if user_input: prompt_parts.append(f"Question: {user_input}")

        # 3. AUDIO SEARCH
        elif media_type == "audio":
            audio_prompt = "Listen to this audio. Write down EXACTLY what the student is asking in Sinhala."
            audio_resp = model.generate_content([audio_prompt, {"mime_type": "audio/ogg", "data": media_data}])
            audio_text = audio_resp.text
            
            embedding = genai.embed_content(
                model="models/text-embedding-004",
                content=audio_text,
                task_type="retrieval_query"
            )['embedding']

            response = supabase.rpc("match_documents", {
                "query_embedding": embedding,
                "match_threshold": 0.28,
                "match_count": 10
            }).execute()

            if response.data:
                context_text = "\n\n".join([f"[SOURCE: {doc['metadata'].get('source', 'Unknown')}] {doc['content']}" for doc in response.data])
                prompt_parts.append(f"ALL TEXTBOOK DATA:\n{context_text}")

            prompt_parts.append(f"STUDENT VOICE QUESTION (Transcribed): {audio_text}")

        # --- SYSTEM PROMPT (STRICT TEACHER MODE) ---
        system_instruction = """
        You are 'My Guru', a dedicated Sri Lankan school teacher.
        You have access to textbooks for multiple subjects (Sinhala, History, Science, Health, etc.).

        **CRITICAL INSTRUCTIONS FOR ACCURACY:**
        1. **Identify the Subject:** Look at the [SOURCE] tags in the context. If the student asks about 'Kavi' (Verses), look for 'Sinhala/Literature' data. If they ask about 'Force', look for 'Science' data.
        2. **Verses vs. Exercises:** - If the student asks for "Kavi" (Verses/Poems), provide the **actual verses**. DO NOT provide the exercises (abhyasa) or questions about the verses unless asked.
           - If the retrieved data only contains questions *about* the poem but not the poem itself, admit that you don't have the full verses text.
        3. **Subject Switching:** The student can switch subjects at any time. Adapt immediately based on their question.

        **TONE & LANGUAGE:**
        1. Address the student as "පුතේ" (Puthe). 
        2. **PROHIBITED:** Never use "Machan", "Yaluwa", "Ha ha", or overly casual slang. Be professional, kind, and direct.
        3. Language: Sinhala.

        **FORMATTING:**
        - Use Emojis (📚, ✅, 🏐) sparingly but effectively.
        - Use Bullet points (🔹).
        - Leave empty lines between paragraphs for readability.
        - Keep answers concise but complete.
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
            
            # --- SIMPLE USER CHECK (NO STAGES) ---
            # අපි දැන් යූසර්ව "Subject" එකකට කොටු කරන්නේ නෑ.
            # එයා අලුත් නම් විතරක් Register කරනවා.
            user_data = supabase.table("users").select("*").eq("phone_number", phone).execute()
            
            if not user_data.data:
                supabase.table("users").insert({"phone_number": phone, "setup_stage": "active"}).execute()
                # Welcome Message (එක පාරක් විතරයි යන්නේ)
                whatsapp_utils.send_whatsapp_message(phone, "ආයුබෝවන් පුතේ! මම My Guru. 🎓\n\nඔයාට සිංහල, විද්‍යාව, ඉතිහාසය, සෞඛ්‍යය වගේ ඕනම විෂයයකින් ප්‍රශ්න අහන්න පුළුවන්.\n\nමම ලෑස්තියි! මොකක්ද අද දැනගන්න ඕන? 📚")
                return {"status": "ok"}

            # --- DIRECT Q&A MODE (ALL TYPES) ---
            response = None
            
            if msg_type == "text":
                response = get_ai_response(msg['text']['body'])
            
            elif msg_type == "image":
                media_url = whatsapp_utils.get_media_url(msg['image']['id'])
                if media_url:
                    media_data = whatsapp_utils.download_media_file(media_url)
                    caption = msg['image'].get('caption', "")
                    response = get_ai_response(caption, media_data=media_data, media_type="image")
            
            elif msg_type == "audio":
                media_url = whatsapp_utils.get_media_url(msg['audio']['id'])
                if media_url:
                    media_data = whatsapp_utils.download_media_file(media_url)
                    response = get_ai_response("", media_data=media_data, media_type="audio")

            # Send Response (No Feedback Buttons)
            if response:
                whatsapp_utils.send_whatsapp_message(phone, response)

    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()

    return {"status": "ok"}