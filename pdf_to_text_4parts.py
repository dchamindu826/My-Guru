import os
import time
import fitz  # PyMuPDF
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configs
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# මොඩල් එක (පින්තූර සහ සිංහල අකුරු වලට සුපිරිම එක)
model = genai.GenerativeModel('gemini-2.0-flash')

# ඔයා එවපු PDF එකේ නම (මේක knowledge ෆෝල්ඩර් එකේ තියෙන්න ඕන)
PDF_NAME = "Grade-10-Design-Electrical-And-Electronic-Technology-textbook-Sinhala-Medium-–-New-Syllabus.pdf"
PDF_PATH = os.path.join("knowledge", PDF_NAME)

def extract_part(doc, start_page, end_page, part_number):
    print(f"\n🔄 Processing Part {part_number} (Pages {start_page+1} to {end_page})...")
    
    # 1. කොටසට අදාල තාවකාලික PDF එකක් හදනවා
    temp_pdf = f"temp_part_{part_number}.pdf"
    new_doc = fitz.open()
    new_doc.insert_pdf(doc, from_page=start_page, to_page=end_page-1)
    new_doc.save(temp_pdf)
    new_doc.close()

    try:
        # 2. Gemini වෙත Upload කරනවා
        print("      ☁️ Uploading to Gemini...")
        pdf_file = genai.upload_file(temp_pdf, mime_type="application/pdf")
        
        # Process වෙනකම් ඉන්නවා
        while pdf_file.state.name == "PROCESSING":
            time.sleep(2)
            pdf_file = genai.get_file(pdf_file.name)

        # 3. Text + Image Description ගන්නවා
        print("      🧠 Extracting Text & Images...")
        prompt = """
        You are an expert textbook assistant. 
        Convert this PDF section into a rich text format suitable for RAG.
        
        RULES:
        1. Extract all Sinhala and English text exactly as it appears.
        2. **VERY IMPORTANT:** Whenever you see a circuit, diagram, tool, or photo, insert a tag `[IMAGE]` and describe it in detail in Sinhala.
           (Example: [IMAGE]: මෙහි දැක්වෙන්නේ ශ්‍රේණිගත පරිපථයකි. බල්බ දෙකක් සහ වෝල්ටීයතා ප්‍රභවයක් ඇත...)
        3. Keep the structure clear.
        """
        
        response = model.generate_content([pdf_file, prompt])
        content = response.text

        # 4. Text File එකක් විදියට Save කරනවා
        output_filename = f"textbook_part_{part_number}.txt"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"      ✅ Saved to '{output_filename}'")
        
        # Cloud එකෙන් මකලා දානවා
        genai.delete_file(pdf_file.name)

    except Exception as e:
        print(f"      ❌ Error: {e}")
    
    finally:
        if os.path.exists(temp_pdf):
            os.remove(temp_pdf)

def main():
    if not os.path.exists(PDF_PATH):
        print("❌ PDF එක හොයාගන්න බැහැ! 'knowledge' ෆෝල්ඩර් එකේ තියෙනවද බලන්න.")
        return

    doc = fitz.open(PDF_PATH)
    total_pages = len(doc)
    print(f"📚 Total Pages: {total_pages}")

    # කොටස් 4කට බෙදෙන ගාණ
    chunk_size = total_pages // 4
    
    # කොටස් 4 වෙන වෙනම යවනවා
    parts = [
        (0, chunk_size),                # Part 1
        (chunk_size, chunk_size * 2),   # Part 2
        (chunk_size * 2, chunk_size * 3), # Part 3
        (chunk_size * 3, total_pages)   # Part 4 (ඉතුරු ටික)
    ]

    for i, (start, end) in enumerate(parts):
        extract_part(doc, start, end, i + 1)
        
        if i < 3: # අන්තිම කොටසට පස්සේ ඉන්න ඕන නෑ
            print("      💤 Resting for 60s to save API Quota...")
            time.sleep(60) # විනාඩියක විවේකයක් (Error නොවදී යන්න)

    print("\n🎉 All 4 text files created successfully!")

if __name__ == "__main__":
    main()