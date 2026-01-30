import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

# Configs
ACCESS_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_ID")
VERSION = "v18.0"

def send_whatsapp_message(to, body):
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    
    print(f"🚀 ATTEMPTING TO SEND to {to}...") 
    response = requests.post(url, headers=headers, json=data)
    
    # 🔥 මෙන්න මේ ටිකෙන් තමයි ලෙඩේ අල්ලන්නේ
    if response.status_code == 200:
        print("✅ Message Sent Successfully!")
        return response.json()
    else:
        print(f"❌ WhatsApp API Error: {response.status_code}")
        print(f"❌ Error Details: {response.text}") # Meta එකෙන් එවන සම්පූර්ණ විස්තරේ
        return None

def send_interactive_buttons(to, body_text, buttons):
    url = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    
    button_list = []
    for btn_id, btn_title in buttons.items():
        button_list.append({
            "type": "reply",
            "reply": {
                "id": btn_id,
                "title": btn_title
            }
        })

    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body_text},
            "action": {"buttons": button_list}
        }
    }
    
    print(f"🚀 ATTEMPTING BUTTONS to {to}...")
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        print("✅ Buttons Sent Successfully!")
    else:
        print(f"❌ WhatsApp Button Error: {response.status_code}")
        print(f"❌ Error Details: {response.text}")

# --- Media Functions ---
def get_media_url(media_id):
    url = f"https://graph.facebook.com/{VERSION}/{media_id}"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("url")
    return None

def download_media_file(media_url):
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    response = requests.get(media_url, headers=headers)
    if response.status_code == 200:
        return response.content
    return None