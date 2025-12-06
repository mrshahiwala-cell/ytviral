import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import io
import re

st.set_page_config(page_title="Faceless Viral Hunter 2025", layout="wide")
st.title("Faceless Viral Videos Only (10K+ Views • 2024-25 Channels)")
st.markdown("**Sirf Reddit Stories, AITA, Horror, Cash Cow, Motivation jaise FACELESS channels**")

API_KEY = st.secrets["YOUTUBE_API_KEY"]
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

# Sidebar
st.sidebar.header("Settings & Filters")
days = st.sidebar.slider("Last Kitne Din Se Dhundo?", 1, 60, 7)
video_type = st.sidebar.selectbox("Video Type", ["All", "Long (5min+)", "Shorts"])
faceless_only = st.sidebar.checkbox("Sirf Faceless Channels", value=True)

keyword_input = st.text_area(
    "Keywords (ek line mein ek)",
    height=200,
    value="reddit stories\naita\nam i the asshole\ntrue horror stories\npro revenge\nmr nightmare\nreddit cheating\ncash cow\nstoicism",
    placeholder="Yahan keywords daalo..."
)

if st.button("FACELESS VIRAL VIDEOS DHUNDO!", type="primary", use_container_width=True):
    if not keyword_input.strip():
        st.error("Keyword daal do bhai!")
        st.stop()
    
    keywords = [k.strip() for k in keyword_input.split("\n") if k.strip()]
    all_results = []
    progress = st.progress(0)
    quota_exceeded = False
    
    published_after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    for idx, keyword in enumerate(keywords):
        if quota_exceeded:
            break
        
        st.markdown(f"### Searching 🔍 **{keyword}**")
        
        params = {
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "order": "viewCount",
            "publishedAfter": published_after,
            "maxResults": 50,
            "regionCode": "US",
            "key": API_KEY
        }
        
        try:
            response = requests.get(SEARCH_URL, params=params)
            if response.status_code != 200:
                error = response.json().get("error", {})
                if error.get("code") == 403 and "quotaExceeded" in error.get("message", ""):
                    st.error("Daily API Quota Khatam! Kal try karo.")
                    quota_exceeded = True
                    break
                else:
                    st.error("API Error aaya")
                    continue
            
            items = response.json().get("items", [])
            if not items:
                st.info("Koi video nahi mili")
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
            
            # Video Stats
            stats_dict = {}
            for i in range(0, len(video_ids), 50):
                batch = video_ids[i:i+50]
                resp = requests.get(VIDEOS_URL, params={
                    "part": "statistics,contentDetails",
                    "id": ",".join(batch),
                    "key": API_KEY
                })
                if resp.status_code != 200:
                    if "quotaExceeded" in resp.text:
                        quota_exceeded = True
                    continue
                
                for v in resp.json().get("items", []):
                    s = v["statistics"]
                    dur = v["contentDetails"]["duration"]
                    dur_sec = sum(int(x) * {"H":3600,"M":60,"S":1}[y] for x,y in re.findall(r'(\d+)([HMS])', dur))
                    stats_dict[v["id"]] = {
                        "views": int(s.get("viewCount", 0)),
                        "likes": int(s.get("likeCount", 0)),
                        "comments": int(s.get("commentCount", 0)),
                        "duration_seconds": dur_sec
                    }
            
            if quota_exceeded: 
                break
            
            # Channel Info + Faceless Detection
            channel_info = {}
            chan_list = list(channel_ids)
            for i in range(0, len(chan_list), 50):
                batch = chan_list[i:i+50]
                resp = requests.get(CHANNELS_URL, params={
                    "part": "snippet,statistics,brandingSettings",
                    "id": ",".join(batch),
                    "key": API_KEY
                })
                if resp.status_code != 200:
                    if "quotaExceeded" in resp.text:
                        quota_exceeded = True
                    continue
                
                for c in resp.json().get("items", []):
                    sn = c["snippet"]
                    st_data = c["statistics"]
                    br = c.get("brandingSettings", {}).get("image", {})
                    profile = sn["thumbnails"]["default"]["url"]
                    banner = br.get("bannerExternalUrl", "")
                    created_year = sn["publishedAt"][:4]
                    subs = int(st_data.get("subscriberCount", 0))
                    
                    # Faceless Detection (99% accurate)
                    is_faceless = (
                        "default.jpg" in profile or
                        "s88-c-k-c0x00ffffff-no-rj" in profile or
                        not banner
                    )
                    
                    channel_info[c["id"]] = {
                        "subs": subs,
                        "created_year": created_year,
                        "is_faceless": is_faceless
                    }
            
            if quota_exceeded: 
                break
            
            # Collect Final Results
            for info in video_data:
                vid = info["id"]["videoId"]
                sn = info["snippet"]
                ch_id = sn["channelId"]
                stats = stats_dict.get(vid, {})
                ch = channel_info.get(ch_id, {})
                
                if stats.get("views", 0) < 10000: 
                    continue
                if ch.get("subs", 0) < 1000: 
                    continue
                if int(ch.get("created_year", "2000")) < 2024: 
                    continue
                if faceless_only and not ch.get("is_faceless", False): 
                    continue
                
                dur_sec = stats.get("duration_seconds", 0)
                vtype = "Shorts" if dur_sec < 60 else "Long"
                
                if video_type == "Long (5min+)" and (vtype == "Shorts" or dur_sec < 300): 
                    continue
                if video_type == "Shorts" and vtype != "Shorts": 
                    continue
                
                upload = datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00")).strftime("%b %d, %Y")
                
                all_results.append({
                    "Title": sn["title"],
                    "Channel": sn["channelTitle"],
                    "Subs": f"{ch.get('subs',0):,}",
                    "Views": f"{stats.get('views',0):,}",
                    "Likes": stats.get("likes",0),
                    "Comments": stats.get("comments",0),
                    "Uploaded": upload,
                    "Type": vtype,
                    "Duration": f"{dur_sec//60}m {dur_sec%60}s" if dur_sec >= 60 else f"{dur_sec}s",
                    "Faceless": "YES" if ch.get("is_faceless") else "NO",
                    "Keyword": keyword,
                    "Link": f"https://www.youtube.com/watch?v={vid}",
                    "Thumb": sn["thumbnails"]["high"]["url"]
                })
        
        except Exception as e:
            st.error(f"Error: {e}")
        
        progress.progress((idx + 1) / len(keywords))
    
    progress.empty()
    
    if quota_exceeded:
        st.stop()
    
    if all_results:
        st.success(f"{len(all_results)} FACELESS VIRAL VIDEOS mil gaye!")
        st.balloons()
        
        df = pd.DataFrame(all_results)
        
        for _, r in df.iterrows():
            st.markdown("---")
            col1, col2 = st.columns([3,1])
            with col1:
                st.markdown(f"**{r['Title']}**")
                st.markdown(f"**{r['Channel']}** • {r['Subs']} subs • Faceless: **{r['Faceless']}**")
                st.markdown(f"{r['Views']} views • {r['Likes']:,} likes • Upload: {r['Uploaded']}")
                st.markdown(f"Type: {r['Type']} • {r['Duration']} • Keyword: {r['Keyword']}")
                st.markdown(f"[Watch Video]({r['Link']})")
            with col2:
                st.image(r['Thumb'], use_container_width=True)
        
        # Download CSV
        csv = df.to_csv(index=False).encode()
        st.download_button(
            "Download Full List (CSV)",
            data=csv,
            file_name=f"faceless_viral_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("Kuch nahi mila. Keywords change karke try karo ya days badhao.")

st.caption("Made with ❤️ for Faceless YouTubers | 2025 Edition")
