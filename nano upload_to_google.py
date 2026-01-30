import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# මෙතනට ඔයාගේ PDF එකේ නම හරියටම දාන්න
PDF_FILE = "knowledge/health 10.pdf" 

print(f"🚀 Uploading {PDF_FILE} directly to Gemini...")

# 1. Upload the file
sample_file = genai.upload_file(path=PDF_FILE, display_name="Health Grade 10 Textbook")

print(f"✅ Upload Successful!")
print(f"📄 File Name: {sample_file.name}") # <--- මේක වැදගත්
print(f"🔗 URI: {sample_file.uri}")
print("\n⚠️ මේ 'File Name' එක Copy කරගන්න. අපිට main.py එකට ඕන වෙනවා.")