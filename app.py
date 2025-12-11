import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import re
from collections import defaultdict

# ------------------------------------------------------------
# APP CONFIG
# ------------------------------------------------------------
st.set_page_config(page_title="Faceless Viral Hunter PRO 2025", layout="wide")
st.title("🎯 Faceless Viral Videos Hunter PRO")
st.markdown("**Advanced AI-Powered Detection • Multi-Region Search • Smart Ranking**")

API_KEY = st.secrets["YOUTUBE_API_KEY"]

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

# ------------------------------------------------------------
# FACELESS INDICATORS (EXPANDED)
# ------------------------------------------------------------
FACELESS_KEYWORDS = [
    'reddit', 'aita', 'story time', 'text to speech', 'tts',
    'horror stories', 'true stories', 'scary stories',
    'cash cow', 'motivation', 'facts', 'top 10', 'top 5',
    'stoicism', 'philosophy', 'meditation', 'ambient',
    'lofi', 'study beats', 'relaxing', 'nature sounds',
    'minecraft parkour', 'subway surfers', 'satisfying',
    'oddly satisfying', 'compilation', 'caught on camera',
    'ai voice', 'ai narration', 'documentary', 'explained',
    'mystery', 'unsolved', 'creepypasta', 'nosleep'
]

FACELESS_TITLE_PATTERNS = [
    r'reddit',
    r'aita',
    r'am i the',
    r'story time',
    r'horror stor',
    r'true.*stor',
    r'scary.*stor',
    r'\(part \d+\)',
    r'#shorts',
    r'facts about',
    r'things you didn',
    r'you won.*t believe',
]

# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------
st.sidebar.header("⚙️ Advanced Settings")

days = st.sidebar.slider("📅 Published in Last N Days", 1, 90, 30)
min_views = st.sidebar.number_input("👁️ Minimum Views", 0, 1000000, 5000)
video_type = st.sidebar.selectbox("🎥 Video Type", ["All", "Long (5min+)", "Shorts"])

st.sidebar.markdown("---")
st.sidebar.subheader("Channel Filters")

# UPDATED: More flexible channel age
channel_age_months = st.sidebar.slider(
    "📆 Channel Created Within (Months)", 
    1, 36, 12,
    help="Newer channels have more growth potential"
)

min_subs = st.sidebar.number_input("📊 Min Subscribers", 0, 100000, 100)
max_subs = st.sidebar.number_input("📊 Max Subscribers", 0, 10000000, 500000)

faceless_strictness = st.sidebar.select_slider(
    "🎭 Faceless Detection",
    options=["Relaxed", "Moderate", "Strict", "Ultra Strict"],
    value="Moderate"
)

st.sidebar.markdown("---")
st.sidebar.subheader("Advanced Options")

min_engagement = st.sidebar.slider(
    "💬 Min Engagement Rate (%)", 
    0.0, 10.0, 1.0, 0.1,
    help="(Likes + Comments) / Views * 100"
)

search_regions = st.sidebar.multiselect(
    "🌍 Search Regions",
    ["US", "GB", "CA", "AU", "IN", "PK"],
    default=["US", "GB"]
)

max_results_per_keyword = st.sidebar.slider(
    "🔢 Max Results Per Keyword", 10, 50, 30
)

premium_only = st.sidebar.checkbox("💎 Premium Countries Only", value=False)

keyword_input = st.text_area(
    "🔑 Keywords (One Per Line)",
    height=250,
    value=(
        "reddit stories\n"
        "aita\n"
        "am i the asshole\n"
        "reddit cheating stories\n"
        "pro revenge\n"
        "malicious compliance\n"
        "entitled parents\n"
        "true horror stories\n"
        "mr nightmare\n"
        "scary stories animated\n"
        "3 scary stories\n"
        "stoic motivation\n"
        "sigma male\n"
        "minecraft parkour reddit\n"
        "subway surfers reddit stories"
    )
)

