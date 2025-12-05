import streamlit as st
import requests
from datetime import datetime, timedelta
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
video_type = st.selectbox("Video Type", ["All", "Long (>60 sec)", "Shorts (≤60 sec)"])
if st.button("Viral Videos Dhundo Abhi!", type="primary"):
    if not keyword_input.strip():
        st.error("Keyword daal bhai!")
        st.stop()
    keywords = [k.strip() for k in keyword_input.replace(",", "\n").split("\n") if k.strip()]
    results = []
    progress = st.progress(0)
   
    # Correct date format (abhi kabhi error nahi aayega)
    published_after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    def parse_duration(dur):
        if not dur:
            return 0
        dur = dur.replace("PT", "")
        hours = 0
        mins = 0
        secs = 0
        if 'H' in dur:
            parts = dur.split('H')
            hours = int(parts[0])
            dur = parts[1]
        if 'M' in dur:
            parts = dur.split('M')
            mins = int(parts[0])
            dur = parts[1]
        if 'S' in dur:
            secs = int(dur.split('S')[0])
        return hours * 3600 + mins * 60 + secs
    
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
            # Video Stats + Duration
            stats_dict = {}
            for i in range(0, len(video_ids), 50):
                batch = video_ids[i:i+50]
                stats = requests.get(VIDEOS_URL, params={"part": "statistics,contentDetails", "id": ",".join(batch), "key": API_KEY}).json()
                for v in stats.get("items", []):
                    s = v["statistics"]
                    stats_dict[v["id"]] = {
                        "views": int(s.get("viewCount", 0)),
                        "likes": int(s.get("likeCount", 0)),
                        "comments": int(s.get("commentCount", 0)),
                        "duration": v["contentDetails"].get("duration", "PT0S")
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
            # Final Filter & Display
            for info in video_data:
                vid = info["id"]["videoId"]
                sn = info["snippet"]
                ch_id = sn["channelId"]
               
                views = stats_dict.get(vid, {}).get("views", 0)
                likes = stats_dict.get(vid, {}).get("likes", 0)
                comments = stats_dict.get(vid, {}).get("comments", 0)
                duration = stats_dict.get(vid, {}).get("duration", "PT0S")
                duration_secs = parse_duration(duration)
                subs = channel_info.get(ch_id, {}).get("subs", 0)
                created_year = channel_info.get(ch_id, {}).get("created_year", "2000")
                # TERE TARGET WALE FILTERS
                if views < 10000: # 10K+ views
                    continue
                if subs < 1000: # 1K+ subs
                    continue
                if int(created_year) < 2024: # Sirf 2024 ya 2025 ke channels
                    continue
                # Video Type Filter
                if video_type == "Shorts (≤60 sec)" and duration_secs > 60:
                    continue
                if video_type == "Long (>60 sec)" and duration_secs <= 60:
                    continue
                # Upload Time
                upload_time = datetime.strptime(sn["publishedAt"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H:%M UTC")
                # FULL OPEN DISPLAY – NO EXPANDER
                st.markdown("---")
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{sn['title']}**")
                    st.markdown(f"**Channel:** {sn['channelTitle']} | Subs: **{subs:,}** | Created: **{created_year}**")
                    st.markdown(f"**Views:** {views:,} | ❤️ {likes:,} | 💬 {comments:,}")
                    st.markdown(f"**Uploaded:** {upload_time}")
                    st.markdown(f"**Keyword:** `{keyword}`")
                    st.markdown(f"[Watch Video](https://www.youtube.com/watch?v={vid})")
                with col2:
                    st.image(sn["thumbnails"]["high"]["url"], use_column_width=True)
               
                results.append(vid)
        except Exception as e:
            st.error(f"Error: {e}")
        progress.progress((idx + 1) / len(keywords))
    total = len(results)
    if total > 0:
        st.success(f"Total {total} REAL VIRAL VIDEOS mili jo abhi chal rahi hain!")
        st.balloons()
    else:
        st.warning("Koi perfect match nahi mila – filters thodi tight hain. 'reddit stories' try karo")
    progress.empty()
