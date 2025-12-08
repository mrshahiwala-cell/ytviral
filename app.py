import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import re


# ------------------------------------------------------------
# APP CONFIG
# ------------------------------------------------------------
st.set_page_config(page_title="Faceless Viral Hunter 2025", layout="wide")
st.title("Faceless Viral Videos Only (10K+ Views • 2025-26 Channels)")
st.markdown("**Sirf Reddit Stories, AITA, Horror, Cash Cow, Motivation jaise FACELESS channels**")

API_KEY = st.secrets["YOUTUBE_API_KEY"]

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"


# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------
st.sidebar.header("Settings & Filters")
days = st.sidebar.slider("Days?", 1, 60, 7)
video_type = st.sidebar.selectbox("Video Type", ["All", "Long (5min+)", "Shorts"])
faceless_only = st.sidebar.checkbox("Only Faceless Channels", value=True)
search_in = st.sidebar.selectbox("Search In?", ["Keywords", "Titles", "Both"])
min_subs = st.sidebar.number_input("Min Subscribers", min_value=0, value=1000)
max_subs = st.sidebar.number_input("Max Subscribers", min_value=0, value=1000000000)
premium_only = st.sidebar.checkbox("Only Premium Countries", value=True)

keyword_input = st.text_area(
    "Keywords/Titles (Line by Line)",
    height=200,
    value=(
        "reddit stories\naita\nam i the asshole\ntrue horror stories\n"
        "pro revenge\nmr nightmare\nreddit cheating\ncash cow\nstoicism"
    )
)

premium_countries = {
    'US','CA','GB','AU','NZ','DE','FR','IT','ES','NL','BE','AT','CH',
    'SE','NO','DK','FI','IE','LU','JP','KR'
}


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
def fetch_json(url, params):
    """Safe wrapper for requests.get"""
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        if "quotaExceeded" in resp.text:
            return "QUOTA"
        return None
    return resp.json()


def parse_duration(duration):
    """Convert ISO 8601 duration to seconds"""
    return sum(int(v) * {"H": 3600, "M": 60, "S": 1}[u]
               for v, u in re.findall(r"(\d+)([HMS])", duration))


def detect_faceless(profile_url, banner_url):
    """Simple faceless detection"""
    return (
        "default.jpg" in profile_url
        or "s88-c-k-c0x00ffffff-no-rj" in profile_url
        or not banner_url
    )


