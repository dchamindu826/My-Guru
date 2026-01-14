import os
import time
import socket
import google.generativeai as genai
from supabase import create_client
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 1. Timeout එක විනාඩි 20ක් (තත්පර 1200) කරනවා. Slow Internet වුනාට කමක් නෑ.
socket.setdefaulttimeout(1200)

load_dotenv()

# Configs
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)

# ✅ Model: Gemini 1.5 Flash (Images + Text තේරුම් ගන්නා මොඩල් එක)
model = genai.GenerativeModel('gemini-2.0-flash')

# Smart Splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000, # Images විස්තර කරන නිසා ලොකු කෑලි ගමු
    chunk_overlap=200,
    separators=["\n\n", "\n", " ", ""]
)

def get_embedding(text):
    for attempt in range(3): # Embedding ෆේල් වුනොත් 3 පාරක් ට්‍රයි කරනවා
        try:
            time.sleep(1)
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"   ⚠️ Embedding retry ({attempt+1}/3)...")
            time.sleep(5)
    return None

def process_book_with_images(pdf_path):
    print(f"🚀 Uploading PDF to Google Brain: {pdf_path}...")
    print("   (This might take time depending on your internet. Please wait...)")
    
    try:
        # 1. Upload File
        pdf_file = genai.upload_file(pdf_path, mime_type="application/pdf")
        
        # Wait for processing
        while pdf_file.state.name == "PROCESSING":
            print("   ⏳ Google is reading the file...")
            time.sleep(5)
            pdf_file = genai.get_file(pdf_file.name)

        if pdf_file.state.name == "FAILED":
            print("❌ File processing failed.")
            return

        print("✅ PDF Uploaded! Now analyzing Images & Text...")

        # 2. විශේෂ Prompt එක: පින්තූරත් විස්තර කරන්න කියනවා
        prompt = """
        You are an expert textbook analyzer.
        Your task:
        1. Extract ALL text from this document accurately in Sinhala.
        2. LOOK AT EVERY IMAGE/DIAGRAM: If there is a diagram, describe it in detail in Sinhala. 
           (Example: "රූපය 5.4 මගින් පෙන්වන්නේ ආලෝක වර්තනයයි. එහි කිරණ ගමන් කරන ආකාරය...")
        3. Output everything as a continuous study note.
        """
        
        response = model.generate_content([pdf_file, prompt])
        full_content = response.text
        
        print(f"📖 Extracted {len(full_content)} characters (including image descriptions).")

        # 3. Chunk & Upload
        print("🧠 Smart Chunking...")
        chunks = text_splitter.split_text(full_content)
        
        print(f"📤 Uploading {len(chunks)} knowledge chunks to Database...")
        for i, chunk in enumerate(chunks):
            vector = get_embedding(chunk)
            if vector:
                data = {
                    "content": chunk,
                    "embedding": vector,
                    "metadata": {"source": os.path.basename(pdf_path), "type": "text+image_desc"}
                }
                supabase.table('documents').insert(data).execute()
                if (i+1) % 5 == 0:
                    print(f"   ✅ Uploaded {i+1}/{len(chunks)}")
        
        print(f"🎉 Success! '{os.path.basename(pdf_path)}' is fully ingested with Image Context.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

def main():
    folder_name = "knowledge"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        
    files = [f for f in os.listdir(folder_name) if f.endswith('.pdf')]
    
    if not files:
        print("⚠️ No PDFs found.")
        return
    
    print(f"⚡ Found {len(files)} PDFs.")
    
    for file in files:
        process_book_with_images(os.path.join(folder_name, file))

if __name__ == "__main__":
    main()