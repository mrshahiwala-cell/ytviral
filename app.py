import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import io
import re

st.set_page_config(page_title="Faceless Viral Hunter 2025", layout="wide")
st.title("Faceless Viral Videos Only (10K+ Views • New Channels • 2024-25)")
st.markdown("**Sirf wo channels jo face nahi dikhate → Reddit Stories, AITA, Horror, Motivation, Cash Cow style**")

API_KEY = st.secrets["YOUTUBE_API_KEY"]
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

# Sidebar Filters
st.sidebar.header("Filters")
days = st.sidebar.slider("Last Kitne Din Se Dhundo?", 1, 60, 7)
video_type = st.sidebar.selectbox("Video Type", ["All", "Long (5min+)", "Shorts"])
faceless_only = st.sidebar.checkbox("Sirf Faceless Channels Dhundo", value=True)

keyword_input = st.text_area(
    "Keywords (har line mein ek keyword)",
    height=200,
    placeholder="reddit stories\naita\nam i the asshole\ntrue horror stories\npro revenge\nmr nightmare\nreddit cheating\ncash cow channel\nstoicism\ntop 10 creepy"
)

if st.button("FACELESS VIRAL VIDEOS DHUNDO ABHI!", type="primary", use_container_width=True):
    if not keyword_input.strip():
        st.error("Bhai keyword to daal do pehle!")
        st.stop()

    keywords = [k.strip() for k in keyword_input.split("\n") if k.strip()]
    all_results = []
    progress = st.progress(0)
    quota_exceeded = False

    published_after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    for idx, keyword in enumerate(keywords):
        if quota_exceeded:
            break

        st.markdown(f"### Searching → **{keyword}**")

        params = {
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "order": "viewCount",
            "publishedAfter": published_after,
            "maxResults": 50,
            "regionCode": "US",
            "relevanceLanguage": "en",
            "key": API_KEY
        }

        try:
            response = requests.get(SEARCH_URL, params=params)
            if response.status_code := response.status_code != 200:
                error = response.json().get("error", {})
                if error.get("code") == 403 and "quotaExceeded" in error.get("message", ""):
                    st.error("API Quota Khatam! Kal try karna ya new key daal do.")
                    quota_exceeded = True
                    break
                else:
                    st.error(f"API Error: {response.text}")
                    continue

            items = response.json().get("items", [])
            if not items:
                st.info("→ Is keyword pe koi video nahi mili")
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

            # ====== VIDEO STATS (Views, Duration) ======
            stats_dict = {}
            for i in range(0, len(video_ids), 50):
                batch = video_ids[i:i+50]
                resp = requests.get(VIDEOS_URL, params={
                    "part": "statistics,statistics,contentDetails",
                    "id": ",".join(batch),
                    "key": API_KEY
                })
                if resp.status_code != 200:
                    if "quotaExceeded" in resp.text:
                        st.error("Quota over bhai!")
                        quota_exceeded = True
                    continue

                for v in resp.json().get("items", []):
                    stats = v["statistics"]
                    duration = v["contentDetails"]["duration"]
                    dur_sec = sum(int(x) * {"H": 3600, "M": 60, "S": 1}[y]
                                  for x, y in re.findall(r"(\d+)([HMS])", duration))

                    stats_dict[v["id"]] = {
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)),
                        "comments": int(stats.get("commentCount", 0)),
                        "duration_seconds": dur_sec
                    }

            if quota_exceeded:
                break

            # ====== CHANNEL STATS + FACELESS DETECTION ======
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
                    st = c["statistics"]
                    br = c.get("brandingSettings", {})
                    img = br.get("image", {})

                    profile_url = sn["thumbnails"]["default"]["url"]
                    banner_url = img.get("bannerExternalUrl", "")

                    created_year = sn["publishedAt"][:4]
                    subs = int(st.get("subscriberCount", 0))

                    # FACELESS DETECTION (bohot accurate)
                    is_faceless = False
                    if ("default.jpg" in profile_url or
                        "s88-c-k-c0x00ffffff-no-rj" in profile_url or
                        not banner_url or
                        "yt3.ggpht.com" in banner_url and banner_url.endswith("=s0")):
                        is_faceless = True

                    channel_info[c["id"]] = {
                        "subs": subs,
                        "created_year": created_year,
                        "is_faceless": is_faceless,
                        "channel_name": sn["title"]
                    }

            if quota_exceeded:
                break

            # ====== FINAL FILTERING & COLLECT RESULTS ======
            for info in video_data:
                vid = info["id"]["videoId"]
                sn = info["snippet"]
                ch_id = sn["channelId"]

                stats = stats_dict.get(vid, {})
                ch = channel_info.get(ch_id, {})

                views = stats.get("views", 0)
                duration_sec = stats.get("duration_seconds", 0)
                subs = ch.get("subs", 0)
                created_year = ch.get("created_year", "2000")
                is_faceless = ch.get("is_faceless", False)

                # Main Filters
                if views < 10000:        # 10K+ views
                    continue
                if subs < 1000:          # 1K+ subs
                    continue
                if int(created_year) < 2024:  # Only 2024-2025 channels
                    continue
                if faceless_only and not is_faceless:  # Faceless only
                    continue

                # Video type filter
                video_cat = "Shorts" if duration_sec < 60 else "Long"
                if video_type == "Long (5min+)" and (video_cat == "Shorts" or duration_sec < 300):
                    continue
                if video_type == "Shorts" and video_cat != "Shorts":
                    continue

                upload_time = datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00")) \
                    .strftime("%b %d, %Y %H:%M UTC")

                all_results.append({
                    "Title": sn["title"],
                    "Channel": sn["channelTitle"],
                    "Subscribers": f"{subs:,}",
                    "Views": f"{views:,}",
                    "Likes": stats.get("likes", 0),
                    "Comments": stats.get("comments", 0),
                    "Uploaded": upload_time,
                    "Type": video_cat,
                    "Duration": f"{duration_sec//60}m {duration_sec%60}s" if duration_sec >= 60 else f"{duration_sec}s",
                    "Faceless": "Yes" if is_faceless else "No",
                    "Keyword": keyword,
                    "Link": f"https://www.youtube.com/watch?v={vid}",
                    "Thumbnail": sn["thumbnails"]["high"]["url"]
                })

        except Exception as e:
            st.error(f"Error: {e}")

        progress.progress((idx + 1) / len(keywords))

    # ====== RESULTS DISPLAY ======
    progress.empty()

    if quota_exceeded:
        st.stop()

    if all_results:
        st.success(f"Total {len(all_results)} FACELESS VIRAL VIDEOS mil gaye!")
        st.balloons()

        df = pd.DataFrame(all_results)
        
        # Beautiful cards
        for _, row in df.iterrows():
            st.markdown("---")
            c1, c2 = st.columns([3,1])
            with c1:
                st.markdown(f"### {row['Title']}")
                st.markdown(f"**{row['Channel']}** • {row['Subscribers']} subs • Created {row.get('created_year', '2024+')}")
                st.markdown(f"**{row['Views']} views** • {row['Likes']:,} likes • {row['Comments']:,} comments")
                st.markdown(f"**{row['Uploaded']}** • {row['Type']} • {row['Duration']}")
                st.markdown(f"**Keyword:** `{row['Keyword']}` • Faceless: **{row['Faceless']}**")
                st.markdown(f"[Watch on YouTube]({row['Link']})")
            ")
            with c2:
                st.image(row['Thumbnail'], use_column_width=True)

        # Download Button
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download All as CSV",
            data=csv,
            file_name=f"faceless_viral_videos_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("Kuch nahi mila bhai Try these keywords:\n\n`reddit stories`\n`aita`\n`true scary stories`\n`pro revenge`\n`mr nightmare`")
