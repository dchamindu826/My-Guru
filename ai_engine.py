import os
import requests
import google.generativeai as genai
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Setup Configurations
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# Initialize Clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

def send_whatsapp_message(to_number, message):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "text": {"body": message}
    }
    requests.post(url, headers=headers, json=data)

def send_interactive_buttons(to_number, text, buttons):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    button_list = []
    for btn_id, btn_title in buttons.items():
        button_list.append({
            "type": "reply",
            "reply": {"id": btn_id, "title": btn_title}
        })
    data = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": text},
            "action": {"buttons": button_list}
        }
    }
    requests.post(url, headers=headers, json=data)

def get_rag_response(user_message):
    try:
        # 1. Embed Query
        embedding = genai.embed_content(
            model="models/text-embedding-004",
            content=user_message,
            task_type="retrieval_query"
        )['embedding']

        # 2. Search Supabase
        response = supabase.rpc(
            'match_documents',
            {
                'query_embedding': embedding,
                'match_threshold': 0.3, # පොඩි ගැලපීමක් තිබුණත් ගන්න
                'match_count': 5
            }
        ).execute()

        # Context හදාගැනීම
        context_text = "\n\n".join([doc['content'] for doc in response.data])
        
        # 3. Strict Prompt for Persona
        prompt = f"""
        You are 'Guru Masters', a kind and helpful Sri Lankan Tuition Teacher.
        
        YOUR RULES:
        1. ALWAYS address the student as "පුතේ" (Son/Child) or "දුවේ" (Daughter).
        2. NEVER use words like "මචං" (Machan), "බොක්ක", or slang. Be respectful but friendly.
        3. Only answer based on the [CONTEXT] provided below.
        4. If the [CONTEXT] contains garbage characters (like f.dú;ek), IGNORE THEM and say you cannot find the answer in the notes.
        5. Do NOT hallucinate. If the answer is not in the context, say: "පුතේ, මගේ Notes වල මේ ගැන විස්තරයක් නෑ. වෙන පාඩමක් ගැන අහමුද?"
        
        [CONTEXT from PDF]:
        {context_text}
        
        STUDENT QUESTION:
        "{user_message}"
        
        ANSWER (In Sinhala):
        """
        
        result = model.generate_content(prompt)
        return result.text

    except Exception as e:
        print(f"AI Error: {e}")
        return "පුතේ, පොඩි තාක්ෂණික දෝෂයක්. ආයේ උත්සාහ කරන්න."

async def process_user_message(phone_number, user_message, message_type="text"):
    print(f"📩 Message from {phone_number}: {user_message}")

    # Flow Logic
    if str(user_message).lower() in ["hi", "hello", "start", "menu", "ආයුබෝවන්"]:
        buttons = {"lang_si": "Sinhala 🇱🇰", "lang_en": "English 🇬🇧"}
        send_interactive_buttons(phone_number, "ආයුබෝවන් පුතේ! Guru Masters වෙත සාදරයෙන් පිළිගන්නවා. 🙏\n\nඅපි ඉගෙන ගන්නේ මොන භාෂාවෙන්ද?", buttons)
        return

    if user_message in ["lang_si", "lang_en"]:
        exam_buttons = {"exam_ol": "G.C.E. O/L 📚", "exam_al": "G.C.E. A/L 🎓"}
        send_interactive_buttons(phone_number, "හොඳයි පුතේ! ඔයා සූදානම් වෙන්නේ මොන විභාගයටද?", exam_buttons)
        return

    if user_message in ["exam_ol", "exam_al"]:
        send_whatsapp_message(phone_number, "ඉතාම හොඳයි. දැන් ඔයාට ඕන **Subject එකයි, පාඩමේ නමයි** Type කරලා එවන්න පුතේ.\n\nඋදාහරණ:\nScience - ආලෝකය\nHistory - කෝට්ටේ යුගය")
        return

    # Text Logic
    if message_type == "text":
        ai_reply = get_rag_response(user_message)
        send_whatsapp_message(phone_number, ai_reply)