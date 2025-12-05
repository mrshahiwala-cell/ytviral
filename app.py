import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd

# === CONFIG ===
API_KEY = st.secrets["YOUTUBE_API_KEY"]
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

st.set_page_config(page_title="YouTube Viral Finder Pro", layout="wide")
st.title("🔥 YouTube Viral Content Finder Pro (10000% Accurate)")
st.markdown("**Finds actually exploding videos in any country • Real-time viral potential detector**")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    days = st.slider("Lookback Period (Days)", 1, 30, 7)
    min_views = st.number_input("Minimum Views", 500, 1000000, 5000)
    min_engagement_rate = st.slider("Min Engagement Rate (%)", 1.0, 20.0, 4.0)
    
    country_names = {
        "US": "United States", "GB": "United Kingdom", "IN": "India", "PK": "Pakistan",
        "BD": "Bangladesh", "CA": "Canada", "AU": "Australia", "AE": "UAE", 
        "MY": "Malaysia", "SG": "Singapore", "DE": "Germany", "FR": "France",
        "BR": "Brazil", "MX": "Mexico", "ID": "Indonesia", "EG": "Egypt"
    }
    country_code = st.selectbox("Select Country", options=list(country_names.keys()), 
                               format_func=lambda x: f"{x} - {country_names[x]}")

# Input
keyword_input = st.text_area(
    "Enter Keywords (one per line or comma separated)",
    height=150,
    placeholder="e.g.\nreddit stories\ncheating revenge\naita\nopen marriage\nmrbeast challenge"
)

