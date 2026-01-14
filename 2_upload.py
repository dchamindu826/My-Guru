import os
import time
import google.generativeai as genai
from supabase import create_client
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

def get_embedding(text):
    try:
        time.sleep(1)
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except:
        return None

def upload_data():
    if not os.path.exists("full_book.txt"):
        print("❌ 'full_book.txt' නෑ! ඉස්සෙල්ලා Step 1 කරන්න.")
        return

    print("📖 Text File එක කියවමින්...")
    with open("full_book.txt", "r", encoding="utf-8") as f:
        text = f.read()

    chunks = text_splitter.split_text(text)
    print(f"🧩 කෑලි {len(chunks)} කට කැඩුවා. Upload කරමින්...")

    for i, chunk in enumerate(chunks):
        vector = get_embedding(chunk)
        if vector:
            data = {
                "content": chunk,
                "embedding": vector,
                "metadata": {"source": "Science Book"}
            }
            supabase.table('documents').insert(data).execute()
            print(f"   📤 Uploaded {i+1}/{len(chunks)}")

    print("\n🎉 සම්පූර්ණයෙන්ම ඉවරයි! දැන් Bot වැඩ.")

if __name__ == "__main__":
    upload_data()