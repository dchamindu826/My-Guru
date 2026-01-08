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
                'match_threshold': 0.3, 
                'match_count': 5
            }
        ).execute()

        context_text = "\n\n".join([doc['content'] for doc in response.data])
        
        # 3. Strict Prompt for "My Guru" & Simple Personality
        prompt = f"""
        ඔයාගේ නම 'My Guru'. ඔයා හරිම කරුණාවන්ත, ලොකු දැනුමක් තියෙන ගුරුවරයෙක්.
        
        පිළිපැදිය යුතු නීති:
        1. කිසිම වෙලාවක ඔයාගේ නම 'Guru Masters' කියලා කියන්න එපා. නම සැමවිටම 'My Guru' විය යුතුයි.
        2. ශිෂ්‍යයාට සැමවිටම "පුතේ" හෝ "දුවේ" කියා අමතන්න.
        3. ඉතාම සරල, පැහැදිලි සිංහල භාෂාවෙන් උත්තර දෙන්න. අමාරු වචන පාවිච්චි කරන්න එපා.
        4. ලබා දී ඇති [CONTEXT] එකේ ඇති තොරතුරු පමණක් පාවිච්චි කරන්න.
        5. [CONTEXT] එකේ නැති දෙයක් ඇහුවොත්, බොරු කියන්න එපා. "පුතේ, ඒ ගැන විස්තර මගේ සටහන් වල දැනට නෑ, අපි වෙන දෙයක් ගැන ඉගෙන ගමුද?" වගේ දෙයක් කියන්න.
        6. භාෂාව මිත්‍රශීලී විය යුතුයි. "මචං" වැනි වචන කිසිසේත් භාවිතා නොකරන්න.
        
        [CONTEXT]:
        {context_text}
        
        ශිෂ්‍යයාගේ ප්‍රශ්නය:
        "{user_message}"
        
        පිළිතුර (සරල සිංහලෙන්):
        """
        
        result = model.generate_content(prompt)
        return result.text

    except Exception as e:
        print(f"AI Error: {e}")
        return "පුතේ, පොඩි තාක්ෂණික ප්‍රශ්නයක් ආවා. අපි ආයෙත් උත්සාහ කරමුද?"

async def process_user_message(phone_number, user_message, message_type="text"):
    # Flow Logic
    if str(user_message).lower() in ["hi", "hello", "start", "menu", "ආයුබෝවන්"]:
        buttons = {"lang_si": "Sinhala 🇱🇰", "lang_en": "English 🇬🇧"}
        send_interactive_buttons(phone_number, "ආයුබෝවන් පුතේ! 'My Guru' වෙත ඔයාව සාදරයෙන් පිළිගන්නවා. 🙏\n\nඅපි ඉගෙන ගන්නේ මොන භාෂාවෙන්ද?", buttons)
        return

    if user_message in ["lang_si", "lang_en"]:
        exam_buttons = {"exam_ol": "G.C.E. O/L 📚", "exam_al": "G.C.E. A/L 🎓"}
        send_interactive_buttons(phone_number, "හොඳයි පුතේ! ඔයා සූදානම් වෙන්නේ මොන විභාගයටද?", exam_buttons)
        return

    if user_message in ["exam_ol", "exam_al"]:
        send_whatsapp_message(phone_number, "ඉතාම හොඳයි. දැන් ඔයාට ඉගෙන ගන්න ඕන විෂය (Subject) සහ පාඩමේ නම එවන්න පුතේ. මම ඔයාට ඒක සරලව කියලා දෙන්නම්.\n\nඋදාහරණ:\nScience - ආලෝකය\nMaths - වීජ ගණිතය")
        return

    if message_type == "text":
        ai_reply = get_rag_response(user_message)
        send_whatsapp_message(phone_number, ai_reply)