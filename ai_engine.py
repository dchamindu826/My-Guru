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

# Clients Initialize
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)
# ඔයාගේ Account එකට වැඩ කරන වේගවත්ම Model එක
model = genai.GenerativeModel('gemini-flash-latest') 

def send_whatsapp_message(to_number, message):
    """WhatsApp එකට Reply එක යවන function එක"""
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
        response = requests.post(url, headers=headers, json=data)
        return response.status_code
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

def get_simple_response(user_message):
    """කෙලින්ම AI එකෙන් උත්තරේ ගන්න (Embedding නැතුව - වේගවත්)"""
    prompt = f"""
    You are a helpful Sri Lankan O/L Tuition Teacher named 'Guru Masters'.
    User Message: "{user_message}"
    
    Answer in friendly Sinhala. Keep it short and encouraging.
    If they say 'Hi' or 'Hello', welcome them warmly.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return "සමාවෙන්න පුතේ, පොඩි තාක්ෂණික දෝෂයක්. ආයේ උත්සාහ කරන්න."

async def process_user_message(phone_number, user_message):
    print(f"📩 Message from {phone_number}: {user_message}")

    # 1. AI උත්තරේ ගන්න (Database බලන්න කලින් මේක කරමු - වේගවත් වෙන්න)
    # ළමයා බලන් ඉන්න නිසා මුලින්ම උත්තරේ යවලා ඉමු.
    ai_reply = get_simple_response(user_message)
    
    # 2. Reply එක යවන්න
    send_whatsapp_message(phone_number, ai_reply)
    print("✅ Reply Sent! (Now updating DB in background)")

    # 3. Database වැඩ ටික (පස්සේ හිමින් වුනාට කමක් නෑ)
    try:
        # User ඉන්නවද බලනවා
        response = supabase.table('users').select("*").eq('phone_number', phone_number).execute()
        
        if not response.data:
            # New User
            user = supabase.table('users').insert({"phone_number": phone_number}).execute()
            user_id = user.data[0]['id']
        else:
            # Existing User
            user_id = response.data[0]['id']

        # Chat Log එක දානවා
        supabase.table('chat_logs').insert({
            "user_id": user_id,
            "message_user": user_message,
            "message_bot": ai_reply
        }).execute()
        
    except Exception as e:
        print(f"⚠️ Database Error (Background): {e}")