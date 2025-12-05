import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import io
import re

st.set_page_config(page_title="Viral Hunter 2025", layout="wide")
st.title("Real Viral Videos Only (10K+ Views • 1K+ Subs • New Channels)")
API_KEY = st.secrets["YOUTUBE_API_KEY"]
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

# Input
days = st.slider("Last Kitne Din Se Dhundo?", 1, 90, 15)
keyword_input = st.text_area("Keywords (ek line mein ek)", height=160,
    placeholder="reddit stories\naita cheating\ntrue horror stories\nmrbeast\nrevenge stories\nopen marriage")
video_type = st.selectbox("Video Type Filter", ["All", "Long", "Shorts"])

if st.button("Viral Videos Dhundo Abhi!", type="primary"):
    if not keyword_input.strip():
        st.error("Keyword daal bhai!")
        st.stop()
    keywords = [k.strip() for k in keyword_input.replace(",", "\n").split("\n") if k.strip()]
    all_results = []
    progress = st.progress(0)
   
    # Correct date format (ab kabhi error nahi aayega)
    published_after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for idx, keyword in enumerate(keywords):
        st.markdown(f"### Searching: **{keyword}**")
       
        params = {
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "order": "viewCount",
            "publishedAfter": published_after,
            "maxResults": 50,
            "key": API_KEY
        }
        try:
            res = requests.get(SEARCH_URL, params=params).json()
            items = res.get("items", [])
            if not items:
                st.write("→ Koi video nahi mili is keyword pe")
                continue
            video_ids = []
            channel_ids = set()
            video_data = []
            for item in items:
                if item["id"]["kind"] == "youtube#video":
                    vid = item["id"]["videoId"]
                    video_ids.append(vid)
                    channel_ids.add(item["snippet"]["channelId"])
                    video_data.append(item)
            # Video Stats and Duration
            stats_dict = {}
            for i in range(0, len(video_ids), 50):
                batch = video_ids[i:i+50]
                stats = requests.get(VIDEOS_URL, params={"part": "statistics,contentDetails", "id": ",".join(batch), "key": API_KEY}).json()
                for v in stats.get("items", []):
                    s = v["statistics"]
                    duration = v["contentDetails"]["duration"]
                    # Parse duration using regex
                    time_dict = {"H": 3600, "M": 60, "S": 1}
                    dur_seconds = sum(int(num) * time_dict[unit] for num, unit in re.findall(r'(\d+)([HMS])', duration))
                    stats_dict[v["id"]] = {
                        "views": int(s.get("viewCount", 0)),
                        "likes": int(s.get("likeCount", 0)),
                        "comments": int(s.get("commentCount", 0)),
                        "duration_seconds": dur_seconds
                    }
            # Channel Stats + Creation Date
            channel_info = {}
            chan_list = list(channel_ids)
            for i in range(0, len(chan_list), 50):
                batch = chan_list[i:i+50]
                ch = requests.get(CHANNELS_URL, params={"part": "statistics,snippet", "id": ",".join(batch), "key": API_KEY}).json()
                for c in ch.get("items", []):
                    created = c["snippet"]["publishedAt"][:4] # Year only
                    subs = int(c["statistics"].get("subscriberCount", 0))
                    channel_info[c["id"]] = {
                        "subs": subs,
                        "created_year": created
                    }
            # Collect Data
            for info in video_data:
                vid = info["id"]["videoId"]
                sn = info["snippet"]
                ch_id = sn["channelId"]
               
                views = stats_dict.get(vid, {}).get("views", 0)
                likes = stats_dict.get(vid, {}).get("likes", 0)
                comments = stats_dict.get(vid, {}).get("comments", 0)
                duration_seconds = stats_dict.get(vid, {}).get("duration_seconds", 0)
                subs = channel_info.get(ch_id, {}).get("subs", 0)
                created_year = channel_info.get(ch_id, {}).get("created_year", "2000")
                upload_time = sn["publishedAt"]
                upload_dt = datetime.fromisoformat(upload_time.replace("Z", "+00:00"))
                upload_str = upload_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                # TERE TARGET WALE FILTERS
                if views < 10000: # 10K+ views
                    continue
                if subs < 1000: # 1K+ subs
                    continue
                if int(created_year) < 2024: # Sirf 2024 ya 2025 ke channels
                    continue
                # Classify type
                video_category = "Shorts" if duration_seconds < 60 else "Long"
                all_results.append({
                    "title": sn['title'],
                    "channel": sn['channelTitle'],
                    "subs": subs,
                    "created_year": created_year,
                    "views": views,
                    "likes": likes,
                    "comments": comments,
                    "upload_time": upload_str,
                    "keyword": keyword,
                    "link": f"https://www.youtube.com/watch?v={vid}",
                    "thumbnail": sn["thumbnails"]["high"]["url"],
                    "type": video_category
                })
        except Exception as e:
            st.error(f"Error: {e}")
        progress.progress((idx + 1) / len(keywords))
    progress.empty()
    
    # Filter based on video_type
    if video_type != "All":
        all_results = [r for r in all_results if r["type"] == video_type]
    
    # Display Results
    if all_results:
        st.success(f"Total {len(all_results)} REAL VIRAL VIDEOS mili jo abhi chal rahi hain!")
        st.balloons()
        for result in all_results:
            st.markdown("---")
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{result['title']}**")
                st.markdown(f"**Channel:** {result['channel']} | Subs: **{result['subs']:,}** | Created: **{result['created_year']}**")
                st.markdown(f"**Views:** {result['views']:,} | ❤️ {result['likes']:,} | 💬 {result['comments']:,}")
                st.markdown(f"**Upload Time:** {result['upload_time']}")
                st.markdown(f"**Type:** {result['type']}")
                st.markdown(f"**Keyword:** `{result['keyword']}`")
                st.markdown(f"[Watch Video]({result['link']})")
            with col2:
                st.image(result['thumbnail'], use_column_width=True)
        
        # Downloadable CSV
        df = pd.DataFrame(all_results)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="Download Stats CSV",
            data=csv_buffer.getvalue(),
            file_name="viral_videos_stats.csv",
            mime="text/csv"
        )
    else:
        st.warning("Koi perfect match nahi mila – filters thodi tight hain. 'reddit stories' try karo")
