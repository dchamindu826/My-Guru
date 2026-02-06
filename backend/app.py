import streamlit as st
from supabase import create_client
from google import genai
import json
import os
import time
import re
from dotenv import load_dotenv

# --- PAGE CONFIG (Dark Mode Default) ---
st.set_page_config(
    page_title="My Guru AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)
load_dotenv()

# --- FORCE DARK THEME & SINHALA FONT STYLING ---
st.markdown("""
<style>
    /* Import Noto Sans Sinhala (Best for Sri Lankan Apps) */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Sinhala:wght@400;500;700&family=Inter:wght@400;600&display=swap');

    /* Force Dark Theme Backgrounds */
    [data-testid="stAppViewContainer"] {
        background-color: #0E1117;
        color: #E0E0E0;
    }
    [data-testid="stSidebar"] {
        background-color: #161B22;
        border-right: 1px solid #30363D;
    }
    
    /* Apply Sinhala Font Globally */
    html, body, [class*="css"], .stMarkdown, .stButton, .stSelectbox {
        font-family: 'Noto Sans Sinhala', 'Inter', sans-serif !important;
    }

    /* Remove Default Streamlit Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Chat Input Styling */
    .stChatInput input {
        background-color: #161B22 !important;
        color: white !important;
        border: 1px solid #30363D !important;
        border-radius: 10px;
    }

    /* Clean Sidebar Titles */
    .sidebar-title {
        font-size: 22px;
        font-weight: 700;
        background: -webkit-linear-gradient(45deg, #00C6FF, #0072FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 20px;
    }

    /* Chat Messages - More Spacing for Sinhala */
    .stChatMessage {
        line-height: 1.6; /* Increases readability for Sinhala */
    }
    
    /* Image Styling */
    .stImage img {
        border-radius: 10px;
        border: 1px solid #30363D;
        margin-top: 10px;
        margin-bottom: 10px;
        max-width: 100%;
    }

    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #0E1117; 
    }
    ::-webkit-scrollbar-thumb {
        background: #30363D; 
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# --- API CONNECTION ---
try:
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
except Exception as e:
    st.error(f"Configuration Error: {e}")
    st.stop()

# --- HELPER: JSON CLEANER ---
def clean_json_text(text):
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

# --- HELPER: API RETRY LOGIC ---
def safe_google_api_call(contents, config=None, retries=3):
    for attempt in range(retries):
        try:
            if config:
                return client.models.generate_content(model='gemini-2.0-flash', contents=contents, config=config)
            else:
                return client.models.generate_content(model='gemini-2.0-flash', contents=contents)
        except Exception as e:
            if "429" in str(e):
                time.sleep((attempt + 1) * 2)
                continue
            return None
    return None

# --- NEW: STRICT IMAGE RETRIEVAL LOGIC ---
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
                        image_hits[img['image_url']] = img
            except Exception as e:
                print(f"Error fetching Figure {fid}: {e}")

    return list(image_hits.values())

# --- CORE LOGIC ---
@st.cache_data(ttl=3600)
def process_user_query(user_input, subject, medium):
    prompt = f"""
    ROLE: Transliteration Engine.
    INPUT: "{user_input}"
    CONTEXT: Subject={subject}, Medium={medium}
    INSTRUCTIONS: 
    1. Transliterate Singlish to Sinhala phonetically (e.g., "awadi"->"අවධි").
    2. Identify intent.
    OUTPUT JSON ONLY: {{ "interpreted_question": "...", "search_keywords": [...] }}
    """
    try:
        res = safe_google_api_call(prompt, config={'response_mime_type': 'application/json'})
        if res and res.text:
            cleaned_text = clean_json_text(res.text)
            return json.loads(cleaned_text)
        return None
    except: return None

def search_database(keywords, filters):
    all_hits = []
    for kw in keywords:
        query = supabase.table("documents").select("content, metadata")
        if filters.get('subject'): query = query.eq("metadata->>subject", filters['subject'])
        if filters.get('medium'): query = query.eq("metadata->>medium", filters['medium'])
        query = query.ilike("content", f"%{kw}%").limit(8)
        results = query.execute()
        for item in results.data: all_hits.append(item['content'])
    return list(set(all_hits))

def generate_final_answer(context_data, user_question, subject, medium):
    if not context_data:
        return "⚠️ මට ඒ ගැන කරුණු සොයාගැනීමට නොහැකි විය. කරුණාකර වෙනත් විදියකට අසා බලන්න. (No notes found)"
    
    context_text = "\n---\n".join(context_data)
    
    prompt = f"""
    You are an expert Sri Lankan O/L Tutor.
    
    SETTINGS:
    - Subject: {subject}
    - Medium: {medium} (CRITICAL: Answer in this language)
    
    CONTEXT DATA:
    {context_text}
    
    USER QUESTION: {user_question}
    
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
    res = safe_google_api_call(prompt)
    return res.text if res else "System busy. Please try again."

# ==========================================
# 💎 MINIMALIST UI (DARK MODE + SINHALA FONT)
# ==========================================

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR (CLEAN) ---
with st.sidebar:
    st.markdown('<div class="sidebar-title">🎓 My Guru AI</div>', unsafe_allow_html=True)
    
    selected_subject = st.selectbox(
        "📖 Select Subject", 
        ["Health", "Science", "History", "ICT", "English", "Sinhala", "Buddhism"]
    )
    
    selected_medium = st.selectbox(
        "🗣️ Medium", 
        ["Sinhala", "English"]
    )
    
    st.markdown("---")
    
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --- MAIN CHAT AREA ---
st.title(f"📚 O/L {selected_subject} Tutor")

# Display History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # Render Images from History if they exist
        if "images" in message and message["images"]:
            for img in message["images"]:
                st.image(img['url'], caption=img.get('description', 'Figure'), width=400)

# User Input
placeholder_text = "Type your question here..." if selected_medium == "English" else "ඔබේ ප්‍රශ්නය මෙතන ටයිප් කරන්න..."
user_input = st.chat_input(placeholder_text)

if user_input:
    # 1. User Message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. AI Response
    with st.chat_message("assistant"):
        with st.spinner("සටහන් පරීක්ෂා කරමින්..."):
            
            # Logic
            decoded = process_user_query(user_input, selected_subject, selected_medium)
            
            if decoded:
                interpreted_q = decoded['interpreted_question']
                keywords = decoded['search_keywords']
                
                # Search Text
                context = search_database(keywords, {'subject': selected_subject, 'medium': selected_medium})
                
                if context:
                    # Generate Answer
                    answer = generate_final_answer(context, interpreted_q, selected_subject, selected_medium)
                    
                    # --- NEW: Get Images (Strict Mode) ---
                    # Only gets images if Figure IDs (4.5 etc) are found in text
                    relevant_images = get_relevant_images(context, selected_subject, selected_medium)
                    
                    st.markdown(answer)
                    
                    # Show Images
                    image_data_list = []
                    if relevant_images:
                        for img in relevant_images:
                            st.image(img['image_url'], caption=img.get('description', 'Figure'), width=400)
                            image_data_list.append({
                                'url': img['image_url'],
                                'description': img.get('description', 'Figure')
                            })
                    
                    # Save to History
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": answer,
                        "images": image_data_list
                    })
                else:
                    error_msg = f"😕 සමාවෙන්න, **{interpreted_q}** ගැන සටහන් සොයාගැනීමට නොහැකි විය."
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
            else:
                st.error("System busy. Please try again.")