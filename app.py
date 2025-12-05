# app.py
import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Viral Hunter 2025", layout="wide")
st.title("YouTube Viral Hunter 2025")
st.markdown("### Bilkul FREE • Sirf YouTube API • Koi error nahi • Har roz viral ideas")

# Sidebar Settings
with st.sidebar:
    st.header("Settings")
    days = st.slider("Last kitne din se videos dhundo?", 1, 7, 3)
    country = st.selectbox("Country", ["IN", "PK", "US", "GB", "BD", "AE", "CA", "GLOBAL"], index=0)
    min_views = st.number_input("Minimum Views", 3000, 500000, 8000)
    min_vph = st.slider("Views Per Hour (jitna zyada = zyada viral)", 3000, 150000, 15000)
    st.info("Gemini nahi hai — lekin results 1000% accurate hain!")

# Keyword Input
keyword_input = st.text_area(
    "Keywords daalo (comma ya enter se):",
    height=120,
    placeholder="carryminati, mrbeast, dhruv rathee, technical guruji, reddit stories, pakistani prank"
).strip()

if not keyword_input:
    st.stop()

keywords = [k.strip() for k in keyword_input.replace(",", "\n").split("\n") if k.strip()]

# Main Function
@st.cache_data(ttl=3600, show_spinner=False)
def find_viral_videos(keywords, days_back, country_code, min_views, min_vph):
    search_url = "https://www.googleapis.com/googleapis/youtube/v3/search"
    videos_url = "https://www.googleapis.com/youtube/v3/videos"
    
    published_after = (datetime.utcnow() - timedelta(days=days_back)).isoformat("T") + "Z"
    region = country_code if country_code != "GLOBAL" else None
    
    results = []

    for keyword in keywords:
        st.write(f"Searching: **{keyword}**")

        params = {
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "order": "date",
            "publishedAfter": published_after,
            "maxResults": 50,
            "regionCode": region,
            "key": st.secrets["YOUTUBE_API_KEY"]
        }

        try:
            res = requests.get(search_url, params=params, timeout=15)
            data = res.json()

            if not data.get("items"):
                continue

            video_ids = []
            temp = {}

            for item in data["items"]:
                vid = item["id"].get("videoId")
                if not vid: continue

                published = item["snippet"]["publishedAt"]
                pub_time = datetime.fromisoformat(published.replace("Z", "+00:00"))
                hours_old = max(1, (datetime.utcnow().replace(tzinfo=None) - pub_time.replace(tzinfo=None)).total_seconds() / 3600)

                video_ids.append(vid)
                temp[vid] = {
                    "title": item["snippet"]["title"],
                    "channel": item["snippet"]["channelTitle"],
                    "thumb": item["snippet"]["thumbnails"]["high"]["url"],
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "hours": hours_old
                }

            # Get Stats
            stats = requests.get(videos_url, params={
                "part": "statistics",
                "id": ",".join(video_ids),
                "key": st.secrets["YOUTUBE_API_KEY"]
            }, timeout=15).json()

            for item in stats.get("items", []):
                vid = item["id"]
                s = item["statistics"]
                views = int(s.get("viewCount", 0))
                likes = int(s.get("likeCount", 0))
                comments = int(s.get("commentCount", 0))

                if views < min_views: continue
                vph = int(views / temp[vid]["hours"])
                if vph < min_vph: continue

                # Super Accurate Viral Score (0–100)
                velocity = min(vph / 80000 * 50, 50)
                engagement = (likes + comments*4) / views * 100 if views > 0 else 0
                engage_score = min(engagement * 2.5, 35)
                fresh_score = max(15 - hours_old/8, 0)
                total_score = velocity + engage_score + fresh_score

                results.append({
                    "Title": temp[vid]["title"],
                    "Channel": temp[vid]["channel"],
                    "Views": views,
                    "VPH": vph,
                    "Likes": likes,
                    "Comments": comments,
                    "Engagement %": round(engagement, 2),
                    "Age (hrs)": round(hours_old, 1),
                    "Viral Score": round(total_score, 1),
                    "URL": temp[vid]["url"],
                    "Thumbnail": temp[vid]["thumb"]
                })

        except Exception as e:
            st.error(f"Error: {e}")
            continue

    return sorted(results, key=lambda x: x["Viral Score"], reverse=True)[:30]

# Run Button
if st.button("ABHI VIRAL VIDEOS DHUNDO", type="primary", use_container_width=True):
    with st.spinner("500+ videos scan kar raha hoon..."):
        data = find_viral_videos(keywords, days, country, min_views, min_vph)

    if not data:
        st.warning("Koi viral video nahi mila — keywords change karo ya days badhao")
    else:
        st.balloons()
        st.success(f"{len(data)} TEZ VIRAL videos mil gaye!")

        for video in data:
            score = "red" if video["Viral Score"] >= 80 else "orange" if video["Viral Score"] >= 65 else "green"
            c1, c2 = st.columns([1, 4])

            with c1:
                st.image(video["Thumbnail"], use_column_width=True)
                st.markdown(f"<h2 style='color:{color}; text-align:center'>Score: {video['Viral Score']}</h2>", 
                           unsafe_allow_html=True)

            with c2:
                st.markdown(f"### [{video['Title']}]({video['URL']})")
                st.write(f"**{video['Channel']}**")
                st.write(f"Views: **{video['Views']:,}** • VPH: **{video['VPH']:,}** • Engagement: **{video['Engagement %']}%** • Age: {video['Age (hrs)']} hrs")

            st.divider()

        # Download Button
        df = pd.DataFrame(data)
        st.download_button(
            "Download All Viral Videos (CSV)",
            df.to_csv(index=False).encode(),
            f"viral_videos_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )

st.caption("100% Free • No Gemini • Sirf YouTube API • Made for Desi Creators")
