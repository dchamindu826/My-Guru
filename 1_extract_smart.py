import os
import time
import fitz  # PyMuPDF
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Gemini 2.0 Flash is best
model = genai.GenerativeModel('gemini-2.0-flash')

def extract_in_batches():
    folder_name = "knowledge"
    files = [f for f in os.listdir(folder_name) if f.endswith('.pdf')]
    
    if not files:
        print("❌ PDF එකක් නෑ!")
        return

    pdf_path = os.path.join(folder_name, files[0])
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    print(f"📘 සම්පූර්ණ පිටු ගණන: {total_pages}")
    
    # Text File එක මුලින් සුද්ද කරමු
    with open("full_book.txt", "w", encoding="utf-8") as f:
        f.write("")

    # පිටු 40 බැගින් කඩලා යවමු (Batch Size = 40)
    batch_size = 40
    
    for start_page in range(0, total_pages, batch_size):
        end_page = min(start_page + batch_size, total_pages)
        print(f"\n🚀 Processing Pages {start_page+1} to {end_page}...")

        # 1. තාවකාලික PDF කෑල්ලක් හදනවා
        new_doc = fitz.open()
        new_doc.insert_pdf(doc, from_page=start_page, to_page=end_page-1)
        temp_pdf_name = f"temp_part_{start_page}.pdf"
        new_doc.save(temp_pdf_name)
        new_doc.close()

        # 2. ඒ කෑල්ල Upload කරනවා
        try:
            pdf_file = genai.upload_file(temp_pdf_name, mime_type="application/pdf")
            
            while pdf_file.state.name == "PROCESSING":
                time.sleep(2)
                pdf_file = genai.get_file(pdf_file.name)

            print("   ✅ Uploaded! Analyzing...")

            # 3. Prompt (Images + Text)
            prompt = f"""
            Extract all text from pages {start_page+1} to {end_page} of this book in Sinhala.
            Describe every IMAGE and DIAGRAM in detail.
            Do not summarize. Output plain text.
            """
            
            response = model.generate_content([pdf_file, prompt])
            
            # 4. Save (Append) to File
            with open("full_book.txt", "a", encoding="utf-8") as f:
                f.write(f"\n\n--- PAGES {start_page+1} to {end_page} ---\n\n")
                f.write(response.text)

            print(f"   🎉 Part Done! ({len(response.text)} chars)")
            
        except Exception as e:
            print(f"   ❌ Error in this part: {e}")

        # Temp file එක මකනවා
        os.remove(temp_pdf_name)
        time.sleep(5) # Google ලිමිට් නොවදින්න පොඩි බ්‍රේක් එකක්

    print("\n✅ All parts extracted successfully to 'full_book.txt'!")

if __name__ == "__main__":
    extract_in_batches()