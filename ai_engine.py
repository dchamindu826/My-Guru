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
    """සාමාන්‍ය Text Message යවන Function එක"""
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
    """Buttons යවන විශේෂ Function එක"""
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Buttons JSON එක හදමු
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

def get_ai_response(user_message):
    """AI එකෙන් උත්තර ගන්න Function එක (Subject එක Type කළාම)"""
    # මෙතන පස්සේ ඔයාගේ RAG Logic (Supabase search) එක එනවා.
    # දැනට අපි කෙලින්ම AI එකට කතා කරමු.
    
    prompt = f"""
    You are a friendly Sri Lankan Tuition Teacher named 'My Guru'.
    The student is asking about: "{user_message}".
    
    If the user asks for a specific subject (Science, Maths, etc.), explain a key concept briefly.
    Answer in a mix of Sinhala and English (Singlish allowed if helpful) or pure Sinhala.
    Keep it encouraging and helpful.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "සමාවෙන්න පුතේ, පොඩි තාක්ෂණික දෝෂයක්. ආයේ උත්සාහ කරන්න."

async def process_user_message(phone_number, user_message, message_type="text"):
    print(f"📩 Message from {phone_number} [{message_type}]: {user_message}")

    # --- FLOW LOGIC ---

    # 1. මුලින්ම Language එක අහමු (Start / Hi)
    if user_message.lower() in ["hi", "hello", "start", "menu", "ආයුබෝවන්"]:
        buttons = {
            "lang_si": "Sinhala සිංහල",
            "lang_en": "English",
            "lang_ta": "Tamil தமிழ்"
        }
        send_interactive_buttons(phone_number, "Welcome to My Guru! 🎓\nPlease select your language:", buttons)
        return

    # 2. Language එක තෝරගත්තම -> Exam එක අහමු
    if user_message in ["lang_si", "lang_en", "lang_ta"]:
        # මෙතනදි ඕන නම් Database එකේ language එක save කරගන්න පුළුවන් (user table update)
        
        exam_buttons = {
            "exam_ol": "G.C.E. O/L",
            "exam_al": "G.C.E. A/L"
        }
        send_interactive_buttons(phone_number, "හොඳයි! ඔයා සූදානම් වෙන්නේ මොන විභාගයටද? 👇", exam_buttons)
        return

    # 3. Exam එක තෝරගත්තම -> Subject එක Type කරන්න කියමු
    if user_message in ["exam_ol", "exam_al"]:
        msg = "එළකිරි! දැන් ඔයාට ඉගෙන ගන්න ඕන **Subject (විෂය)** එකේ නම Type කරන්න.\n\nඋදාහරණ:\n- Science\n- Maths\n- History\n- Commerce"
        send_whatsapp_message(phone_number, msg)
        return

    # 4. වෙන මොනවා හරි ලිව්වොත් -> ඒක Subject එකක් කියලා හිතලා AI එකෙන් උත්තර දෙමු
    ai_reply = get_ai_response(user_message)
    send_whatsapp_message(phone_number, ai_reply)

    # 5. Database Update (Log)
    try:
        # Check User
        response = supabase.table('users').select("*").eq('phone_number', phone_number).execute()
        if not response.data:
            user = supabase.table('users').insert({"phone_number": phone_number}).execute()
            user_id = user.data[0]['id']
        else:
            user_id = response.data[0]['id']

        # Log Chat
        supabase.table('chat_logs').insert({
            "user_id": user_id,
            "message_user": user_message,
            "message_bot": ai_reply if message_type == "text" else "Interactive Flow"
        }).execute()
    except Exception as e:
        print(f"DB Error: {e}")