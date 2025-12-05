# app.py
import streamlit as st
import requests
from datetime import datetime, timedelta, timezone
import pandas as pd

st.set_page_config(page_title="YouTube Viral Finder", layout="wide")
st.title("YouTube Viral Content Finder 2025")

# API Key
API_KEY = st.secrets["YOUTUBE_API_KEY"]

# URLs
SEARCH_URL   = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL   = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

# Sidebar
with st.sidebar:
    days = st.slider("Search last X days", 1, 7, 3)
    country = st.selectbox("Country", ["GLOBAL","IN","PK","US","GB","CA","AE","BD","AU"])
    min_vph = st.slider("Minimum Views/Hour (viral filter)", 5000, 100000, 15000)

# Input
keyword_input = st.text_area("Keywords (one per line or comma)", height=130).strip()
if not keyword_input:
    st.stop()

keywords = [k.strip() for k in keyword_input.replace(",","\n").split("\n") if k.strip()]

@st.cache_data(ttl=1800)
def get_viral_videos(keywords, days_back, region):
    published_after = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat(timespec='seconds') + "Z"
    region_code = None if region == "GLOBAL" else region

    results = []

    for kw in keywords:
        st.write(f"Searching → **{kw}**")

        params = {
            "part": "snippet",
            "q": kw,
            "type": "video",
            "order": "date",
            "publishedAfter": published_after,
            "maxResults": 40,
            "regionCode": region_code,
            "key": API_KEY
        }

        try:
            r = requests.get(SEARCH_URL, params=params, timeout=15)
            data = r.json()

            if not data.get("items"):
                continue

            video_ids = []
            info = {}

            for item in data["items"]:
                vid = item["id"].get("videoId")
                if not vid: continue

                pub = item["snippet"]["publishedAt"]
                published_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                hours_old = max(1, (datetime.now(timezone.utc) - published_dt).total_seconds() / 3600)

                video_ids.append(vid)
                info[vid] = {
                    "title": item["snippet"]["title"],
                    "channel": item["snippet"]["channelTitle"],
                    "thumb": item["snippet"]["thumbnails"]["high"]["url"],
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "published": pub,
                    "hours_old": hours_old
                }

            # Get stats in one call
            stats_r = requests.get(VIDEOS_URL, params={
                "part": "statistics",
                "id": ",".join(video_ids),
                "key": API_KEY
            }, timeout=15).json()

            for item in stats_r.get("items", []):
                vid = item["id"]
                s = item["statistics"]
                views = int(s.get("viewCount", 0))
                likes = int(s.get("likeCount", 0))
                comments = int(s.get("commentCount", 0))

                hours = info[vid]["hours_old"]
                vph = int(int)(views / hours)

                if vph < min_vph:
                    continue

                engagement = (likes + comments*3) / views * 100 if views > 0 else 0
                score = min(vph/80000*55,55) + min(engagement*2,30,30) + max(15-hours/10,0)

                results.append({
                    "Title": info[vid]["title"],
                    "Channel": info[vid]["channel"],
                    "Views": views,
                    "VPH": vph,
                    "Engagement %": round(engagement,2),
                    "Age hrs": round(hours,1),
                    "Score": round(score,1),
                    "URL": info[vid]["url"],
                    "Thumb": info[vid]["thumb"]
                })

        except Exception as e:
            st.error(f"Error: {e}")
            continue

    return sorted(results, key=lambda x: x["Score"], reverse=True)[:25]

# Run
if st.button("FIND VIRAL VIDEOS NOW", type="primary", use_container_width=True):
    with st.spinner("Scanning latest videos…"):
        viral_list = get_viral_videos(keywords, days, country)

    if not viral_list:
        st.info("No fast-growing videos found — try different keywords")
    else:
        st.success(f"Found {len(viral_list)} exploding videos")
        for v in viral_list:
            score_color = "red" if v["Score"] >= 80 else "orange" if v["Score"] >= 65 else "green"
            c1, c2 = st.columns([1,5])
            with c1:
                st.image(v["Thumb"])
                st.markdown(f"<h3 style='color:{score_color};text-align:center'>{v['Score']}</h3>", unsafe_allow_html=True)
            with c2:
                st.subheader(v["Title"])
                st.write(f"**{v['Channel']}** • {v['Views']:,} views • **{v['VPH']:,}/hr** • {v['Engagement %']}%")
                st.markdown(f"[Watch Video]({v['URL']})")
            st.divider()

        # CSV download
        df = pd.DataFrame(viral_list)
        st.download_button("Download Results (CSV)", df.to_csv(index=False).encode(), "viral_today.csv", "text/csv")
