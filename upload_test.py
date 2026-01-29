import os
import time
import fitz  # PyMuPDF
import PIL.Image
import io
from supabase import create_client
from dotenv import load_dotenv
import google.generativeai as genai

# Configs Load
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)

# Gemini 2.0 Flash
model = genai.GenerativeModel('gemini-2.0-flash')

# ⚠️ Database එක Clear කරන්න ඕන නම් SQL Editor එකෙන් TRUNCATE TABLE documents; රන් කරන්න.
# Python එකෙන් Clear කරන Function එක අපි අයින් කළා වැරදිලා මැකෙන එක නවත්තන්න.

def get_embedding_with_retry(text, retries=3):
    for attempt in range(retries):
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"   ⚠️ Embedding Error (Attempt {attempt+1}): {e}")
            time.sleep(5)
    return None

# --- UPDATE: grade සහ subject_name දෙකම ගන්නවා ---
def process_pdf(pdf_path, start_page, end_page, grade, subject_name):
    doc = fitz.open(pdf_path)
    print(f"📘 Processing: Grade {grade} - {subject_name}")
    print(f"📂 File: {pdf_path}")
    print(f"📄 Total Pages: {len(doc)}")
    print(f"🎯 Selected Range: Page {start_page} to {end_page}\n")

    for page_num, page in enumerate(doc):
        current_page = page_num + 1

        # --- PAGE RANGE LOGIC ---
        if current_page < start_page:
            continue
        
        if current_page > end_page:
            print(f"🛑 Reached End Page ({end_page}). Stopping.")
            break
        # ------------------------

        retries = 3
        success = False
        
        while retries > 0 and not success:
            try:
                print(f"🔄 Processing Page {current_page}...")
                
                # Image Capture
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_data = pix.tobytes("png")
                image = PIL.Image.open(io.BytesIO(img_data))

                # --- PROMPT (CLEAN RAW TEXT) ---
                prompt = """
                You are a highly accurate OCR engine.
                Task: Extract all text from this page exactly as it appears.

                RULES:
                1. **OUTPUT RAW TEXT ONLY:** Do NOT use markdown (no **, no ##, no - lists). Just plain paragraphs.
                2. **CONTINUITY:** Maintain the flow. Do not break sentences unnaturally.
                3. **FULL CONTENT:** Capture everything from top to bottom.
                4. **IMAGES:** If there is a diagram, describe it in Sinhala inside brackets: [රූපය: විස්තරය].
                5. **NO CHATTER:** Do not say "Here is the text". Just give the text.
                """
                
                response = model.generate_content([prompt, image])
                text_content = response.text.strip()

                if not text_content or len(text_content) < 20:
                    print(f"⚠️ Page {current_page} seems empty. Skipped.")
                    break

                # --- FULL PREVIEW ---
                print("\n" + "="*60)
                print(f"📄 PAGE {current_page} CONTENT:")
                print("="*60)
                print(text_content[:200] + "...") 
                print("="*60 + "\n")

                # Database Upload
                vector = get_embedding_with_retry(text_content)
                
                if vector:
                    data = {
                        "content": text_content,
                        "embedding": vector,
                        "metadata": {
                            # 1. Source එකට Grade එකත් එකතු කළා
                            "source": f"Grade {grade} {subject_name}", 
                            "page": current_page,
                            "subject": subject_name, # Filter කරන්න
                            "grade": grade           # Filter කරන්න (අලුත් field එක)
                        }
                    }
                    supabase.table('documents').insert(data).execute()
                    print(f"✅ Page {current_page} Uploaded Successfully! (Gr:{grade} | Sub:{subject_name})\n")
                    success = True
                else:
                    print(f"❌ Embedding Failed for Page {current_page}")
                    break

            except Exception as e:
                print(f"❌ Error on Page {current_page}: {e}")
                print("⏳ Retrying in 5 seconds...")
                time.sleep(5)
                retries -= 1
        
        time.sleep(2)

def main():
    # ==========================================
    # 👇 Before Update Data
    # ==========================================
    
    # 1. PDF එකේ නම
    pdf_file = "knowledge/health 10.pdf"

    # 2. ශ්‍රේණිය (Grade) - 
    GRADE = 10 

    # 3. විෂය (Subject) - (උදා: "Science", "History", "Sinhala")
    SUBJECT = "Health"
    
    # 4. පිටු ගාණ (පටන් ගන්න සහ ඉවර වෙන පිටුව)
    START_PAGE = 9
    END_PAGE = 238

    # ==========================================

    if os.path.exists(pdf_file):
        print(f"🚀 Starting Upload for Grade {GRADE} - {SUBJECT}...")
        process_pdf(pdf_file, START_PAGE, END_PAGE, GRADE, SUBJECT)
        print("\n🎉 Book Uploaded Successfully!")
    else:
        print(f"❌ PDF File not found at: {pdf_file}")

if __name__ == "__main__":
    main()