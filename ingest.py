import os
import PyPDF2
import google.generativeai as genai
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Initialize Clients
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)

def get_embedding(text):
    """Generates vector embedding for text chunk"""
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document"
    )
    return result['embedding']

def process_pdf(file_path):
    print(f"📖 Reading: {file_path}...")
    text = ""
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"❌ Error reading PDF: {e}")
        return

    # Chunking (Text එක කොටස් වලට කැඩීම)
    # Gemini එකට එකපාර ලොකු ගොඩක් දාන්න බෑ, ඒකයි කඩන්නේ.
    chunk_size = 1000  # අකුරු 1000 කෑලි
    overlap = 200      # සම්බන්ධය තියාගන්න පොඩි කොටසක් රිපීට් කරනවා
    
    start = 0
    chunks = []
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += (chunk_size - overlap)

    print(f"🧩 Split into {len(chunks)} chunks. Uploading to DB...")

    # Upload to Supabase
    count = 0
    for chunk in chunks:
        try:
            vector = get_embedding(chunk)
            data = {
                "content": chunk,
                "embedding": vector,
                "metadata": {"source": os.path.basename(file_path)}
            }
            supabase.table('documents').insert(data).execute()
            count += 1
            print(f"✅ Chunk {count}/{len(chunks)} uploaded.")
        except Exception as e:
            print(f"⚠️ Upload failed for chunk: {e}")

def main():
    # 1. Folder එක බලන්න
    folder_name = "knowledge"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"📂 '{folder_name}' folder created. Please put your PDFs inside it and run again.")
        return

    # 2. PDF Files හොයන්න
    files = [f for f in os.listdir(folder_name) if f.endswith('.pdf')]
    
    if not files:
        print(f"⚠️ No PDFs found in '{folder_name}' folder.")
        return

    print(f"🚀 Found {len(files)} PDFs. Starting ingestion...")
    
    for file in files:
        file_path = os.path.join(folder_name, file)
        process_pdf(file_path)

    print("\n🎉 All Done! Your bot is now trained.")

if __name__ == "__main__":
    main()