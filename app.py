import streamlit as st
import requests
from datetime import datetime, timedelta, timezone
import time

# ====== API ======
API_KEY = st.secrets["YOUTUBE_API_KEY"]
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

st.set_page_config(page_title="YouTube Viral Finder", layout="wide")
st.title("YouTube Viral Videos Finder (Ab Pakka Chalega!)")
st.markdown("**Bilkul working version – no error, no chawal**")

# Inputs
col1, col2 = st.columns(2)
with col1:
    days = st.number_input("Kitne din pehle se videos dhundo (1-30)", 1, 30, 7)
with col2:
    country = st.selectbox("Country", 
        ["US", "IN", "GB", "PK", "BD", "CA", "AU", "AE", "BR", "ID", "MY", "EG", "DE", "FR"],
        index=1)

keyword_input = st.text_area("Keywords daal do (ek line mein ek ya comma se)", 
    height=150,
    placeholder="reddit stories\naita cheating\ntrue horror stories\nmrbeast\nopen marriage")

if st.button("Viral Videos Nikalo Abhi!", type="primary"):
    if not keyword_input.strip():
        st.error("Bhai keyword to daal do!")
        st.stop()

    keywords = [k.strip() for k in keyword_input.replace(",", "\n").split("\n") if k.strip()]
    if not keywords:
        st.stop()

    all_results = []
    progress = st.progress(0)

    # Correct date format
    published_after = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat("T") + "Z"

    for i, keyword in enumerate(keywords):
        st.write(f"**Searching:** `{keyword}` in **{country}**")
        
        search_params = {
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "order": "viewCount",
            "publishedAfter": published_after,
            "maxResults": 50,
            "regionCode": country,
            "key": API_KEY
        }

        try:
            response = requests.get(SEARCH_URL, params=search_params)
            data = response.json()

            if "error" in data:
                st.error(f"API Error: {data['error']['message']}")
                continue

            items = data.get("items", [])
            if not items:
                st.warning(f"`{keyword}` ke liye kuch nahi mila")
                continue

            video_ids = []
            channel_ids = set()
            videos_info = []

            for item in items:
                if item["id"]["kind"] == "youtube#video":
                    video_id = item["id"]["videoId"]
                    video_ids.append(video_id)
                    channel_ids.add(item["snippet"]["channelId"])
                    videos_info.append(item)

            # Get Video Stats
            video_stats = {}
            for j in range(0, len(video_ids), 50):
                batch = video_ids[j:j+50]
                stats_resp = requests.get(VIDEOS_URL, params={
                    "part": "statistics",
                    "id": ",".join(batch),
                    "key": API_KEY
                }).json()
                for item in stats_resp.get("items", []):
                    vid = item["id"]
                    stts = item["statistics"]
                    video_stats[vid] = {
                        "views": int(stts.get("viewCount", 0)),
                        "likes": int(stts.get("likeCount", 0)),
                        "comments": int(stts.get("commentCount", 0))
                    }

            # Get Channel Subscribers
            channel_stats = {}
            chan_list = list(channel_ids)
            for j in range(0, len(chan_list), 50):
                batch = chan_list[j:j+50]
                chan_resp = requests.get(CHANNELS_URL, params={
                    "part": "statistics",
                    "id": ",".join(batch),
                    "key": API_KEY
                }).json()
                for item in chan_resp.get("items", []):
                    channel_stats[item["id"]] = int(item["statistics"].get("subscriberCount", 0))

            # Save Results
            for info in videos_info:
                vid = info["id"]["videoId"]
                stats = video_stats.get(vid, {})
                views = stats.get("views", 0)
                if views < 1000:  # sirf 1000+ views wale
                    continue

                snippet = info["snippet"]
                all_results.append({
                    "Title": snippet["title"],
                    "Channel": snippet["channelTitle"],
                    "URL": f"https://www.youtube.com/watch?v={vid}",
                    "Thumbnail": snippet["thumbnails"]["high"]["url"],
                    "Published": snippet["publishedAt"][:10],
                    "Views": f"{views:,}",
                    "Likes": f"{stats.get('likes', 0):,}",
                    "Comments": f"{stats.get('comments', 0):,}",
                    "Subscribers": f"{channel_stats.get(snippet['channelId'], 0):,}",
                    "Keyword": keyword
                })

        except Exception as e:
            st.error(f"Error: {e}")

        progress.progress((i + 1) / len(keywords))
        time.sleep(0.3)  # API ko thodi saans

    # Final Display
    if all_results:
        # Remove duplicates
        seen = set()
        final_results = []
        for r in all_results:
            if r["URL"] not in seen:
                seen.add(r["URL"])
                final_results.append(r)

        # Sort by views
        final_results = sorted(final_results, key=lambda x: int(x["Views"].replace(",", "")), reverse=True)

        st.success(f"Total {len(final_results)} Viral Videos Mile!")

        for res in final_results[:100]:
            st.markdown(f"""
            **{res['Title']}**  
            **Channel:** {res['Channel']} | Subs: {res['Subscribers']}  
            **Views:** {res['Views']} | Likes {res['Likes']} | Comments {res['Comments']}  
            **Keyword:** `{res['Keyword']}`  
            [Watch Video]({res['URL']})
            """)
            st.image(res['Thumbnail'], width=320)
            st.markdown("---")
    else:
        st.warning("Koi video nahi mila bhai. Try karo: `reddit`, `aita`, `cheating stories`")

    progress.empty()
