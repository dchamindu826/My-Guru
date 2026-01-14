import os
import requests
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

def get_media_url(media_id):
    """WhatsApp Media ID එක දීලා URL එක ගන්නවා"""
    url = f"https://graph.facebook.com/v17.0/{media_id}"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("url")
    return None

def download_media(media_url, file_extension):
    """URL එකෙන් ෆයිල් එක ඩවුන්ලෝඩ් කරලා බයිට් විදියට දෙනවා"""
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    response = requests.get(media_url, headers=headers)
    
    if response.status_code == 200:
        filename = f"temp_media.{file_extension}"
        with open(filename, "wb") as f:
            f.write(response.content)
        return filename
    return None

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