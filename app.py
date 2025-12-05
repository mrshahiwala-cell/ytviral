import streamlit as st
import requests
from datetime import datetime, timedelta
import google.generativeai as genai
from PIL import Image
import io
import pandas as pd

# ======================= CONFIG =======================
st.set_page_config(page_title="YouTube Viral Hunter Pro", layout="wide")
st.title("YouTube Viral Hunter Pro 2025")
st.markdown("### Aaj ke sabse tezi se viral ho rahe videos – bilkul free!")

# ======================= API KEYS =======================
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]

# ←←←← YAHAN APNI GEMINI KEY PASTE KAR DO
GEMINI_API_KEY = "AIzaSyAuxEnMZXoYmZZtKEqAVJ7GdQ-VVHSgryg"

# Agar code mein nahi daali to secrets se try karega
if GEMINI_API_KEY == "AIzaSyAuxEnMZXoYmZZtKEqAVJ7GdQ-VVHSgryg":
    try:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    except:
        st.error("Gemini API key nahi mili! Code mein daal do ya secrets.toml mein add karo.")
        st.stop()

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# ======================= SIDEBAR =======================
with st.sidebar:
    st.header("Settings")
    days = st.slider("Last kitne din se videos dhundo?", 18, 7, 3)
    country = st.selectbox("Country", ["IN", "PK", "US", "GB", "BD", "AE", "CA", "GLOBAL"], index=0)
    min_views = st.number_input("Minimum Views", 5000, 1000000, 10000)
    min_vph = st.slider("Views Per Hour (viral ke liye)", 5000, 200000, 25000)
    st.markdown("---")
    st.success("Gemini se title + thumbnail analysis!")

# ======================= INPUT =======================
keyword_input = st.text_area(
    "Keywords daalo (comma ya new line se):",
    height=120,
    placeholder="carryminati roast, mrbeast challenge, dhruv rathee, technical guruji, reddit stories hindi"
).strip()  # ← Yahan hi strip kar diya

# Agar kuch nahi daala to stop
if not keyword_input:
    st.warning("Bhai keyword toh daal do pehle!")
    st.stop()

# Keywords ko list mein convert
keywords = [k.strip() for k in keyword_input.replace(",", "\n").split("\n") if k.strip()]

# ======================= MAIN FUNCTION =======================
@st.cache_data(ttl=1800, show_spinner=False)
def find_viral_videos(keywords, days_back, country_code, min_views, min_vph):
    url_search = "https://www.googleapis.com/youtube/v3/search"
    url_videos = "https://www.googleapis.com/youtube/v3/videos"
    
    published_after = (datetime.utcnow() - timedelta(days=days_back)).isoformat("T") + "Z"
    region = country_code if country_code != "GLOBAL" else None
    
    viral_list = []

    for keyword in keywords:
        st.write(f"Scanning: **{keyword}**")

        params = {
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "order": "date",
            "publishedAfter": published_after,
            "maxResults": 50,
            "regionCode": region,
            "key": YOUTUBE_API_KEY
        }

        try:
            res = requests.get(url_search, params=params, timeout=15)
            data = res.json()

            if not data.get("items"):
                continue

            video_ids = []
            temp_data = {}

            for item in data["items"]:
                vid = item["id"].get("videoId")
                if not vid: 
                    continue
                    
                pub_dt = datetime.fromisoformat(item["snippet"]["publishedAt"].replace("Z", "+00:00"))
                hours_old = (datetime.utcnow().replace(tzinfo=None) - pub_dt.replace(tzinfo=None)).total_seconds() / 3600
                if hours_old < 1: 
                    hours_old = 1

                video_ids.append(vid)
                temp_data[vid] = {
                    "title": item["snippet"]["title"],
                    "channel": item["snippet"]["channelTitle"],
                    "thumb": item["snippet"]["thumbnails"]["high"]["url"],
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "hours": hours_old
                }

            # Get stats
            stats_res = requests.get(url_videos, params={
                "part": "statistics",
                "id": ",".join(video_ids),
                "key": YOUTUBE_API_KEY
            }, timeout=15).json()

            for item in stats_res.get("items", []):
                vid = item["id"]
                stats = item["statistics"]
                views = int(stats.get("viewCount", 0))
                likes = int(stats.get("likeCount", 0))
                comments = int(stats.get("commentCount", 0))

                if views < min_views: 
                    continue
                vph = int(views / temp_data[vid]["hours"])
                if vph < min_vph: 
                    continue

                # Viral Score
                velocity_score = min(vph / 100000 * 50, 50)
                engagement = (likes + comments*3) / views * 100 if views > 0 else 0
                engage_score = min(engagement * 2, 30)
                freshness = max(20 - temp_data[vid]["hours"]/6, 0)
                score = velocity_score + engage_score + freshness

                viral_list.append({
                    **temp_data[vid],
                    "views": views,
                    "vph": vph,
                    "likes": likes,
                    "comments": comments,
                    "engagement": round(engagement, 2),
                    "score": round(score, 1)
                })

        except Exception as e:
            st.error(f"API Error: {e}")
            continue

    return sorted(viral_list, key=lambda x: x["score"], reverse=True)[:25]

# ======================= RUN =======================
if st.button("VIRAL VIDEOS DHUNDO", type="primary", use_container_width=True):
    with st.spinner("500+ videos scan kar raha hoon..."):
        results = find_viral_videos(keywords, days, country, min_views, min_vph)

    if not results:
        st.warning("Koi viral video nahi mila – keywords ya settings change karo")
    else:
        st.balloons()
        st.success(f"🎉 {len(results)} SUPER VIRAL videos mil gaye!")

        for v in results:
            score_color = "red" if v["score"] >= 85 else "orange" if v["score"] >= 70 else "green"
            c1, c2 = st.columns([1, 4])
            with c1:
                st.image(v["thumb"])
                st.markdown(f"<h2 style='color:{score_color}'>Score: {v['score']}</h2>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"### [{v['title']}]({v['url']})")
                st.write(f"**{v['channel']}** • {v['views']:,} views • {v['vph']:,}/hour • Engagement {v['engagement']}%")

                if st.button("Gemini se Analysis Karo", key=v['url']):
                    with st.spinner("Gemini AI soch raha hai..."):
                        try:
                            img = Image.open(requests.get(v["thumb"], stream=True).raw)
                            prompt = f"""
                            Title: {v['title']}
                            Views: {v['views']:,} | Views/hour: {v['vph']:,}
                            1. Yeh video kyun viral ho raha hai?
                            2. Best hook kya lagta hai?
                            3. Thumbnail kitne marks (1-10)?
                            4. Ek similar idea Hindi/Urdu mein suggest karo.
                            Short jawab do.
                            """
                            resp = model.generate_content([prompt, img])
                            st.markdown("### Gemini AI Ka Analysis")
                            st.write(resp.text)
                        except Exception as e:
                            st.write("Gemini busy hai ya error aaya, thodi der baad try karo")

            st.divider()

        # Download CSV
        df = pd.DataFrame(results)
        st.download_button("📥 Download All Results (CSV)", df.to_csv(index=False).encode(), "viral_videos_today.csv", "text/csv")

st.caption("Made with ❤️ by Desi Creators | 100% Free Tool")
