import os
from supabase import create_client
from dotenv import load_dotenv

# Load Env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Connected to Supabase!")

    # 1. Health පාඩමට අදාල මුළු පිටු ගණන බලමු
    print("\n📊 Checking Page Count for 'Health'...")
    response = supabase.table("documents")\
        .select("*", count="exact")\
        .eq("metadata->>subject", "Health")\
        .execute()
    
    print(f"📄 Total Pages Found: {response.count}")
    
    if response.count == 0:
        print("❌ අවුලක්! Health විෂයට අදාල කිසිම Data එකක් නෑ. Upload එක Fail වෙලා.")
    else:
        print("✅ Data තියෙනවා (පිටු 193ක්)! දැන් අපි බලමු අකුරු හරියට තියෙනවද කියලා.")

        # 2. "ගුණාත්මකභාවය" කියන වචනේ තියෙන පිටුවක් හොයමු (.ilike පාවිච්චි කරලා)
        keyword = "ගුණාත්මකභාවය"
        print(f"\n🔍 Searching for keyword: '{keyword}'...")
        
        # % ලකුණ දැම්මම ඒ වචනේ කෑල්ලක් තිබුනත් අහු වෙනවා
        search_res = supabase.table("documents")\
            .select("content, metadata")\
            .ilike("content", f"%{keyword}%")\
            .limit(1)\
            .execute()

        if search_res.data:
            print("\n✅ Found Content! (මේ ටික කියවන්න පුළුවන්ද බලන්න):")
            print("-" * 50)
            print(search_res.data[0]['content'][:500]) # මුල් අකුරු 500 පෙන්වන්න
            print("-" * 50)
            print(f"📍 Source Info: {search_res.data[0]['metadata']}")
        else:
            print(f"❌ '{keyword}' කියන වචනේ හම්බුනේ නෑ. OCR එකේ අවුලක් වෙන්න පුළුවන්. හෝ සිංහල අකුරු කැඩිලා ඇති.")
            
            # වචනේ හම්බුනේ නැත්නම් නිකන් පිටුවක් අරන් බලමු මොනවා හරි තියෙනවද කියලා
            print("\n⚠️ නිකන් පිටුවක් අරන් බලමු අකුරු පේන විදිය:")
            random_page = supabase.table("documents").select("content").limit(1).execute()
            if random_page.data:
                print(random_page.data[0]['content'][:200])

except Exception as e:
    print(f"❌ Error: {e}")