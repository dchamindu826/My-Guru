import os
import time
import fitz  # PyMuPDF
import PIL.Image
import io
from supabase import create_client
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, InternalServerError

# Configs Load
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)

# Gemini 2.0 Flash
model = genai.GenerativeModel('gemini-2.0-flash')

# --- 🔥 FIX: Embedding Logic with Heavy Retry ---
def get_embedding_with_retry(text, retries=5):
    delay = 10 # පටන් ගන්න තත්පර ගාණ
    for attempt in range(retries):
        try:
            # මොඩල් එක හොයාගැනීම (Fallback support)
            embed_model = "models/text-embedding-004"
            
            result = genai.embed_content(
                model=embed_model,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']

        except (ResourceExhausted, ServiceUnavailable, InternalServerError) as e:
            print(f"   ⚠️ Rate Limit Hit (Embedding). Waiting {delay}s...")
            time.sleep(delay)
            delay *= 2 # ඊළඟ පාර ඩබල් වෙලාවක් ඉන්නවා (10s -> 20s -> 40s...)
            
        except Exception as e:
            # වෙනත් Error එකක් නම් (උදා: 404 Model not found), පරණ මොඩල් එක ට්‍රයි කරනවා
            if "404" in str(e):
                try:
                    print("   ⚠️ Trying fallback model (embedding-001)...")
                    result = genai.embed_content(
                        model="models/embedding-001",
                        content=text,
                        task_type="retrieval_document"
                    )
                    return result['embedding']
                except:
                    pass
            print(f"   ❌ Embedding Error: {e}")
            time.sleep(5)
            
    return None

# --- 🔥 FIX: OCR Logic with Heavy Retry ---
def generate_content_with_retry(prompt, image, retries=5):
    delay = 20 # OCR එකට වැඩි වෙලාවක් ඉමු
    for attempt in range(retries):
        try:
            response = model.generate_content([prompt, image])
            return response.text.strip()
            
        except (ResourceExhausted, ServiceUnavailable, InternalServerError) as e:
            print(f"   ⚠️ Rate Limit Hit (OCR). Waiting {delay}s...")
            time.sleep(delay)
            delay *= 2 # වෙලාව ඩබල් කරනවා
            
        except Exception as e:
            print(f"   ❌ OCR Error: {e}")
            time.sleep(10)
            
    return None

def process_pdf(pdf_path, start_page, end_page, grade, subject_name, doc_type, medium):
    doc = fitz.open(pdf_path)
    print(f"📘 Processing: Grade {grade} - {subject_name} ({medium})")
    print(f"📂 Type: {doc_type}")
    print(f"📄 Total Pages: {len(doc)}")
    print(f"🎯 Selected Range: Page {start_page} to {end_page}\n")

    for page_num, page in enumerate(doc):
        current_page = page_num + 1

        if current_page < start_page: continue
        if current_page > end_page:
            print(f"🛑 Reached End Page ({end_page}). Stopping.")
            break

        print(f"🔄 Processing Page {current_page}...")
        
        # Image Capture
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_data = pix.tobytes("png")
        image = PIL.Image.open(io.BytesIO(img_data))

        prompt = f"""
        You are a highly accurate OCR engine.
        Task: Extract content from this {medium} medium {doc_type} page.
        RULES:
        1. OUTPUT RAW TEXT ONLY.
        2. Preserve numbering.
        3. Describe images in [brackets] (English).
        4. NO CHATTER.
        """
        
        # 🔥 භාවිතා කරන්නේ අපේ අලුත් Retry Function එක
        text_content = generate_content_with_retry(prompt, image)

        if not text_content or len(text_content) < 20:
            print(f"⚠️ Page {current_page} seems empty. Skipped.")
            continue

        # --- PREVIEW ---
        print("\n" + "="*60)
        print(f"📄 PAGE {current_page} CONTENT:")
        print("="*60)
        print(text_content[:200] + "...") 
        print("="*60 + "\n")

        # 🔥 භාවිතා කරන්නේ අපේ අලුත් Retry Function එක
        vector = get_embedding_with_retry(text_content)
        
        if vector:
            data = {
                "content": text_content,
                "embedding": vector,
                "metadata": {
                    "source": f"Gr{grade} {subject_name} ({medium}) {doc_type}", 
                    "page": current_page,
                    "subject": subject_name,
                    "grade": grade,
                    "type": doc_type,
                    "medium": medium
                }
            }
            supabase.table('documents').insert(data).execute()
            print(f"✅ Page {current_page} Uploaded Successfully!\n")
            
        
            print("⏳ Cooling down for 15 seconds to prevent bans...")
            time.sleep(15) 
            
        else:
            print(f"❌ Failed to process Page {current_page} after multiple retries.")
           
            time.sleep(10)
            continue

def main():
    # ==========================================
    # 👇 Upload Details
    # ==========================================
    
    pdf_file = "knowledge/scienceg11 english.pdf"

    GRADE = 11
    SUBJECT = "Science"
    DOC_TYPE = "Textbook" 
    MEDIUM = "English"
    
    # ⚠️ 
    START_PAGE = 9 
    END_PAGE = 444

    # ==========================================

    if os.path.exists(pdf_file):
        print(f"🚀 Starting Upload: {SUBJECT} ({MEDIUM}) - {DOC_TYPE}...")
        process_pdf(pdf_file, START_PAGE, END_PAGE, GRADE, SUBJECT, DOC_TYPE, MEDIUM)
        print("\n🎉 Upload Completed Successfully!")
    else:
        print(f"❌ PDF File not found at: {pdf_file}")

if __name__ == "__main__":
    main()