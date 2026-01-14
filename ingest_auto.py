import os
import time
import google.generativeai as genai
from supabase import create_client
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from google.api_core import retry

load_dotenv()

# Configs
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel('gemini-1.5-flash')

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=200
)

def get_embedding(text):
    """Embeddings ගන්නකොට Error ආවොත් 3 පාරක් Try කරනවා"""
    for attempt in range(3):
        try:
            time.sleep(1) 
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"      ⚠️ Embedding Retry ({attempt+1}/3)...")
            time.sleep(5)
    return None

def upload_file_with_retry(path, max_retries=5):
    """File Upload එක ෆේල් වුනොත් 5 පාරක් Try කරනවා"""
    for attempt in range(max_retries):
        try:
            print(f"      ☁️ Uploading... (Attempt {attempt+1})")
            pdf_file = genai.upload_file(path, mime_type="application/pdf")
            return pdf_file
        except Exception as e:
            print(f"      ⚠️ Upload Failed: {e}")
            print("      ⏳ Waiting 10 seconds before retrying...")
            time.sleep(10)
    raise Exception("❌ Upload failed after 5 attempts. Check Internet.")

def generate_content_with_retry(model, prompt_parts, max_retries=3):
    """Gemini Response එක ගන්නකොට Error ආවොත් 3 පාරක් Try කරනවා"""
    for attempt in range(max_retries):
        try:
            # timeout එක විනාඩි 10ක් (600s) දෙනවා
            response = model.generate_content(prompt_parts, request_options={'timeout': 600})
            return response
        except Exception as e:
            print(f"      ⚠️ Generation Failed: {e}")
            print("      ⏳ Waiting 20 seconds...")
            time.sleep(20)
    raise Exception("❌ Generation failed.")

def process_pdf_automatically(pdf_path):
    filename = os.path.basename(pdf_path)
    print(f"\n🚀 Processing: {filename} ...")

    try:
        # 1. Upload PDF with Retry
        pdf_file = upload_file_with_retry(pdf_path)
        
        # Wait for processing
        while pdf_file.state.name == "PROCESSING":
            print("      ⏳ Google is processing the file...")
            time.sleep(5)
            pdf_file = genai.get_file(pdf_file.name)

        if pdf_file.state.name == "FAILED":
            print("   ❌ Google processing failed internally.")
            return

        print("   ✅ Upload Complete. Extracting Content...")

        # 2. Convert PDF to Text
        prompt = """
        You are an expert textbook digitizer. 
        Your task is to convert this entire PDF into structured text.
        
        RULES:
        1. Extract all text accurately in its original language (Sinhala/English).
        2. **CRITICAL:** When you see an image, diagram, or chart, insert a tag `[IMAGE]` and describe it in detail in Sinhala.
        3. Do not summarize. Keep all educational content.
        4. Output format: Plain Text.
        """
        
        response = generate_content_with_retry(model, [pdf_file, prompt])
        
        full_text = response.text
        print(f"   📖 Extracted {len(full_text)} characters.")

        # 3. Clean up
        try:
            genai.delete_file(pdf_file.name)
        except:
            pass

        # 4. Chunk & Upload
        print("   🔪 Chunking text...")
        chunks = text_splitter.split_text(full_text)
        
        print(f"   📤 Uploading {len(chunks)} chunks to Supabase...")
        
        for i, chunk in enumerate(chunks):
            vector = get_embedding(chunk)
            if vector:
                data = {
                    "content": chunk,
                    "embedding": vector,
                    "metadata": {"source": filename, "type": "auto_ingest"}
                }
                # Database upload එකටත් පොඩි retry එකක්
                for db_attempt in range(3):
                    try:
                        supabase.table('documents').insert(data).execute()
                        break
                    except Exception as e:
                        time.sleep(2)
        
        print(f"   🎉 {filename} Done!")

    except Exception as e:
        print(f"   ❌ Critical Error processing {filename}: {e}")

def main():
    folder_path = "knowledge"
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        return

    files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]
    
    if not files:
        print("⚠️ No PDFs found.")
        return

    print(f"📚 Found {len(files)} PDFs. Starting Auto-Ingestion...")
    
    for file in files:
        process_pdf_automatically(os.path.join(folder_path, file))
        time.sleep(5)

if __name__ == "__main__":
    main()