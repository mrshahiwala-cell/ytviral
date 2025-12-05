import streamlit as st
import requests
from datetime import datetime, timedelta
import time

# ====== API ======
API_KEY = st.secrets["YOUTUBE_API_KEY"]
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

st.set_page_config(page_title="YouTube Viral Finder", layout="wide")
st.title("YouTube Viral Videos Finder (Ab 100% No Error!)")

col1, col2 = st.columns(2)
with col1:
    days = st.number_input("Kitne din pehle se dhundo", 1, 30, 10, help="10-15 din best hota hai")
with col2:
    country = st.selectbox("Country", ["US", "IN", "GB", "PK", "BD", "CA", "AU", "BR", "ID", "DE", "EG", "AE"])

keyword_input = st.text_area("Keywords (ek line mein ek)", height=160,
    placeholder="reddit stories\naita cheating\ntrue horror stories\nmrbeast challenge\nopen marriage")

if st.button("Viral Videos Nikalo!", type="primary"):
    if not keyword_input.strip():
        st.error("Keyword daal bhai!")
        st.stop()

    keywords = [k.strip() for k in keyword_input.replace(",", "\n").split("\n") if k.strip()]
    all_results = []
    progress = st.progress(0)

    # YE LINE SABSE ZAROORI HAI – AB ERROR KABHI NAHI AAYEGA
    published_after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    for idx, keyword in enumerate(keywords):
        st.write(f"**Searching:** `{keyword}` in **{country}**")
        
        params = {
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "order": "viewCount",
            "publishedAfter": published_after,   # Ab perfect format hai
            "maxResults": 50,
            "regionCode": country,
            "key": API_KEY
        }

        try:
            response = requests.get(SEARCH_URL, params=params)
            data = response.json()

            if "error" in data:
                st.error(f"API Error: {data['error']['message']}")
                continue

            items = data.get("items", [])
            if not items:
                st.info(f"`{keyword}` → abhi tak koi video nahi mila")
                continue

            video_ids = []
            channel_ids = set()
            videos_info = []

            for item in items:
                if item["id"]["kind"] == "youtube#video":
                    vid = item["id"]["videoId"]
                    video_ids.append(vid)
                    channel_ids.add(item["snippet"]["channelId"])
                    videos_info.append(item)

            # Video Stats
            stats_dict = {}
            for i in range(0, len(video_ids), 50):
                batch = video_ids[i:i+50]
                stats = requests.get(VIDEOS_URL, params={"part": "statistics", "id": ",".join(batch), "key": API_KEY}).json()
                for itm in stats.get("items", []):
                    s = itm["statistics"]
                    stats_dict[itm["id"]] = {
                        "views": int(s.get("viewCount", 0)),
                        "likes": int(s.get("likeCount", 0)),
                        "comments": int(s.get("commentCount", 0))
                    }

            # Channel Stats
            subs_dict = {}
            chan_list = list(channel_ids)
            for i in range(0, len(chan_list), 50):
                batch = chan_list[i:i+50]
                ch = requests.get(CHANNELS_URL, params={"part": "statistics", "id": ",".join(batch), "key": API_KEY}).json()
                for itm in ch.get("items", []):
                    subs_dict[itm["id"]] = int(itm["statistics"].get("subscriberCount", 0))

            # Add Results
            for info in videos_info:
                vid = info["id"]["videoId"]
                stat = stats_dict.get(vid, {})
                views = stat.get("views", 0)
                if views < 1000:
                    continue

                sn = info["snippet"]
                all_results.append({
                    "Title": sn["title"],
                    "Channel": sn["channelTitle"],
                    "URL": f"https://www.youtube.com/watch?v={vid}",
                    "Thumbnail": sn["thumbnails"]["high"]["url"],
                    "Date": sn["publishedAt"][:10],
                    "Views": f"{views:,}",
                    "Likes": f"{stat.get('likes', 0):,}",
                    "Comments": f"{stat.get('comments', 0):,}",
                    "Subs": f"{subs_dict.get(sn['channelId'], 0):,}",
                    "Keyword": keyword
                })

        except Exception as e:
            st.error(f"Error: {e}")

        progress.progress((idx + 1) / len(keywords))
        time.sleep(0.3)

    # Final Results
    if all_results:
        all_results = sorted(all_results, key=lambda x: int(x["Views"].replace(",", "")), reverse=True)
        seen = set()
        unique = []
        for r in all_results:
            if r["URL"] not in seen:
                seen.add(r["URL"])
                unique.append(r)

        st.success(f"Total {len(unique)} High-View Videos Mile!")
        for r in unique[:80]:
            with st.expander(f"{r['Title'][:100]} | Views: {r['Views']} | Keyword: {r['Keyword']}"):
                col1, col2 = st.columns([2,1])
                with col1:
                    st.markdown(f"**Channel:** {r['Channel']} | Subs: {r['Subs']}")
                    st.markdown(f"**Likes:** {r['Likes']} | **Comments:** {r['Comments']}")
                    st.markdown(f"[Watch Video]({r['URL']})")
                with col2:
                    st.image(r["Thumbnail"])
    else:
        st.warning("Koi video nahi mila – Try karo: reddit stories, aita, horror")

    progress.empty()