if st.button("🚀 Find Viral Videos Now", type="primary"):
    if not keyword_input.strip():
        st.error("Please enter at least one keyword!")
        st.stop()

    keywords = [k.strip() for k in keyword_input.replace(",", "\n").split("\n") if k.strip()]
    all_videos = []
    start_time = datetime.utcnow() - timedelta(days=days)
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, keyword in enumerate(keywords):
        status_text.text(f"Searching: {keyword} in {country_names[country_code]}...")
        
        # === 1. Keyword Search (Recent + Relevant) ===
        search_params = {
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "order": "viewCount",
            "publishedAfter": (start_time).isoformat("T") + "Z",
            "maxResults": 15,
            "regionCode": country_code,
            "relevanceLanguage": country_code.lower(),
            "key": API_KEY
        }
        
        # === 2. Also Get Trending in That Country (Most Important!) ===
        trending_params = {
            "part": "snippet",
            "chart": "mostPopular",
            "regionCode": country_code,
            "maxResults": 25,
            "key": API_KEY
        }

        try:
            # Get keyword results
            search_resp = requests.get(SEARCH_URL, params=search_params).json()
            trending_resp = requests.get(VIDEOS_URL, params=trending_params).json()

            video_ids = []
            items_to_process = []

            # From keyword search
            if "items" in search_resp:
                for item in search_resp["items"]:
                    if "videoId" in item["id"]:
                        video_ids.append(item["id"]["videoId"])
                        items_to_process.append(item)

            # From trending (filter by keyword match in title/description)
            if "items" in trending_resp:
                for item in trending_resp["items"]:
                    title = item["snippet"]["title"].lower()
                    desc = item["snippet"]["description"].lower()
                    if any(k.lower() in title or k.lower() in desc for k in keywords):
                        vid = item["id"]
                        if vid not in video_ids:
                            video_ids.append(vid)
                            items_to_process.append(item)

            if not video_ids:
                continue

            # === Fetch Stats ===
            stats_resp = requests.get(VIDEOS_URL, params={
                "part": "statistics,contentDetails",
                "id": ",".join(video_ids),
                "key": API_KEY
            }).json()

            channel_ids = list(set([item["snippet"]["channelId"] for item in items_to_process if "channelId" in item["snippet"]]))
            channel_resp = requests.get(CHANNELS_URL, params={
                "part": "statistics,snippet",
                "id": ",".join(channel_ids),
                "key": API_KEY
            }).json()

            channel_dict = {c["id"]: c for c in channel_resp.get("items", [])}
            stats_dict = {s["id"]: s for s in stats_resp.get("items", [])}

            for item in items_to_process:
                vid = item["id"]["videoId"] if isinstance(item["id"], dict) else item["id"]
                snippet = item["snippet"]
                stats = stats_dict.get(vid, {})
                channel = channel_dict.get(snippet["channelId"], {})

                views = int(stats.get("statistics", {}).get("viewCount", 0))
                if views < min_views:
                    continue

                likes = int(stats.get("statistics", {}).get("likeCount", 0))
                comments = int(stats.get("statistics", {}).get("commentCount", 0))
                duration = stats.get("contentDetails", {}).get("duration", "")
                
                published_at = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
                hours_old = (datetime.utcnow().replace(tzinfo=None) - published_at.replace(tzinfo=None)).total_seconds() / 3600
                if hours_old == 0:
                    hours_old = 1

                # === VIRAL SCORE CALCULATION ===
                views_per_hour = views / hours_old
                engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0
                viral_score = (views_per_hour * 0.6) + (engagement_rate * 20) + (views / 1000)

                if engagement_rate < min_engagement_rate:
                    continue

                all_videos.append({
                    "Title": snippet["title"],
                    "Channel": snippet["channelTitle"],
                    "URL": f"https://www.youtube.com/watch?v={vid}",
                    "Thumbnail": snippet["thumbnails"]["high"]["url"],
                    "Published": published_at.strftime("%b %d, %Y"),
                    "Age (Hours)": round(hours_old, 1),
                    "Views": f"{views:,}",
                    "Views/Hour": f"{int(views_per_hour):,}",
                    "Likes": f"{likes:,}",
                    "Comments": f"{comments:,}",
                    "Engagement %": f"{engagement_rate:.2f}%",
                    "Viral Score": round(viral_score, 2),
                    "Subscribers": f"{int(channel.get('statistics', {}).get('subscriberCount', 0)):,}",
                    "Duration": duration.replace("PT", "").replace("M", "m ").replace("S", "s") if duration else "N/A"
                })

        except Exception as e:
            st.error(f"Error with keyword '{keyword}': {str(e)}")

        progress_bar.progress((idx + 1) / len(keywords))

    # === DISPLAY RESULTS ===
    if all_videos:
        df = pd.DataFrame(all_videos)
        df = df.drop_duplicates(subset=["URL"])
        df = df.sort_values("Viral Score", ascending=False).reset_index(drop=True)

        st.success(f"🚀 Found {len(df)} VIRAL POTENTIAL Videos in {country_names[country_code]}!")

        # Top badges
        top1 = df.iloc[0]
        st.markdown(f"### 🏆 **MOST VIRAL RIGHT NOW** → [{top1['Title']}]({top1['URL']})")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Views/Hour", top1["Views/Hour"])
        with col2:
            st.metric("Engagement", top1["Engagement %"])
        with col3:
            st.metric("Viral Score", top1["Viral Score"])
        with col4:
            st.image(top1["Thumbnail"], width=200)

        st.markdown("---")
        st.markdown("### 📊 All High-Potential Videos (Sorted by Viral Score)")

        for _, row in df.iterrows():
            score_color = "🟢" if row["Viral Score"] > 5000 else "🟡" if row["Viral Score"] > 2000 else "🔴"
            exp_col = st.expander(f"{score_color} {row['Title'][:80]}...")
            
            with exp_col:
                c1, c2 = st.columns([3, 2])
                with c1:
                    st.markdown(f"**Channel:** {row['Channel']} | 👤 Subs: {row['Subscribers']}")
                    st.markdown(f"**Link:** [Watch Now]({row['URL']})")
                    st.markdown(f"**Published:** {row['Published']} ({row['Age (Hours)']} hrs ago)")
                with c2:
                    st.image(row["Thumbnail"], use_column_width=True)

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Views", row["Views"])
                m2.metric("Views/Hour", row["Views/Hour"])
                m3.metric("Engagement", row["Engagement %"])
                m4.metric("🔥 Viral Score", row["Viral Score"])

                if row["Viral Score"] > 8000:
                    st.markdown("**🚨 EXTREME VIRAL POTENTIAL - MAKE THIS NOW! 🚨**")

    else:
        st.warning("No viral videos found with current filters. Try lowering min views or increasing days.")

    status_text.empty()
    progress_bar.empty()
