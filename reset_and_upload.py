import os
from supabase import create_client
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
import google.generativeai as genai

load_dotenv()

# Configs
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)

TEXT_FILE = "unit_01.txt"  # ඔයා සේව් කරපු ෆයිල් එකේ නම

def get_embedding(text):
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document"
    )
    return result['embedding']

def main():
    print("🧹 Clearing old data from Database...")
    # පරණ ඩේටා ඔක්කොම මකනවා
    try:
        supabase.table('documents').delete().neq('id', 0).execute()
        print("✅ Database Cleared!")
    except Exception as e:
        print(f"⚠️ Clear warning (might be empty): {e}")

    print(f"📂 Reading {TEXT_FILE}...")
    try:
        with open(TEXT_FILE, "r", encoding="utf-8") as f:
            full_text = f.read()
    except FileNotFoundError:
        print("❌ Error: unit_01.txt ෆයිල් එක නෑ! ඒක මේ ෆෝල්ඩර් එකට දාන්න.")
        return

    # Text එක කෑලි වලට කඩනවා
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_text(full_text)

    print(f"🚀 Uploading {len(chunks)} chunks...")

    for i, chunk in enumerate(chunks):
        try:
            vector = get_embedding(chunk)
            data = {
                "content": chunk,
                "embedding": vector,
                "metadata": {"source": "Grade 10 - Unit 01"}
            }
            supabase.table('documents').insert(data).execute()
            if i % 5 == 0: print(f"   ⏳ Uploaded {i}/{len(chunks)}")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")

    print("🎉 All Done! Ready to test My Guru.")

if __name__ == "__main__":
    main()