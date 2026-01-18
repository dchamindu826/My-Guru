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

def clear_database():
    print("🧹 Cleaning old database records...")
    try:
        supabase.table('documents').delete().neq('id', 0).execute()
        print("✅ Database Cleared!")
    except Exception as e:
        print(f"⚠️ Error clearing DB: {e}")

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

def process_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    print(f"📘 Processing PDF: {pdf_path} ({len(doc)} Pages)\n")

    for page_num, page in enumerate(doc):
        retries = 3
        success = False
        
        while retries > 0 and not success:
            try:
                print(f"🔄 Processing Page {page_num + 1}...")
                
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
                    print(f"⚠️ Page {page_num + 1} seems empty. Skipped.")
                    break

                # --- FULL PREVIEW (මුළු පිටුවම පෙන්වන්න) ---
                print("\n" + "="*60)
                print(f"📄 PAGE {page_num + 1} CONTENT:")
                print("="*60)
                print(text_content)  # දැන් මුළු පිටුවම පේනවා
                print("="*60 + "\n")

                # Database Upload
                vector = get_embedding_with_retry(text_content)
                
                if vector:
                    data = {
                        "content": text_content,
                        "embedding": vector,
                        "metadata": {"source": "Grade 10 Health", "page": page_num + 1}
                    }
                    supabase.table('documents').insert(data).execute()
                    print(f"✅ Page {page_num + 1} Uploaded Successfully!\n")
                    success = True
                else:
                    print(f"❌ Embedding Failed for Page {page_num + 1}")
                    break

            except Exception as e:
                print(f"❌ Error on Page {page_num + 1}: {e}")
                print("⏳ Retrying in 5 seconds...")
                time.sleep(5)
                retries -= 1
        
        time.sleep(2)

def main():
    pdf_file = "knowledge/Untitled design.pdf"
    if os.path.exists(pdf_file):
        clear_database()
        process_pdf(pdf_file)
        print("\n🎉 All Pages Uploaded Successfully!")
    else:
        print("❌ PDF File not found!")

if __name__ == "__main__":
    main()