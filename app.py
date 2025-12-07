```python
import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import io
import re
st.set_page_config(page_title="Faceless Viral Hunter 2025", layout="wide")
st.title("Faceless Viral Videos Only (10K+ Views • 2025-26 Channels)")
st.markdown("**Sirf Reddit Stories, AITA, Horror, Cash Cow, Motivation jaise FACELESS channels**")
API_KEY = st.secrets["YOUTUBE_API_KEY"]
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
# Sidebar
st.sidebar.header("Settings & Filters")
days = st.sidebar.slider("Days?", 1, 60, 7)
video_type = st.sidebar.selectbox("Video Type", ["All", "Long (5min+)", "Shorts"])
faceless_only = st.sidebar.checkbox("Only Faceless Channels", value=True)
search_in = st.sidebar.selectbox("Kahan Search Karein?", ["Keywords", "Titles", "Both (Keywords + Titles)"])
min_subs = st.sidebar.number_input("Min Subscribers", min_value=0, value=1000)
max_subs = st.sidebar.number_input("Max Subscribers", min_value=0, value=1000000000)
premium_only = st.sidebar.checkbox("Only Premium Countries", value=True)
keyword_input = st.text_area(
    "Keywords/Titles (Line by Line)",
    height=200,
    value="reddit stories\naita\nam i the asshole\ntrue horror stories\npro revenge\nmr nightmare\nreddit cheating\ncash cow\nstoicism",
    placeholder="Yahan keywords ya titles daalo..."
)
premium_countries = ['US', 'CA', 'GB', 'AU', 'NZ', 'DE', 'FR', 'IT', 'ES', 'NL', 'BE', 'AT', 'CH', 'SE', 'NO', 'DK', 'FI', 'IE', 'LU', 'JP', 'KR']
if st.button("Find FACELESS VIRAL VIDEOS", type="primary", use_container_width=True):
    if not keyword_input.strip():
        st.error("Keyword daal do bhai!")
        st.stop()
   
    keywords = [k.strip() for line in keyword_input.splitlines() for k in line.split(",") if k.strip()]
    all_results = []
    channel_info = {}
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
                    st.error("Change API or Wait 24 hrs")
                    continue
           
            items = response.json().get("items", [])
            if not items:
                st.info("Not Found")
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
            chan_list = [cid for cid in list(channel_ids) if cid not in channel_info]
            for i in range(0, len(chan_list), 50):
                batch = chan_list[i:i+50]
                resp = requests.get(CHANNELS_URL, params={
                    "part": "snippet,statistics,brandingSettings,contentDetails",
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
                    created_date = sn["publishedAt"]
                    country = sn.get("country", "N/A")
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
                        "created_date": created_date,
                        "country": country,
                        "is_faceless": is_faceless,
                        "uploads": c["contentDetails"]["relatedPlaylists"].get("uploads", None)
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
               
                # Title Search Filter
                if search_in == "Titles":
                    if keyword.lower() not in sn["title"].lower():
                        continue
                elif search_in == "Both (Keywords + Titles)":
                    if keyword.lower() not in sn["title"].lower():
                        continue
               
                if stats.get("views", 0) < 10000:
                    continue
                subs = ch.get("subs", 0)
                if not (min_subs <= subs <= max_subs):
                    continue
                if int(ch.get("created_year", "2000")) < 2025:
                    continue
                if faceless_only and not ch.get("is_faceless", False):
                    continue
                if premium_only and ch.get("country", "N/A") not in premium_countries:
                    continue
               
                dur_sec = stats.get("duration_seconds", 0)
                vtype = "Shorts" if dur_sec < 60 else "Long"
               
                if video_type == "Long (5min+)" and (vtype == "Shorts" or dur_sec < 300):
                    continue
                if video_type == "Shorts" and vtype != "Shorts":
                    continue
               
                upload = datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00")).strftime("%b %d, %Y")
                created_formatted = datetime.fromisoformat(ch.get("created_date", "2000-01-01T00:00:00Z").replace("Z", "+00:00")).strftime("%b %d, %Y")
               
                all_results.append({
                    "Title": sn["title"],
                    "Channel": sn["channelTitle"],
                    "ChannelID": ch_id,
                    "Subs": f"{subs:,}",
                    "Views": f"{stats.get('views',0):,}",
                    "Views_int": stats.get("views",0),
                    "Likes": stats.get("likes",0),
                    "Comments": stats.get("comments",0),
                    "Uploaded": upload,
                    "Created": created_formatted,
                    "Country": ch.get("country", "N/A"),
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
        df = pd.DataFrame(all_results)
        df = df.sort_values(by="Views_int", ascending=False)
        df = df.drop_duplicates(subset="ChannelID")
        
        st.success(f"{len(df)} FACELESS VIRAL VIDEOS mil gaye!")
        st.balloons()
       
        st.markdown("### Fetching channel video counts...")
        df["Shorts_Count"] = 0
        df["Long_Count"] = 0
        for index, row in df.iterrows():
            if quota_exceeded:
                break
            ch_id = row["ChannelID"]
            uploads = channel_info.get(ch_id, {}).get("uploads")
            if not uploads:
                df.at[index, "Shorts_Count"] = "N/A"
                df.at[index, "Long_Count"] = "N/A"
                continue
            video_ids = []
            page_token = ""
            while page_token is not None:
                params = {
                    "part": "snippet",
                    "playlistId": uploads,
                    "maxResults": 50,
                    "key": API_KEY,
                    "pageToken": page_token if page_token else ""
                }
                try:
                    resp = requests.get(PLAYLIST_ITEMS_URL, params=params)
                    if resp.status_code != 200:
                        error = resp.json().get("error", {})
                        if error.get("code") == 403 and "quotaExceeded" in error.get("message", ""):
                            st.error("Quota exceeded while fetching videos.")
                            quota_exceeded = True
                        break
                    data = resp.json()
                    video_ids.extend([item["snippet"]["resourceId"]["videoId"] for item in data.get("items", [])])
                    page_token = data.get("nextPageToken")
                except:
                    break
            shorts = 0
            longs = 0
            for i in range(0, len(video_ids), 50):
                if quota_exceeded:
                    break
                batch = video_ids[i:i+50]
                params = {
                    "part": "contentDetails",
                    "id": ",".join(batch),
                    "key": API_KEY
                }
                try:
                    resp = requests.get(VIDEOS_URL, params=params)
                    if resp.status_code != 200:
                        if "quotaExceeded" in resp.text:
                            quota_exceeded = True
                        continue
                    for v in resp.json().get("items", []):
                        dur = v["contentDetails"]["duration"]
                        dur_sec = sum(int(x or 0) * {"H":3600, "M":60, "S":1}.get(y, 0) for x,y in re.findall(r'(\d+)?([HMS])', dur))
                        if dur_sec < 60:
                            shorts += 1
                        else:
                            longs += 1
                except:
                    continue
            df.at[index, "Shorts_Count"] = shorts
            df.at[index, "Long_Count"] = longs
       
        for _, r in df.iterrows():
            st.markdown("---")
            col1, col2 = st.columns([3,1])
            with col1:
                st.markdown(f"**{r['Title']}**")
                st.markdown(f"**{r['Channel']}** • {r['Subs']} subs • Created: {r['Created']} • Country: {r['Country']} • Shorts: {r['Shorts_Count']} • Long: {r['Long_Count']} • Faceless: **{r['Faceless']}**")
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
st.caption("Made with ❤️ for Muhammed Rizwan Qamar | 2025 Edition")
```
