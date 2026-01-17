import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

def get_headers():
    return {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

def send_whatsapp_message(to, body):
    """සාමාන්‍ය Text මැසේජ් යැවීමට"""
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    response = requests.post(url, headers=get_headers(), json=data)
    # Error Check
    if response.status_code != 200:
        print(f"❌ Error sending message: {response.text}")

def send_interactive_buttons(to, text, buttons):
    """Buttons 3ක් දක්වා යැවීමට"""
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    
    button_list = []
    for btn_id, btn_title in buttons.items():
        button_list.append({
            "type": "reply",
            "reply": {"id": btn_id, "title": btn_title}
        })

    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": text},
            "action": {"buttons": button_list}
        }
    }
    response = requests.post(url, headers=get_headers(), json=data)
    # Error Check
    if response.status_code != 200:
        print(f"❌ Error sending buttons: {response.text}")

def send_interactive_list(to, text, button_text, sections):
    """දිග විෂයන් ලිස්ට් එකක් යැවීමට"""
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": text},
            "action": {
                "button": button_text,
                "sections": sections
            }
        }
    }
    response = requests.post(url, headers=get_headers(), json=data)
    # Error Check
    if response.status_code != 200:
        print(f"❌ Error sending list: {response.text}")

def get_media_url(media_id):
    """WhatsApp Media ID එකෙන් URL එක ගැනීම"""
    url = f"https://graph.facebook.com/v22.0/{media_id}"
    response = requests.get(url, headers=get_headers())
    if response.status_code == 200:
        return response.json().get('url')
    else:
        print(f"❌ Error getting media URL: {response.text}")
        return None

def download_media_file(media_url):
    """URL එකෙන් Image/Audio ෆයිල් එක බාගැනීම"""
    response = requests.get(media_url, headers=get_headers())
    if response.status_code == 200:
        return response.content
    else:
        print(f"❌ Error downloading media: {response.text}")
        return None