import os
import google.generativeai as genai
from supabase import create_client
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
import time

load_dotenv()

# Configs
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)

# Splitter Configuration (ලොකු chunks ගමු, image descriptions කැඩෙන එක වලක්වන්න)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=200,
    separators=["\n\n", "\n", " ", ""]
)

def get_embedding(text):
    try:
        time.sleep(1) # Rate limit protection
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        print(f"⚠️ Embedding Error: {e}")
        return None

def main():
    file_path = "knowledge/full_book.txt"
    
    if not os.path.exists(file_path):
        print("❌ File not found! Please put 'full_book.txt' in 'knowledge' folder.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    print(f"📖 Read {len(full_text)} characters.")
    
    # Chunking
    chunks = text_splitter.split_text(full_text)
    print(f"🧩 Created {len(chunks)} chunks. Uploading...")

    for i, chunk in enumerate(chunks):
        vector = get_embedding(chunk)
        if vector:
            data = {
                "content": chunk,
                "embedding": vector,
                "metadata": {"source": "textbook_v1"}
            }
            try:
                supabase.table('documents').insert(data).execute()
                print(f"✅ Uploaded Chunk {i+1}/{len(chunks)}")
            except Exception as e:
                print(f"❌ Upload Error: {e}")

    print("🎉 All Done! Database ready.")

if __name__ == "__main__":
    main()