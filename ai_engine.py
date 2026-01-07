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
    try:
        requests.post(url, headers=headers, json=data)
    except Exception as e:
        print(f"Error sending message: {e}")

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
    try:
        requests.post(url, headers=headers, json=data)
    except Exception as e:
        print(f"Error sending buttons: {e}")

def get_rag_response(user_message):
    """Database එකෙන් Context එක අරගෙන, ලස්සන සිංහලෙන් උත්තර දෙන තැන"""
    try:
        # 1. User ගේ ප්‍රශ්නයට අදාළ Embedding එක ගන්න
        embedding = genai.embed_content(
            model="models/text-embedding-004",
            content=user_message,
            task_type="retrieval_query"
        )['embedding']

        # 2. Supabase එකෙන් ඊට සමාන කොටස් හොයනවා (Threshold එක 0.4 ට දැම්මා, නැත්නම් සමහර විට අහු වෙන්නේ නෑ)
        response = supabase.rpc(
            'match_documents',
            {
                'query_embedding': embedding,
                'match_threshold': 0.4, 
                'match_count': 4
            }
        ).execute()

        # Context එක ගොඩනගනවා
        context_text = "\n\n".join([doc['content'] for doc in response.data])
        
        # Context එකක් හම්බුනේ නැත්නම් (පොතේ නෑ)
        if not context_text:
            return "පුතේ, ඔයා අහපු දේ මම දාගෙන ඉන්න Note වල නෑනේ. 🤔\n\nවෙන විදිහකට අහල බලමුද? නැත්නම් Page Number එක ෂුවර් ද?"

        # 3. AI එකට උපදෙස් (Persona) - මෙතන තමයි භාෂාව හදන්නේ
        prompt = f"""
        You are 'Guru Masters', a super friendly and cool Sri Lankan O/L Tuition Teacher.
        
        YOUR PERSONALITY:
        - Talk like a real Sri Lankan person (Spoken Sinhala + English Mix).
        - Use words like: "පුතේ" (Son/Kid), "මචං" (Machan - only if casual), "පොඩ්ඩක් බලමු", "වැඩේ ගොඩ", "Example එකක් ගත්තොත්".
        - NEVER speak in formal/written Sinhala (Do not use 'ඔබ', 'සඳහා', 'වෙත').
        - Be encouraging and fun.
        
        INSTRUCTIONS:
        - Answer the student's question ONLY using the provided [CONTEXT] below.
        - If the answer is not in the context, say you don't know based on the notes.
        - Explain things simply.
        
        [CONTEXT FROM TEXTBOOK]:
        {context_text}
        
        STUDENT QUESTION:
        "{user_message}"
        
        ANSWER (In Spoken Sinhala/Singlish):
        """
        
        result = model.generate_content(prompt)
        return result.text

    except Exception as e:
        print(f"AI Error: {e}")
        return "පොඩි ටෙක්නිකල් අවුලක් පුතේ. විනාඩියකින් ආයේ ට්‍රයි එකක් දෙමු."

async def process_user_message(phone_number, user_message, message_type="text"):
    print(f"📩 Message from {phone_number} [{message_type}]: {user_message}")

    # --- FLOW LOGIC ---

    # 1. Start / Menu
    if str(user_message).lower() in ["hi", "hello", "start", "menu", "ආයුබෝවන්"]:
        buttons = {
            "lang_si": "Sinhala 🇱🇰",
            "lang_en": "English 🇬🇧"
        }
        send_interactive_buttons(phone_number, "ආයුබෝවන් පුතේ! Welcome to My Guru. 🎓\n\nඅපි මොන භාෂාවෙන්ද ඉගෙන ගන්නේ?", buttons)
        return

    # 2. Language Selection
    if user_message in ["lang_si", "lang_en"]:
        exam_buttons = {
            "exam_ol": "G.C.E. O/L 📚",
            "exam_al": "G.C.E. A/L 🎓"
        }
        send_interactive_buttons(phone_number, "එළකිරි! දැන් කියන්න ඔයාගේ විභාගය මොකක්ද?", exam_buttons)
        return

    # 3. Exam Selection -> Ask for Subject
    if user_message in ["exam_ol", "exam_al"]:
        msg = "නියමයි! දැන් ඔයාට ඕන **Subject එකයි, පාඩමේ නමයි** Type කරලා එවන්න.\n\nඋදාහරණ:\n👉 Science - Light (ආලෝකය)\n👉 History - Kotte Kingdom"
        send_whatsapp_message(phone_number, msg)
        return

    # 4. Handle Subject/Question using RAG
    # RAG function එක Call කරනවා (Button IDs නෙවෙයි නම් විතරයි)
    if message_type == "text":
        ai_reply = get_rag_response(user_message)
        send_whatsapp_message(phone_number, ai_reply)

    # 5. Log Chat
    try:
        response = supabase.table('users').select("*").eq('phone_number', phone_number).execute()
        if not response.data:
            user = supabase.table('users').insert({"phone_number": phone_number}).execute()
            user_id = user.data[0]['id']
        else:
            user_id = response.data[0]['id']

        supabase.table('chat_logs').insert({
            "user_id": user_id,
            "message_user": user_message,
            "message_bot": ai_reply if message_type == "text" else "Interactive Flow"
        }).execute()
    except Exception as e:
        print(f"DB Log Error: {e}")