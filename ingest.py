import os
import fitz  # PyMuPDF
import google.generativeai as genai
from supabase import create_client
from dotenv import load_dotenv
import time

load_dotenv()

# Configs
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)

# ✅ FIX 1: Stable Model එකට මාරු වුනා
vision_model = genai.GenerativeModel('gemini-flash-latest')

def extract_text_using_vision(page_image_bytes):
    """පිටුවේ ෆොටෝ එකක් ගහලා ඒකේ තියෙන සිංහල අකුරු කියවගන්නවා"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            prompt = """
            You are an expert OCR assistant. 
            Extract all the Sinhala and English text from this image accurately.
            Do not explain the image, just provide the text content.
            """
            response = vision_model.generate_content(
                contents=[
                    {"mime_type": "image/png", "data": page_image_bytes},
                    prompt
                ]
            )
            return response.text
        except Exception as e:
            if "429" in str(e):
                print(f"   ⏳ Too fast! Waiting 20 seconds... (Attempt {attempt+1}/{max_retries})")
                time.sleep(20) # Error 429 ආවොත් තත්පර 20ක් ඉන්නවා
            else:
                print(f"   ⚠️ Vision Error: {e}")
                return ""
    return ""

def get_embedding(text):
    try:
        # Embedding වලටත් පොඩි විවේකයක් දෙමු
        time.sleep(2)
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        print(f"⚠️ Embedding Error: {e}")
        return None

def process_pdf(file_path):
    print(f"📖 Processing (Slow Mode): {file_path}")
    
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        print(f"❌ Could not open PDF: {e}")
        return

    full_text = ""

    # හැම පිටුවක්ම Image එකක් කරලා කියවමු
    for page_num, page in enumerate(doc):
        print(f"   👁️ Reading Page {page_num + 1} with AI Vision...")
        
        try:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) 
            img_bytes = pix.tobytes("png")
            
            page_text = extract_text_using_vision(img_bytes)
            
            if page_text:
                full_text += f"\n[Page {page_num + 1}]\n" + page_text
            
            # ✅ FIX 2: පිටුවක් කියවලා තත්පර 10ක් නිදාගන්නවා (Rate Limit නොවදින්න)
            print("      💤 Resting for 10 seconds...")
            time.sleep(10)
            
        except Exception as e:
            print(f"   ⚠️ Page Skip: {e}")

    if not full_text:
        print("⚠️ No text extracted from this PDF.")
        return

    print("✅ Text Extracted. Now Chunking & Uploading...")

    chunk_size = 1000
    overlap = 200
    start = 0
    count = 0
    
    while start < len(full_text):
        end = start + chunk_size
        chunk = full_text[start:end]
        
        try:
            vector = get_embedding(chunk)
            if vector:
                data = {
                    "content": chunk,
                    "embedding": vector,
                    "metadata": {"source": os.path.basename(file_path)}
                }
                supabase.table('documents').insert(data).execute()
                count += 1
                print(f"   📤 Uploaded Chunk {count}")
        except Exception as e:
            print(f"   ❌ Upload Fail: {e}")
            
        start += (chunk_size - overlap)

def main():
    folder_name = "knowledge"
    
    if not os.path.exists(folder_name):
        print(f"❌ '{folder_name}' folder not found!")
        return

    files = [f for f in os.listdir(folder_name) if f.endswith('.pdf')]
    
    if not files:
        print("⚠️ No PDFs found.")
        return

    # Science පොත විතරක් තියන්න කියලා මතක් කරනවා
    print(f"🚀 Found {len(files)} PDFs. Starting Vision Ingestion...")
    print("⚠️ NOTE: If you have many books, this will take time due to Rate Limits.")
    
    for file in files:
        process_pdf(os.path.join(folder_name, file))

    print("\n🎉 All Done! Now the bot can read Sinhala perfectly.")

if __name__ == "__main__":
    main()