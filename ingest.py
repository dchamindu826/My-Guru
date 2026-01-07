import os
import google.generativeai as genai
from supabase import create_client, Client
from dotenv import load_dotenv
from pypdf import PdfReader

# 1. Config Load කරගැනීම
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Supabase Connect කිරීම
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"), 
    os.getenv("SUPABASE_KEY")
)

def get_embedding(text):
    # Gemini Embedding Model එක පාවිච්චි කරලා Text එක Numbers වලට හරවනවා
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document",
        title="O/L Content"
    )
    return result['embedding']

def process_pdf(pdf_path, subject, grade):
    print(f"🔄 Processing {pdf_path}...")
    
    reader = PdfReader(pdf_path)
    full_text = ""
    
    # පිටුවෙන් පිටුව කියවලා Text එක ගන්නවා
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"
            
    # Text එක කොටස් (Chunks) වලට කඩනවා (වචන 500න් 500ට වගේ)
    # ලොකු පාඩමක් එකපාර දාන්න බෑ, පොඩි කෑලි වලට කඩන්න ඕන
    chunk_size = 1000 
    chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
    
    print(f"📊 Found {len(chunks)} chunks. Uploading to Supabase...")

    for i, chunk in enumerate(chunks):
        try:
            vector = get_embedding(chunk)
            
            data = {
                "content": chunk,
                "metadata": {"subject": subject, "grade": grade, "chunk_index": i},
                "embedding": vector
            }
            
            # Database එකට Save කිරීම
            supabase.table("documents").insert(data).execute()
            print(f"✅ Chunk {i+1}/{len(chunks)} saved.")
            
        except Exception as e:
            print(f"❌ Error in chunk {i}: {e}")

if __name__ == "__main__":
    # මෙතන ඔයාගේ PDF file එකේ නම දෙන්න
    # PDF එක මේ folder එකටම දාගන්න ලේසියට
    pdf_name = "science_ol.pdf" 
    
    # PDF එකක් නැත්නම් දැනට මේ විදිහට test කරන්න text එකක් යවලා:
    # process_pdf("sample.pdf", "Science", "11") කියලා run කරන්න එපා file එක නැත්නම්.
    
    print("PDF එකක් project folder එකට දාලා code එකේ 'pdf_name' වෙනස් කරන්න.")
    # උදාහරණයට මම කෙලින්ම text එකක් දාන්නම් test කරන්න:
    
    sample_text = """
    විද්‍යාව 10 ශ්‍රේණිය - නිව්ටන්ගේ නියම.
    නිව්ටන්ගේ පළමු නියමය: බාහිර අසන්තුලිත බලයක් නොයෙදෙන තාක් කල් වස්තුවක් නිශ්චලතාවයේ හෝ ඒකාකාර ප්‍රවේගයෙන් සරල රේඛීයව චලනය වේ.
    නිව්ටන්ගේ දෙවන නියමය: වස්තුවක ගම්‍යතාව වෙනස් වීමේ වේගය යොදන බලයට අනුලෝමව සමානුපාතික වන අතර බලයේ දිශාවට සිදුවේ. F=ma.
    """
    
    print("Testing with sample text...")
    vec = get_embedding(sample_text)
    supabase.table("documents").insert({
        "content": sample_text,
        "metadata": {"subject": "Science", "topic": "Newton Laws"},
        "embedding": vec
    }).execute()
    
    print("🎉 Test Data Uploaded Successfully!")