premium_countries = {
    'US','CA','GB','AU','NZ','DE','FR','IT','ES','NL','BE','AT','CH',
    'SE','NO','DK','FI','IE','LU','JP','KR','SG','AE'
}

# ------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------
def fetch_json(url, params):
    """Safe API call with error handling"""
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            if "quotaExceeded" in resp.text:
                return "QUOTA"
            return None
        return resp.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def parse_duration(duration):
    """Convert ISO 8601 duration to seconds"""
    matches = re.findall(r"(\d+)([HMS])", duration)
    return sum(int(v) * {"H": 3600, "M": 60, "S": 1}[u] for v, u in matches)


def advanced_faceless_detection(channel_data, strictness="Moderate"):
    """
    Advanced faceless detection using multiple signals
    Returns: (is_faceless: bool, confidence: float, reasons: list)
    """
    score = 0
    max_score = 10
    reasons = []
    
    snippet = channel_data.get("snippet", {})
    brand = channel_data.get("brandingSettings", {})
    
    # 1. Profile Picture Analysis
    profile_url = snippet.get("thumbnails", {}).get("default", {}).get("url", "")
    if "default.jpg" in profile_url or "s88-c-k-c0x00ffffff" in profile_url:
        score += 2
        reasons.append("Default profile picture")
    
    # 2. Banner Analysis
    banner = brand.get("image", {}).get("bannerExternalUrl", "")
    if not banner:
        score += 1
        reasons.append("No custom banner")
    
    # 3. Channel Description
    description = snippet.get("description", "").lower()
    faceless_count = sum(1 for kw in FACELESS_KEYWORDS if kw in description)
    if faceless_count >= 3:
        score += 3
        reasons.append(f"Faceless keywords in description ({faceless_count})")
    elif faceless_count >= 1:
        score += 1
        reasons.append(f"Some faceless keywords ({faceless_count})")
    
    # 4. Channel Title
    title = snippet.get("title", "").lower()
    title_matches = sum(1 for kw in FACELESS_KEYWORDS[:15] if kw in title)
    if title_matches >= 1:
        score += 2
        reasons.append("Faceless niche in channel name")
    
    # 5. No custom URL (newer channels)
    if "customUrl" not in snippet:
        score += 1
        reasons.append("No custom URL")
    
    confidence = (score / max_score) * 100
    
    # Determine if faceless based on strictness
    thresholds = {
        "Relaxed": 20,
        "Moderate": 40,
        "Strict": 60,
        "Ultra Strict": 80
    }
    
    is_faceless = confidence >= thresholds.get(strictness, 40)
    
    return is_faceless, confidence, reasons


def calculate_viral_score(video_stats, channel_stats, days_since_upload):
    """
    Calculate viral potential score (0-100)
    Higher score = better viral performance
    """
    views = video_stats.get("views", 0)
    likes = video_stats.get("likes", 0)
    comments = video_stats.get("comments", 0)
    subs = channel_stats.get("subs", 1)
    
    if views == 0:
        return 0
    
    # Views per day
    views_per_day = views / max(days_since_upload, 1)
    
    # Engagement rate
    engagement_rate = ((likes + comments) / views) * 100
    
    # Views to subs ratio (viral coefficient)
    viral_coefficient = views / max(subs, 1)
    
    # Normalized scores
    vpd_score = min(views_per_day / 1000, 10)  # Cap at 10
    eng_score = min(engagement_rate * 2, 10)    # Cap at 10
    viral_coef_score = min(viral_coefficient * 5, 10)  # Cap at 10
    
    # Weighted total
    total_score = (
        vpd_score * 0.4 +          # 40% weight
        eng_score * 0.3 +           # 30% weight
        viral_coef_score * 0.3      # 30% weight
    ) * 10
    
    return min(total_score, 100)


