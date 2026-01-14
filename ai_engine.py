import os
import google.generativeai as genai
from supabase import create_client
from dotenv import load_dotenv
import whatsapp_utils

load_dotenv()

# Setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash') # Best for Multimodal

def get_rag_context(query_text):
    """Database එකෙන් අදාල විස්තර හොයනවා"""
    try:
        embedding = genai.embed_content(
            model="models/text-embedding-004",
            content=query_text,
            task_type="retrieval_query"
        )['embedding']

        response = supabase.rpc(
            'match_documents',
            {
                'query_embedding': embedding,
                'match_threshold': 0.3,
                'match_count': 5
            }
        ).execute()

        return "\n\n".join([doc['content'] for doc in response.data])
    except Exception as e:
        print(f"RAG Error: {e}")
        return ""

def generate_guru_response(user_input, context, media_file=None, media_type=None):
    """ශිෂ්‍යයාට උත්තරේ හදනවා (Text, Audio හෝ Image inputs එක්ක)"""
    
    system_prompt = f"""
    ඔයාගේ නම 'My Guru'. ඔයා කරුණාවන්ත ගුරුවරයෙක්.
    
    උපදෙස්:
    1. ශිෂ්‍යයාට "පුතේ" හෝ "දුවේ" කියන්න.
    2. ඉතාම සරල සිංහලෙන් උත්තර දෙන්න.
    3. පහත දී ඇති [CONTEXT] (පොතේ විස්තර) පාවිච්චි කරලම උත්තර දෙන්න.
    4. ශිෂ්‍යයා පින්තූරයක් එව්වොත්, ඒක පොතේ තියෙන දෙයක් එක්ක ගලපලා විස්තර කරන්න.
    5. Context එකේ නැති දෙයක් ඇහුවොත්, "පුතේ, ඒක අපේ පාඩම් පොතේ නෑනේ" කියලා කියන්න.

    [CONTEXT FROM TEXTBOOK]:
    {context}
    """

    content_payload = [system_prompt]
    
    # Image හෝ Audio ෆයිල් එකක් තියෙනවා නම් Prompt එකට එකතු කරනවා
    if media_file:
        file_ref = genai.upload_file(media_file)
        content_payload.append(file_ref)
        if media_type == "image":
            content_payload.append("මේ පින්තූරය හොඳින් බලලා, Context එකේ තියෙන දැනුම පාවිච්චි කරලා ශිෂ්‍යයාට මේක පැහැදිලි කරන්න.")
        elif media_type == "audio":
            content_payload.append("මේ Audio එක අහලා, ශිෂ්‍යයා අහන ප්‍රශ්නයට Context එකෙන් උත්තර දෙන්න.")

    # User ගේ ප්‍රශ්නය අන්තිමට
    content_payload.append(f"ශිෂ්‍යයාගේ ප්‍රශ්නය: {user_input}")

    try:
        response = model.generate_content(content_payload)
        return response.text
    except Exception as e:
        return "පුතේ, මට පොඩි තාක්ෂණික ගැටලුවක් ආවා. ආයෙත් අහන්නකෝ."

async def process_message(phone_number, message_body, message_type, media_id=None):
    user_query = ""
    media_path = None
    retrieved_context = ""

    # 1. Handle Voice / Audio
    if message_type == "audio" and media_id:
        print("🎙️ Processing Audio...")
        media_url = whatsapp_utils.get_media_url(media_id)
        media_path = whatsapp_utils.download_media(media_url, "ogg") # WhatsApp uses OGG
        # Audio එකේ මොකක්ද තියෙන්නේ කියලා දන්නේ නැති නිසා Context එක ගන්න බෑ තාම.
        # ඒක නිසා අපි කෙලින්ම Gemini ට යවනවා Audio එක + "Answer based on general knowledge first" 
        # (Ideal method: Transcribe first, then search DB. But Gemini 1.5 handles audio directly well)
        # හොඳම ක්‍රමය: ඉස්සෙල්ලා Audio එක Text කරන්න.
        
        audio_file = genai.upload_file(media_path)
        transcription = model.generate_content([audio_file, "Transcribe this audio to Sinhala text exactly."]).text
        print(f"🗣️ Transcribed: {transcription}")
        user_query = transcription
        
    # 2. Handle Image
    elif message_type == "image" and media_id:
        print("🖼️ Processing Image...")
        media_url = whatsapp_utils.get_media_url(media_id)
        media_path = whatsapp_utils.download_media(media_url, "jpeg")
        user_query = message_body if message_body else "මේ පින්තූරය විස්තර කරන්න."
        
        # පින්තූරයේ තියෙන්නේ මොකක්ද කියලා මුලින්ම බලමු (Context search කරන්න)
        img_file = genai.upload_file(media_path)
        img_desc = model.generate_content([img_file, "What is in this image? Describe in 2 sentences."]).text
        print(f"🖼️ Image Concept: {img_desc}")
        
        # Image Concept එකෙන් පොතේ විස්තර හොයමු
        retrieved_context = get_rag_context(img_desc)

    # 3. Handle Text
    else:
        user_query = message_body
        retrieved_context = get_rag_context(user_query)

    # RAG නැතුව Audio ආවා නම් දැන් RAG කරන්න
    if message_type == "audio":
        retrieved_context = get_rag_context(user_query)

    # Generate Final Answer
    # Image එකක් නම් media_path යවනවා, නැත්නම් නිකන් Text
    if message_type == "image":
        ai_reply = generate_guru_response(user_query, retrieved_context, media_path, "image")
    else:
        # Audio එක Text කලානේ, ඒක දැන් Text message එකක් වගේමයි
        ai_reply = generate_guru_response(user_query, retrieved_context)

    # Clean up temp files
    if media_path and os.path.exists(media_path):
        os.remove(media_path)

    # Send to WhatsApp
    whatsapp_utils.send_whatsapp_message(phone_number, ai_reply)