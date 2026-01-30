import os
import time
import fitz  # PyMuPDF
import PIL.Image
import io
from supabase import create_client
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, InternalServerError

# Load Environment Variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel('gemini-2.0-flash')

# =====================================
# 🔥 HEAVY RETRY LOGIC (Rate Limits වළක්වන්න)
# =====================================

def get_embedding_with_retry(text, retries=5):
    """Embedding එක ගන්න Rate Limits Handle කරමින්"""
    delay = 10
    for attempt in range(retries):
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']

        except (ResourceExhausted, ServiceUnavailable, InternalServerError):
            print(f"   ⚠️ Rate Limit Hit (Embedding). Waiting {delay}s...")
            time.sleep(delay)
            delay *= 2
            
        except Exception as e:
            print(f"   ❌ Embedding Error: {e}")
            if "404" in str(e):
                try:
                    result = genai.embed_content(
                        model="models/embedding-001",
                        content=text,
                        task_type="retrieval_document"
                    )
                    return result['embedding']
                except:
                    pass
            time.sleep(5)
            
    return None

def generate_content_with_retry(prompt, image, retries=5):
    """OCR එක Run කරන Rate Limits Handle කරමින්"""
    delay = 20
    for attempt in range(retries):
        try:
            response = model.generate_content([prompt, image])
            return response.text.strip()
            
        except (ResourceExhausted, ServiceUnavailable, InternalServerError):
            print(f"   ⚠️ Rate Limit Hit (OCR). Waiting {delay}s...")
            time.sleep(delay)
            delay *= 2
            
        except Exception as e:
            print(f"   ❌ OCR Error: {e}")
            time.sleep(10)
            
    return None

# =====================================
# 📚 PDF PROCESSING FUNCTION
# =====================================

def process_pdf(pdf_path, start_page, end_page, grade, subject, doc_type, medium):
    """
    PDF එකක් Process කරලා Database එකට දාන Function
    
    Parameters:
    - pdf_path: PDF file එකේ path (උදා: "knowledge/science_g10.pdf")
    - start_page: කොයි පිටුවෙන් පටන් ගන්නද (උදා: 1)
    - end_page: කොයි පිටුවේ ඉවර කරන්නද (උදා: 200)
    - grade: ශ්‍රේණිය (උදා: 10 හෝ 11)
    - subject: විෂය (උදා: "Science", "Mathematics", "History")
    - doc_type: ලේඛන වර්ගය ("Textbook", "Paper", "Marking Scheme")
    - medium: භාෂාව ("Sinhala" හෝ "English")
    """
    
    doc = fitz.open(pdf_path)
    print(f"\n{'='*70}")
    print(f"📘 Processing: Grade {grade} - {subject} ({medium})")
    print(f"📂 Document Type: {doc_type}")
    print(f"📄 Total Pages in PDF: {len(doc)}")
    print(f"🎯 Selected Range: Page {start_page} to {end_page}")
    print(f"{'='*70}\n")

    for page_num, page in enumerate(doc):
        current_page = page_num + 1

        # Page Range Check
        if current_page < start_page:
            continue
        
        if current_page > end_page:
            print(f"🛑 Reached End Page ({end_page}). Stopping.")
            break

        print(f"🔄 Processing Page {current_page}...")
        
        # 1. Image Capture (High Quality)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_data = pix.tobytes("png")
        image = PIL.Image.open(io.BytesIO(img_data))

        # 2. OCR Prompt (Medium අනුව වෙනස් වෙනවා)
        if medium == "Sinhala":
            prompt = """
            You are a highly accurate OCR engine for Sinhala language educational content.
            Task: Extract all text from this page exactly as it appears.
            
            RULES:
            1. OUTPUT RAW TEXT ONLY (No markdown, no formatting).
            2. Preserve numbering and structure.
            3. For diagrams/images: [රූපය: සංක්ෂිප්ත විස්තරය]
            4. NO CHATTER - Just give the text.
            """
        else:  # English
            prompt = """
            You are a highly accurate OCR engine for English language educational content.
            Task: Extract all text from this page exactly as it appears.
            
            RULES:
            1. OUTPUT RAW TEXT ONLY (No markdown, no formatting).
            2. Preserve numbering and structure.
            3. For diagrams/images: [Image: brief description]
            4. NO CHATTER - Just give the text.
            """
        
        # 3. OCR විසින් Text Extract කරන්න
        text_content = generate_content_with_retry(prompt, image)

        if not text_content or len(text_content) < 20:
            print(f"⚠️ Page {current_page} seems empty or failed. Skipped.")
            time.sleep(5)
            continue

        # 4. Preview (පළමු 200 characters)
        print("\n" + "-"*70)
        print(f"📄 PAGE {current_page} PREVIEW:")
        print("-"*70)
        print(text_content[:200] + "...")
        print("-"*70 + "\n")

        # 5. Embedding Vector එක Generate කරන්න
        vector = get_embedding_with_retry(text_content)
        
        if not vector:
            print(f"❌ Failed to generate embedding for Page {current_page}. Skipping.")
            time.sleep(10)
            continue

        # 6. Database එකට Save කරන්න
        data = {
            "content": text_content,
            "embedding": vector,
            "metadata": {
                "source": f"Grade {grade} {subject} ({medium}) - {doc_type}",
                "page": current_page,
                "grade": str(grade),        # Filter කරන්න පුළුවන් විදිහට
                "subject": subject,
                "medium": medium,
                "type": doc_type
            }
        }
        
        try:
            supabase.table('documents').insert(data).execute()
            print(f"✅ Page {current_page} uploaded successfully!")
            print(f"   Grade: {grade} | Subject: {subject} | Medium: {medium} | Type: {doc_type}\n")
        except Exception as e:
            print(f"❌ Database Error on Page {current_page}: {e}\n")
        
        # 7. Cooling Period (Rate Limits වළක්වන්න)
        print("⏳ Cooling down for 15 seconds...")
        time.sleep(15)

    print(f"\n{'='*70}")
    print(f"🎉 PDF Processing Completed!")
    print(f"{'='*70}\n")

# =====================================
# 🚀 MAIN FUNCTION
# =====================================

def main():
    """
    👇 මෙතන තමයි Upload Details වෙනස් කරන්න ඕනේ
    """
    
    # ---------------------------------
    # 📝 UPLOAD CONFIGURATION
    # ---------------------------------
    
    PDF_FILE = "knowledge/health 10.pdf"  # PDF file එකේ path
    
    GRADE = 10                   # ශ්‍රේණිය (10 හෝ 11)
    SUBJECT = "Health"           # විෂය (Science, Mathematics, History, etc.)
    DOC_TYPE = "Textbook"         # Textbook / Paper / Marking Scheme
    MEDIUM = "Sinhala"            # Sinhala / English
    
    START_PAGE = 9                # මෙතනින් පටන් ගන්නවා
    END_PAGE = 238                # මෙතනින් ඉවර වෙනවා
    
    # ---------------------------------
    
    # Validation
    if not os.path.exists(PDF_FILE):
        print(f"❌ ERROR: PDF file not found at: {PDF_FILE}")
        print("   Please check the file path and try again.")
        return
    
    # Start Processing
    print("🚀 Starting PDF Upload Process...")
    process_pdf(PDF_FILE, START_PAGE, END_PAGE, GRADE, SUBJECT, DOC_TYPE, MEDIUM)
    print("✅ Upload process completed successfully!")

if __name__ == "__main__":
    main()