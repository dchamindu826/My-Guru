import os
import time
import fitz  # PyMuPDF
import PIL.Image
import io
from supabase import create_client
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)
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
            time.sleep(5) # Wait 5 seconds
    return None

def process_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    print(f"📘 Processing PDF: {pdf_path} ({len(doc)} Pages)\n")

    for page_num, page in enumerate(doc):
        # Retry Logic for Generation
        success = False
        retries = 3
        
        while retries > 0 and not success:
            try:
                print(f"🔄 Processing Page {page_num + 1}...")
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_data = pix.tobytes("png")
                image = PIL.Image.open(io.BytesIO(img_data))

                # PROMPT: Images විස්තර කරන්න කියලත් දාමු
                prompt = """
                You are a Data Extraction Engine. 
                Extract content from this textbook page.
                
                RULES:
                1. Extract Sinhala/English text EXACTLY as shown.
                2. NO introductory phrases like "Here is the text".
                3. **CRITICAL:** If there is a diagram/image, describe it in detail inside brackets like this: 
                   [IMAGE: ක්‍රීඩකයින් දෙදෙනෙක් දැල අසල පන්දුව අවහිර කරන ආකාරය]
                4. Keep the text raw and clean.
                """
                
                response = model.generate_content([prompt, image])
                text_content = response.text.strip()

                if not text_content or len(text_content) < 20:
                    print(f"⚠️ Page {page_num + 1} is empty. Skipped.")
                    break

                # Preview
                print(f"   📄 Extracted: {text_content[:50]}...")

                # Embed & Upload
                vector = get_embedding_with_retry(text_content)
                
                if vector:
                    data = {
                        "content": text_content,
                        "embedding": vector,
                        "metadata": {"source": "Grade 10 Health", "page": page_num + 1}
                    }
                    supabase.table('documents').insert(data).execute()
                    print(f"   ✅ Page {page_num + 1} Uploaded!\n")
                    success = True
                else:
                    print(f"   ❌ Failed to get embedding for Page {page_num + 1}")
                    break

            except Exception as e:
                print(f"   ❌ Network Error on Page {page_num + 1}: {e}")
                print("   ⏳ Retrying in 5 seconds...")
                time.sleep(5)
                retries -= 1

def main():
    pdf_file = "knowledge/Untitled design.pdf" # නම හරියටම බලන්න
    if os.path.exists(pdf_file):
        clear_database()
        process_pdf(pdf_file)
        print("\n🎉 Upload Complete!")
    else:
        print("❌ File not found.")

if __name__ == "__main__":
    main()