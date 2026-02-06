from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
from google import genai
import os
import re
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List

load_dotenv()

app = FastAPI()

# --- CORS CONFIG ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins (Update for production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CLIENTS ---
# Ensure these env vars are set in your VPS .env file
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# --- DATA MODELS ---
class ChatRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    message: str
    subject: str
    grade: str
    medium: str

# --- 1. IMAGE LOGIC (Strict Mode - From your Streamlit Code) ---
def get_relevant_images(context_strings, subject, medium):
    """
    STRICT MODE: Only fetch images if specific 'Figure IDs' (e.g., 4.5, 10.2)
    are found in the retrieved text. No fallback to page numbers.
    """
    image_hits = {} 
    found_fig_ids = set()

    # 1. Scan text for Figure IDs (Regex: Digit.Digit)
    if context_strings:
        for text in context_strings:
            # Finds patterns like 4.5, 10.1, 8.3
            ids = re.findall(r"(\d+\.\d+)", text)
            for fig_id in ids:
                found_fig_ids.add(fig_id)
    
    # 2. Fetch Exact Figure Matches
    if found_fig_ids:
        # Limit to top 3 relevant figures to avoid clutter
        target_ids = list(found_fig_ids)[:3]
        
        for fid in target_ids:
            try:
                # Query content_library for description containing "Figure X.Y"
                response = supabase.table("content_library") \
                    .select("image_url, description") \
                    .eq("subject", subject) \
                    .eq("medium", medium) \
                    .ilike("description", f"%Figure {fid}%") \
                    .limit(1) \
                    .execute()
                
                if response.data:
                    for img in response.data:
                        # Use image_url as key to avoid duplicates
                        image_hits[img['image_url']] = img['image_url']
            except Exception as e:
                print(f"Error fetching Figure {fid}: {e}")

    return list(image_hits.values())

# --- 2. RAG SEARCH LOGIC (From your Streamlit Code) ---
def search_database(query, grade, subject, medium):
    all_hits = []
    # Simplified keyword search logic (assuming query itself is the keyword string for now)
    # In Streamlit, you extracted keywords. Here we use the whole query or basic split.
    keywords = query.split() 
    
    for kw in keywords:
        if len(kw) < 3: continue # Skip small words

        query_builder = supabase.table("documents").select("content, metadata")
        # Assuming metadata structure matches exactly what you had
        # Note: Supabase JSON filtering syntax might vary slightly based on your setup
        # Here using basic text search approach for compatibility
        
        response = query_builder \
            .eq("metadata->>grade", grade) \
            .eq("metadata->>subject", subject) \
            .eq("metadata->>medium", medium) \
            .ilike("content", f"%{kw}%") \
            .limit(5) \
            .execute()
            
        for item in response.data: 
            all_hits.append(item['content'])
            
    return list(set(all_hits))

# --- API ENDPOINTS ---

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    # 1. Check User & Credits
    try:
        user_res = supabase.table("profiles").select("plan_type, credits_left").eq("id", req.user_id).single().execute()
        if not user_res.data:
            # Handle guest or create profile logic if needed, skipping for now
            pass 
        else:
            plan = user_res.data['plan_type']
            credits = user_res.data['credits_left']

            if plan != "genius" and credits <= 0:
                return {
                    "answer": "⚠️ අයියෝ පුතේ! ඔයාගේ දවසේ ප්‍රශ්න ප්‍රමාණය ඉවරයි. Unlimited Plan එක අරගන්න.",
                    "status": "no_credits"
                }
    except:
        pass

    # 2. Get Context (RAG)
    context_data = search_database(req.message, req.grade, req.subject, req.medium)
    context_text = "\n---\n".join(context_data) if context_data else "No specific context found."

    # 3. Create Session if needed
    session_id = req.session_id
    if not session_id:
        title = " ".join(req.message.split()[:4]) + "..."
        session_res = supabase.table("chat_sessions").insert({
            "user_id": req.user_id,
            "subject": req.subject,
            "title": title
        }).execute()
        session_id = session_res.data[0]['id']

    # 4. Generate Answer (Gemini)
    prompt = f"""
    You are an expert Sri Lankan O/L Tutor.
    
    SETTINGS:
    - Subject: {req.subject}
    - Medium: {req.medium} (CRITICAL: Answer in this language)
    
    CONTEXT DATA:
    {context_text}
    
    USER QUESTION: {req.message}
    
    INSTRUCTIONS:
    1. **Persona**: Be friendly. Explain clearly like a teacher.
    2. **Handling "CONCEPTS"**:
       - Define first.
       - Break down into Pillars/Components using Bullet Points.
       - Conclude.
    3. **Handling "LISTS"**: Preserve exact order from text.
    4. **Images**: If you see Figure IDs (e.g., 4.5) in the context, refer to them (e.g., "See Figure 4.5").
    5. **Language**: 
       - If Medium=English -> English ONLY.
       - If Medium=Sinhala -> Sinhala ONLY.
    """
    
    try:
        gemini_res = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        answer = gemini_res.text
    except Exception as e:
        answer = "සමාවෙන්න, තාක්ෂණික දෝෂයක්. කරුණාකර නැවත උත්සාහ කරන්න."

    # 5. Get Images (Strict Mode)
    # We pass the *context_data* to find figure IDs, just like in Streamlit code
    image_urls = get_relevant_images(context_data, req.subject, req.medium)
    
    # Take the first image if available (Streamlit code displayed list, API returns one or list)
    # Let's return the first one for the chat bubble, or handle list in frontend
    main_image = image_urls[0] if image_urls else None

    # 6. Save Messages
    supabase.table("chat_messages").insert([
        {"session_id": session_id, "role": "user", "content": req.message},
        {"session_id": session_id, "role": "ai", "content": answer, "image_url": main_image}
    ]).execute()

    # 7. Deduct Credit
    try:
        if user_res.data['plan_type'] != "genius":
            supabase.table("profiles").update({"credits_left": user_res.data['credits_left'] - 1}).eq("id", req.user_id).execute()
    except:
        pass

    return {
        "session_id": session_id,
        "answer": answer,
        "image_url": main_image,
        "credits_left": user_res.data['credits_left'] - 1 if user_res.data else 0,
        "status": "success"
    }

# --- SESSIONS ENDPOINT ---
@app.get("/sessions/{user_id}")
async def get_sessions(user_id: str):
    res = supabase.table("chat_sessions").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    return res.data

# --- MESSAGES ENDPOINT ---
@app.get("/messages/{session_id}")
async def get_messages(session_id: str):
    res = supabase.table("chat_messages").select("*").eq("session_id", session_id).order("created_at", desc=True).execute()
    return res.data[::-1] # Return oldest first for chat history