# ------------------------------------------------------------
# MAIN ACTION
# ------------------------------------------------------------
if st.button("Find FACELESS VIRAL VIDEOS", type="primary", use_container_width=True):

    if not keyword_input.strip():
        st.error("Keyword daal do bhai!")
        st.stop()

    keywords = [kw.strip() for line in keyword_input.splitlines()
                for kw in line.split(",") if kw.strip()]

    all_results = []
    channel_cache = {}
    progress = st.progress(0)

    published_after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # LOOP THROUGH KEYWORDS
    for idx, kw in enumerate(keywords):

        st.markdown(f"### Searching 🔍 **{kw}**")

        search_params = {
            "part": "snippet",
            "q": kw,
            "type": "video",
            "order": "viewCount",
            "publishedAfter": published_after,
            "maxResults": 50,
            "regionCode": "US",
            "key": API_KEY
        }

        data = fetch_json(SEARCH_URL, search_params)
        if data == "QUOTA":
            st.error("Daily API Quota Khatam! Kal try karo.")
            st.stop()
        if not data:
            st.error("API Error – wait or change key")
            continue

        items = data.get("items", [])
        if not items:
            st.info("Koi video nahi mila is keyword ke liye")
            continue

        # Extract IDs
        video_ids = [i["id"]["videoId"] for i in items]
        channel_ids = {i["snippet"]["channelId"] for i in items}

        # ------------------------------------------------------------
        # VIDEO DETAILS
        # ------------------------------------------------------------
        video_stats = {}
        params = {
            "part": "statistics,contentDetails",
            "id": ",".join(video_ids),
            "key": API_KEY
        }
        vid_data = fetch_json(VIDEOS_URL, params)
        if vid_data == "QUOTA":
            st.error("Daily API Quota Khatam! Kal try karo.")
            st.stop()

        for v in vid_data.get("items", []):
            dur_sec = parse_duration(v["contentDetails"]["duration"])
            s = v["statistics"]

            video_stats[v["id"]] = {
                "views": int(s.get("viewCount", 0)),
                "likes": int(s.get("likeCount", 0)),
                "comments": int(s.get("commentCount", 0)),
                "duration": dur_sec
            }

        # ------------------------------------------------------------
        # CHANNEL DETAILS (cache)
        # ------------------------------------------------------------
        new_channels = [cid for cid in channel_ids if cid not in channel_cache]

        if new_channels:
            params = {
                "part": "snippet,statistics,brandingSettings,contentDetails",
                "id": ",".join(new_channels),
                "key": API_KEY
            }
            ch_data = fetch_json(CHANNELS_URL, params)

            if ch_data == "QUOTA":
                st.error("Daily API Quota Khatam! Kal try karo.")
                st.stop()

            for c in ch_data.get("items", []):
                sn = c["snippet"]
                stats = c["statistics"]
                brand_img = c.get("brandingSettings", {}).get("image", {})
                profile = sn["thumbnails"]["default"]["url"]
                banner = brand_img.get("bannerExternalUrl", "")

                channel_cache[c["id"]] = {
                    "subs": int(stats.get("subscriberCount", 0)),
                    "created": sn["publishedAt"],
                    "country": sn.get("country", "N/A"),
                    "faceless": detect_faceless(profile, banner)
                }

        # ------------------------------------------------------------
        # FILTER VIDEOS
        # ------------------------------------------------------------
        for item in items:
            sn = item["snippet"]
            vid = item["id"]["videoId"]
            cid = sn["channelId"]
            stats = video_stats.get(vid, {})
            ch = channel_cache.get(cid, {})

            # Title/Keyword filter
            if search_in != "Keywords":
                if kw.lower() not in sn["title"].lower():
                    continue

            # Video stats filters
            if stats.get("views", 0) < 10000:
                continue

            subs = ch.get("subs", 0)
            if not (min_subs <= subs <= max_subs):
                continue

            # New channels only (2025+)
            created_year = int(ch.get("created", "2000")[:4])
            if created_year < 2025:
                continue

            # Faceless filter
            if faceless_only and not ch.get("faceless"):
                continue

            # Country filter
            if premium_only and ch.get("country") not in premium_countries:
                continue

            # Short/Long filter
            dur = stats.get("duration", 0)
            vtype = "Shorts" if dur < 60 else "Long"

            if video_type == "Long (5min+)" and (dur < 300):
                continue
            if video_type == "Shorts" and vtype != "Shorts":
                continue

            # Add result
            all_results.append({
                "Title": sn["title"],
                "Channel": sn["channelTitle"],
                "ChannelID": cid,
                "Subs": subs,
                "Views": stats.get("views"),
                "Likes": stats.get("likes"),
                "Comments": stats.get("comments"),
                "Uploaded": sn["publishedAt"],
                "Created": ch.get("created"),
                "Country": ch.get("country"),
                "Type": vtype,
                "Duration": dur,
                "Faceless": "YES" if ch.get("faceless") else "NO",
                "Keyword": kw,
                "Thumb": sn["thumbnails"]["high"]["url"],
                "Link": f"https://www.youtube.com/watch?v={vid}"
            })

        progress.progress((idx + 1) / len(keywords))

    progress.empty()

    # ------------------------------------------------------------
    # RESULTS
    # ------------------------------------------------------------
    if not all_results:
        st.warning("Kuch nahi mila. Keywords change karo ya days badhao.")
        st.stop()

    df = pd.DataFrame(all_results)
    df = df.sort_values(by="Views", ascending=False)
    df = df.drop_duplicates(subset="ChannelID")

    st.success(f"{len(df)} FACELESS VIRAL VIDEOS mil gaye! 🎉")
    st.balloons()

    # DISPLAY RESULTS
    for _, r in df.iterrows():
        st.markdown("---")
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**{r['Title']}**")
            st.markdown(
                f"**{r['Channel']}** • {r['Subs']:,} subs • Country: {r['Country']} • "
                f"Faceless: **{r['Faceless']}**"
            )
            st.markdown(
                f"{r['Views']:,} views • Type: {r['Type']} • Duration: {r['Duration']}s"
            )
            st.markdown(f"[Watch Video]({r['Link']})")

        with col2:
            st.image(r["Thumb"], use_container_width=True)

    # CSV DOWNLOAD
    csv = df.to_csv(index=False).encode()
    st.download_button(
        "📥 Download Full List (CSV)",
        data=csv,
        file_name=f"faceless_viral_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )

st.caption("Made with ❤️ for Muhammed Rizwan Qamar | Clean 2025 Edition")
