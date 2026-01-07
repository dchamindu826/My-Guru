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

# අපි Gemini Flash එක පාවිච්චි කරමු PDF එක "බලලා" කියවන්න
vision_model = genai.GenerativeModel('gemini-1.5-flash')
embed_model = "models/text-embedding-004"

def extract_text_using_vision(page_image_bytes):
    """පිටුවේ ෆොටෝ එකක් ගහලා ඒකේ තියෙන සිංහල අකුරු කියවගන්නවා"""
    try:
        prompt = """
        Extract all the text from this image perfectly into Sinhala Unicode.
        Do not describe the image, just output the text content.
        If there are headers, keep them.
        """
        response = vision_model.generate_content(
            contents=[
                {"mime_type": "image/png", "data": page_image_bytes},
                prompt
            ]
        )
        return response.text
    except Exception as e:
        print(f"⚠️ Vision Error: {e}")
        return ""

def get_embedding(text):
    result = genai.embed_content(
        model=embed_model,
        content=text,
        task_type="retrieval_document"
    )
    return result['embedding']

def process_pdf(file_path):
    print(f"📖 Processing (Vision Mode): {file_path}")
    
    doc = fitz.open(file_path)
    full_text = ""

    # හැම පිටුවක්ම Image එකක් කරලා කියවමු
    for page_num, page in enumerate(doc):
        print(f"   👁️ Reading Page {page_num + 1} with AI Vision...")
        
        # 1. Convert page to Image
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # High Res
        img_bytes = pix.tobytes("png")
        
        # 2. Send to Gemini to Read (OCR)
        page_text = extract_text_using_vision(img_bytes)
        
        if page_text:
            full_text += f"\n[Page {page_num + 1}]\n" + page_text
        
        # Rate limit එක වදින්නේ නැති වෙන්න පොඩි විවේකයක්
        time.sleep(2)

    print("✅ Text Extracted using AI. Now Chunking...")

    # Chunking & Uploading
    chunk_size = 1000
    overlap = 200
    start = 0
    
    count = 0
    while start < len(full_text):
        end = start + chunk_size
        chunk = full_text[start:end]
        
        try:
            vector = get_embedding(chunk)
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
    files = [f for f in os.listdir(folder_name) if f.endswith('.pdf')]
    
    if not files:
        print("⚠️ No PDFs found.")
        return

    print(f"🚀 Found {len(files)} PDFs. Starting Vision Ingestion...")
    for file in files:
        process_pdf(os.path.join(folder_name, file))

    print("\n🎉 All Done! Now the bot can read Sinhala perfectly.")

if __name__ == "__main__":
    main()