def search_videos_multi_region(keyword, regions, max_results, published_after):
    """Search across multiple regions and combine results"""
    all_items = []
    seen_ids = set()
    
    for region in regions:
        params = {
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "order": "viewCount",
            "publishedAfter": published_after,
            "maxResults": min(max_results, 50),
            "regionCode": region,
            "key": API_KEY,
            "relevanceLanguage": "en"
        }
        
        data = fetch_json(SEARCH_URL, params)
        
        if data == "QUOTA":
            return "QUOTA"
        if not data:
            continue
        
        for item in data.get("items", []):
            vid_id = item["id"]["videoId"]
            if vid_id not in seen_ids:
                seen_ids.add(vid_id)
                all_items.append(item)
        
        if len(all_items) >= max_results:
            break
    
    return all_items[:max_results]


# ------------------------------------------------------------
# MAIN SEARCH
# ------------------------------------------------------------
if st.button("🚀 FIND VIRAL VIDEOS", type="primary", use_container_width=True):
    
    if not keyword_input.strip():
        st.error("❌ Please enter at least one keyword!")
        st.stop()
    
    if not search_regions:
        st.error("❌ Please select at least one region!")
        st.stop()
    
    keywords = [kw.strip() for kw in keyword_input.strip().split("\n") if kw.strip()]
    
    all_results = []
    channel_cache = {}
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    published_after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    channel_created_after = datetime.utcnow() - timedelta(days=channel_age_months * 30)
    
    # ------------------------------------------------------------
    # SEARCH LOOP
    # ------------------------------------------------------------
    for idx, keyword in enumerate(keywords):
        
        status_text.markdown(f"### 🔍 Searching: **{keyword}** ({idx+1}/{len(keywords)})")
        
        # Multi-region search
        items = search_videos_multi_region(
            keyword, 
            search_regions, 
            max_results_per_keyword,
            published_after
        )
        
        if items == "QUOTA":
            st.error("⚠️ YouTube API Quota Exceeded! Try again tomorrow.")
            st.stop()
        
        if not items:
            st.warning(f"No results for: {keyword}")
            continue
        
        # Get video IDs and channel IDs
        video_ids = [i["id"]["videoId"] for i in items]
        channel_ids = list({i["snippet"]["channelId"] for i in items})
        
        # ------------------------------------------------------------
        # FETCH VIDEO STATS
        # ------------------------------------------------------------
        video_stats = {}
        
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]
            params = {
                "part": "statistics,contentDetails",
                "id": ",".join(batch),
                "key": API_KEY
            }
            
            data = fetch_json(VIDEOS_URL, params)
            if data == "QUOTA":
                st.error("⚠️ YouTube API Quota Exceeded!")
                st.stop()
            
            if data:
                for v in data.get("items", []):
                    dur = parse_duration(v["contentDetails"]["duration"])
                    stats = v["statistics"]
                    
                    video_stats[v["id"]] = {
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)),
                        "comments": int(stats.get("commentCount", 0)),
                        "duration": dur
                    }
        
        # ------------------------------------------------------------
        # FETCH CHANNEL STATS (Cached)
        # ------------------------------------------------------------
        new_channels = [cid for cid in channel_ids if cid not in channel_cache]
        
        if new_channels:
            for i in range(0, len(new_channels), 50):
                batch = new_channels[i:i+50]
                params = {
                    "part": "snippet,statistics,brandingSettings,contentDetails",
                    "id": ",".join(batch),
                    "key": API_KEY
                }
                
                data = fetch_json(CHANNELS_URL, params)
                if data == "QUOTA":
                    st.error("⚠️ YouTube API Quota Exceeded!")
                    st.stop()
                
                if data:
                    for ch in data.get("items", []):
                        is_faceless, confidence, reasons = advanced_faceless_detection(
                            ch, faceless_strictness
                        )
                        
                        channel_cache[ch["id"]] = {
                            "subs": int(ch["statistics"].get("subscriberCount", 0)),
                            "total_views": int(ch["statistics"].get("viewCount", 0)),
                            "video_count": int(ch["statistics"].get("videoCount", 0)),
                            "created": ch["snippet"]["publishedAt"],
                            "country": ch["snippet"].get("country", "N/A"),
                            "faceless": is_faceless,
                            "faceless_confidence": confidence,
                            "faceless_reasons": reasons,
                            "description": ch["snippet"].get("description", "")
                        }
        
        # ------------------------------------------------------------
        # FILTER AND SCORE VIDEOS
        # ------------------------------------------------------------
        for item in items:
            snippet = item["snippet"]
            vid_id = item["id"]["videoId"]
            ch_id = snippet["channelId"]
            
            vstats = video_stats.get(vid_id, {})
            chstats = channel_cache.get(ch_id, {})
            
            # Basic filters
            views = vstats.get("views", 0)
            if views < min_views:
                continue
            
            subs = chstats.get("subs", 0)
            if not (min_subs <= subs <= max_subs):
                continue
            
            # Channel age filter
            created_date = datetime.fromisoformat(chstats.get("created", "2000-01-01T00:00:00Z").replace("Z", ""))
            if created_date < channel_created_after:
                continue
            
            # Faceless filter
            if not chstats.get("faceless", False):
                continue
            
            # Premium country filter
            if premium_only and chstats.get("country") not in premium_countries:
                continue
            
            # Duration filter
            dur = vstats.get("duration", 0)
            vtype = "Shorts" if dur < 60 else "Long"
            
            if video_type == "Long (5min+)" and dur < 300:
                continue
            if video_type == "Shorts" and vtype != "Shorts":
                continue
            
            # Engagement rate filter
            likes = vstats.get("likes", 0)
            comments = vstats.get("comments", 0)
            engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0
            
            if engagement_rate < min_engagement:
                continue
            
            # Calculate days since upload
            upload_date = datetime.fromisoformat(snippet["publishedAt"].replace("Z", ""))
            days_since = (datetime.utcnow() - upload_date).days + 1
            
            # Calculate viral score
            viral_score = calculate_viral_score(vstats, chstats, days_since)
            
            # Add to results
            all_results.append({
                "Title": snippet["title"],
                "Channel": snippet["channelTitle"],
                "ChannelID": ch_id,
                "VideoID": vid_id,
                "Subs": subs,
                "Views": views,
                "Likes": likes,
                "Comments": comments,
                "EngagementRate": round(engagement_rate, 2),
                "ViewsPerDay": round(views / days_since, 0),
                "ViralScore": round(viral_score, 1),
                "Uploaded": snippet["publishedAt"][:10],
                "ChannelCreated": chstats.get("created", "")[:10],
                "ChannelAge(Days)": (datetime.utcnow() - created_date).days,
                "Country": chstats.get("country"),
                "Type": vtype,
                "Duration": f"{dur//60}:{dur%60:02d}",
                "FacelessConfidence": round(chstats.get("faceless_confidence", 0), 1),
                "FacelessReasons": ", ".join(chstats.get("faceless_reasons", [])),
                "Keyword": keyword,
                "Thumb": snippet["thumbnails"]["high"]["url"],
                "Link": f"https://www.youtube.com/watch?v={vid_id}",
                "ChannelLink": f"https://www.youtube.com/channel/{ch_id}"
            })
        
        progress_bar.progress((idx + 1) / len(keywords))
    
    progress_bar.empty()
    status_text.empty()
    
    # ------------------------------------------------------------
    # RESULTS DISPLAY
    # ------------------------------------------------------------
    if not all_results:
        st.warning("😔 No videos found matching your criteria. Try:")
        st.markdown("""
        - Reducing minimum views
        - Increasing channel age range
        - Relaxing faceless detection
        - Adding more keywords
        - Reducing engagement rate requirement
        """)
        st.stop()
    
    df = pd.DataFrame(all_results)
    
    # Remove duplicates (keep highest viral score)
    df = df.sort_values("ViralScore", ascending=False)
    df = df.drop_duplicates(subset="VideoID", keep="first")
    
    # Final sort by viral score
    df = df.sort_values("ViralScore", ascending=False).reset_index(drop=True)
    
    st.success(f"✅ Found **{len(df)}** High-Quality Faceless Viral Videos!")
    st.balloons()
    
    # ------------------------------------------------------------
    # STATISTICS
    # ------------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Videos", len(df))
    with col2:
        st.metric("Avg Viral Score", round(df["ViralScore"].mean(), 1))
    with col3:
        st.metric("Avg Views/Day", f"{int(df['ViewsPerDay'].mean()):,}")
    with col4:
        st.metric("Unique Channels", df["ChannelID"].nunique())
    
    st.markdown("---")
    
    # ------------------------------------------------------------
    # TOP VIDEOS DISPLAY
    # ------------------------------------------------------------
    st.subheader("🏆 Top Viral Videos")
    
    for idx, row in df.head(20).iterrows():
        with st.container():
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"### #{idx+1} • {row['Title']}")
                
                st.markdown(f"""
                **Channel:** [{row['Channel']}]({row['ChannelLink']}) • 
                **Subs:** {row['Subs']:,} • 
                **Country:** {row['Country']}
                """)
                
                st.markdown(f"""
                📊 **Stats:** {row['Views']:,} views • {row['Likes']:,} likes • 
                {row['Comments']:,} comments • {row['ViewsPerDay']:,} views/day
                """)
                
                st.markdown(f"""
                🎯 **Viral Score:** {row['ViralScore']}/100 • 
                **Engagement:** {row['EngagementRate']}% • 
                **Type:** {row['Type']} ({row['Duration']})
                """)
                
                st.markdown(f"""
                🎭 **Faceless Confidence:** {row['FacelessConfidence']}% 
                ({row['FacelessReasons']})
                """)
                
                st.markdown(f"""
                📅 **Uploaded:** {row['Uploaded']} • 
                **Channel Age:** {row['ChannelAge(Days)']} days • 
                **Keyword:** *{row['Keyword']}*
                """)
                
                st.markdown(f"[▶️ Watch Video]({row['Link']}) | [📺 Visit Channel]({row['ChannelLink']})")
            
            with col2:
                st.image(row['Thumb'], use_container_width=True)
            
            st.markdown("---")
    
    # ------------------------------------------------------------
    # DOWNLOAD OPTIONS
    # ------------------------------------------------------------
    st.subheader("📥 Download Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv = df.to_csv(index=False).encode()
        st.download_button(
            "📄 Download Full CSV",
            data=csv,
            file_name=f"faceless_viral_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Top 50 only
        top_csv = df.head(50).to_csv(index=False).encode()
        st.download_button(
            "🏆 Download Top 50 CSV",
            data=top_csv,
            file_name=f"top50_viral_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    # ------------------------------------------------------------
    # ANALYTICS
    # ------------------------------------------------------------
    with st.expander("📊 Advanced Analytics"):
        
        st.subheader("Top Performing Keywords")
        keyword_stats = df.groupby("Keyword").agg({
            "ViralScore": "mean",
            "Views": "sum",
            "VideoID": "count"
        }).round(1).sort_values("ViralScore", ascending=False)
        keyword_stats.columns = ["Avg Viral Score", "Total Views", "Video Count"]
        st.dataframe(keyword_stats, use_container_width=True)
        
        st.subheader("Top Countries")
        country_stats = df.groupby("Country").agg({
            "ViralScore": "mean",
            "ChannelID": "nunique",
            "Views": "sum"
        }).round(1).sort_values("ViralScore", ascending=False)
        country_stats.columns = ["Avg Viral Score", "Channels", "Total Views"]
        st.dataframe(country_stats, use_container_width=True)
        
        st.subheader("Video Type Distribution")
        type_stats = df.groupby("Type").agg({
            "VideoID": "count",
            "ViralScore": "mean",
            "ViewsPerDay": "mean"
        }).round(1)
        type_stats.columns = ["Count", "Avg Viral Score", "Avg Views/Day"]
        st.dataframe(type_stats, use_container_width=True)

st.caption("🚀 Upgraded by AI • Made for Muhammed Rizwan Qamar • Pro Edition 2025")
