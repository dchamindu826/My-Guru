import os
from supabase import create_client
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configs
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)

def test_search(query):
    print(f"\n🔎 Testing Query: '{query}'")
    print("-" * 50)
    
    # 1. Embed Query
    embedding = genai.embed_content(
        model="models/text-embedding-004",
        content=query,
        task_type="retrieval_query"
    )['embedding']

    # 2. Search in DB
    response = supabase.rpc("match_documents", {
        "query_embedding": embedding,
        "match_threshold": 0.3, # මේ අගය වෙනස් කරලා බලන්න පුළුවන්
        "match_count": 3
    }).execute()

    # 3. Print Results
    if not response.data:
        print("❌ No matches found in Database!")
    else:
        for i, doc in enumerate(response.data):
            print(f"\n📄 Match #{i+1} (Similarity Score: {doc['similarity']:.4f})")
            print(f"📖 Page: {doc['metadata'].get('page', 'Unknown')}")
            print(f"📝 Content Preview: {doc['content'][:200]}...") # මුල් අකුරු 200 පෙන්වන්න
            print("-" * 30)

# මෙතන ඔයාට සැක ප්‍රශ්නය ගහලා බලන්න
test_search("සෞඛ්‍යය යනු කුමක්ද?") 
test_search("පෝෂ්‍ය පදාර්ථ වර්ග")