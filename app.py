import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import re
from collections import defaultdict

# ------------------------------------------------------------
# APP CONFIG
# ------------------------------------------------------------
st.set_page_config(page_title="🎯 Faceless Viral Hunter", layout="wide")

# Initialize session state
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
if 'trigger_search' not in st.session_state:
    st.session_state.trigger_search = False
if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'quota_used' not in st.session_state:
    st.session_state.quota_used = 0

API_KEY = st.secrets["YOUTUBE_API_KEY"]

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

MAX_RESULTS = 5  # Only 5 results for quota saving

# Premium CPM Countries (High paying)
PREMIUM_COUNTRIES = ['US', 'CA', 'GB', 'AU', 'DE', 'FR', 'NL', 'CH', 'NO', 'SE', 'DK', 'AT', 'BE', 'NZ', 'IE']

# All monetizable countries
MONETIZATION_COUNTRIES = {
    'US', 'CA', 'GB', 'AU', 'NZ', 'DE', 'FR', 'IT', 'ES', 'NL', 'BE', 'AT', 'CH',
    'SE', 'NO', 'DK', 'FI', 'IE', 'LU', 'JP', 'KR', 'SG', 'HK', 'IN', 'BR', 'MX'
}

CPM_RATES = {
    'US': 4.0, 'CA': 3.5, 'GB': 3.5, 'AU': 4.0, 'NZ': 3.0,
    'DE': 3.5, 'FR': 2.5, 'IT': 2.0, 'ES': 2.0, 'NL': 3.0,
    'CH': 4.5, 'NO': 4.0, 'SE': 3.0, 'DK': 3.0, 'AT': 3.0,
    'BE': 2.5, 'IE': 3.0, 'JP': 2.5, 'N/A': 1.0
}

FACELESS_INDICATORS = [
    "stories", "reddit", "aita", "horror", "scary", "creepy",
    "nightmare", "revenge", "confession", "askreddit", "tifu",
    "motivation", "stoic", "stoicism", "wisdom", "quotes",
    "facts", "explained", "documentary", "mystery", "unsolved",
    "true crime", "compilation", "top 10", "top 5", "ranking",
    "ai voice", "text to speech", "tts", "faceless", "voice over"
]


# ------------------------------------------------------------
# QUOTA TRACKING
# ------------------------------------------------------------
def add_quota(units):
    st.session_state.quota_used += units


# ------------------------------------------------------------
# HTML REPORT GENERATOR
# ------------------------------------------------------------
def generate_html_report(df, search_query):
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Faceless Hunter Report - {search_query}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e4e4e4;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            text-align: center;
            padding: 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            margin-bottom: 25px;
        }}
        .header h1 {{ font-size: 2rem; margin-bottom: 10px; }}
        .search-info {{ background: rgba(0,0,0,0.2); padding: 10px 20px; border-radius: 20px; display: inline-block; margin-top: 10px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .summary-card {{ background: rgba(255,255,255,0.05); padding: 20px; border-radius: 12px; text-align: center; }}
        .summary-card .num {{ font-size: 1.8rem; font-weight: 700; color: #667eea; }}
        .summary-card .label {{ font-size: 0.85rem; color: #888; margin-top: 5px; }}
        .card {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .card-header {{ display: flex; gap: 15px; margin-bottom: 15px; }}
        .thumb {{ width: 180px; height: 100px; border-radius: 8px; object-fit: cover; }}
        .card-content {{ flex: 1; }}
        .card-title {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 8px; color: #fff; }}
        .card-title a {{ color: #fff; text-decoration: none; }}
        .channel {{ color: #667eea; font-weight: 500; text-decoration: none; }}
        .meta {{ font-size: 0.85rem; color: #888; margin-top: 5px; }}
        .stats {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0; }}
        .stat {{ background: rgba(255,255,255,0.08); padding: 8px 12px; border-radius: 8px; font-size: 0.85rem; }}
        .video-breakdown {{ background: rgba(102, 126, 234, 0.1); padding: 10px 15px; border-radius: 8px; margin: 10px 0; }}
        .badge {{ display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; margin-right: 5px; }}
        .badge-green {{ background: rgba(40, 167, 69, 0.2); color: #28a745; }}
        .badge-blue {{ background: rgba(102, 126, 234, 0.2); color: #667eea; }}
        .badge-yellow {{ background: rgba(255, 193, 7, 0.2); color: #ffc107; }}
        .btn {{ display: inline-block; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 8px; margin: 5px 5px 5px 0; font-size: 0.9rem; }}
        .btn:hover {{ background: #5a6fd6; }}
        .rank {{ font-size: 1.5rem; font-weight: bold; color: #667eea; margin-right: 15px; }}
        .footer {{ text-align: center; padding: 30px; color: #666; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Faceless Viral Hunter Report</h1>
            <p>Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
            <div class="search-info">🔍 Search: <strong>{search_query}</strong></div>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <div class="num">{len(df)}</div>
                <div class="label">📊 Channels Found</div>
            </div>
            <div class="summary-card">
                <div class="num">{df['Views'].sum():,.0f}</div>
                <div class="label">👁️ Total Views</div>
            </div>
            <div class="summary-card">
                <div class="num">{df['Virality'].mean():,.0f}/day</div>
                <div class="label">🔥 Avg Virality</div>
            </div>
            <div class="summary-card">
                <div class="num">${df['EstRevenue'].sum():,.0f}</div>
                <div class="label">💰 Est. Revenue</div>
            </div>
        </div>
"""
    
    for idx, row in df.iterrows():
        rank_emoji = "🏆" if idx == 0 else ("🥈" if idx == 1 else ("🥉" if idx == 2 else "⭐"))
        mon_badge = "badge-green" if row['MonetizationScore'] >= 70 else "badge-yellow"
        
        html += f"""
        <div class="card">
            <div class="card-header">
                <span class="rank">{rank_emoji}#{idx+1}</span>
                <img src="{row['Thumb']}" class="thumb" alt="Thumbnail">
                <div class="card-content">
                    <div class="card-title"><a href="{row['Link']}" target="_blank">{row['Title']}</a></div>
                    <a href="{row['ChannelLink']}" target="_blank" class="channel">📺 {row['Channel']}</a>
                    <div class="meta">
                        🌍 {row['Country']} • 📅 Created: {row['ChCreated']} • 📂 {row['Niche']}
                    </div>
                </div>
            </div>
            
            <div class="video-breakdown">
                <strong>📊 Video Breakdown:</strong> 
                🎬 Total: {row['TotalVideos']} | 
                📱 Shorts: {row['ShortsCount']} | 
                ⏱️ Medium: {row['MediumCount']} | 
                🎥 Long: {row['LongCount']}
            </div>
            
            <div class="stats">
                <div class="stat">👁️ {row['Views']:,} views</div>
                <div class="stat">👥 {row['Subs']:,} subs</div>
                <div class="stat">🔥 {row['Virality']:,.0f}/day</div>
                <div class="stat">💬 {row['Engagement%']}%</div>
                <div class="stat">⭐ Quality: {row['QualityScore']:.0f}</div>
                <div class="stat">💰 ${row['EstRevenue']:,.0f}</div>
            </div>
            
            <div>
                <span class="badge {mon_badge}">💰 Monetized ({row['MonetizationScore']}%)</span>
                <span class="badge badge-blue">✅ Faceless ({row['FacelessScore']}%)</span>
            </div>
            
            <div style="margin-top: 15px;">
                <a href="{row['Link']}" target="_blank" class="btn">▶️ Watch Video</a>
                <a href="{row['ChannelLink']}" target="_blank" class="btn" style="background: rgba(255,255,255,0.1);">📺 View Channel</a>
            </div>
        </div>
"""
    
    html += """
        <div class="footer">
            <p>🎯 Faceless Viral Hunter Report</p>
            <p>Made with ❤️ for Muhammed Rizwan Qamar</p>
        </div>
    </div>
</body>
</html>
"""
    return html


# ------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------
def fetch_json(url, params, quota_cost=0):
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            if quota_cost > 0:
                add_quota(quota_cost)
            return resp.json()
        if "quotaExceeded" in resp.text or resp.status_code == 403:
            return "QUOTA"
    except:
        pass
    return None


def parse_duration(duration):
    if not duration:
        return 0
    total = 0
    matches = re.findall(r"(\d+)([HMS])", duration)
    for value, unit in matches:
        if unit == "H":
            total += int(value) * 3600
        elif unit == "M":
            total += int(value) * 60
        elif unit == "S":
            total += int(value)
    return total


def calculate_virality(views, published_at):
    try:
        pub_date = datetime.strptime(published_at[:19], "%Y-%m-%dT%H:%M:%S")
        days_since = max((datetime.utcnow() - pub_date).days, 1)
        return round(views / days_since, 2)
    except:
        return 0


def calculate_engagement(views, likes, comments):
    if views == 0:
        return 0
    return round(((likes + comments * 2) / views) * 100, 2)


def calculate_quality_score(views, virality, engagement, mon_score, faceless_score, subs, avg_views):
    score = 0
    
    # Virality (25 pts)
    if virality >= 5000: score += 25
    elif virality >= 2000: score += 20
    elif virality >= 1000: score += 15
    elif virality >= 500: score += 10
    else: score += 5
    
    # Engagement (20 pts)
    if engagement >= 5: score += 20
    elif engagement >= 3: score += 15
    elif engagement >= 1: score += 10
    else: score += 5
    
    # Monetization (20 pts)
    score += mon_score * 0.2
    
    # Faceless (15 pts)
    score += faceless_score * 0.15
    
    # Channel size sweet spot (10 pts)
    if 5000 <= subs <= 50000: score += 10
    elif 1000 <= subs < 5000: score += 7
    else: score += 5
    
    # Avg views (10 pts)
    if avg_views >= 10000: score += 10
    elif avg_views >= 5000: score += 7
    else: score += 5
    
    return min(round(score, 1), 100)


def check_monetization(ch):
    score = 0
    subs = ch.get("subs", 0)
    total_views = ch.get("total_views", 0)
    created = ch.get("created", "")
    country = ch.get("country", "N/A")
    
    # Subs check (1000+ required)
    if subs >= 1000:
        score += 35
    elif subs >= 500:
        score += 15
    
    # Channel age (30+ days)
    if created:
        try:
            created_date = datetime.strptime(created[:19], "%Y-%m-%dT%H:%M:%S")
            days_old = (datetime.utcnow() - created_date).days
            if days_old >= 30:
                score += 20
        except:
            pass
    
    # Watch hours estimate
    watch_hours = (total_views * 3) / 60
    if watch_hours >= 4000:
        score += 30
    elif watch_hours >= 2000:
        score += 15
    
    # Country
    if country in MONETIZATION_COUNTRIES:
        score += 15
    
    return min(score, 100)


def detect_faceless(ch):
    score = 0
    profile = ch.get("profile", "")
    banner = ch.get("banner", "")
    name = ch.get("name", "").lower()
    desc = ch.get("description", "").lower()
    
    if "default.jpg" in profile:
        score += 30
    if not banner:
        score += 20
    
    for kw in FACELESS_INDICATORS:
        if kw in name:
            score += 15
            break
    
    for kw in FACELESS_INDICATORS:
        if kw in desc:
            score += 10
            break
    
    return score >= 35, min(score, 100)


def detect_niche(title, channel, keyword):
    text = f"{title} {channel} {keyword}".lower()
    niches = {
        "Reddit Stories": ["reddit", "aita", "tifu", "revenge"],
        "Horror": ["horror", "scary", "creepy", "nightmare"],
        "True Crime": ["true crime", "murder", "case"],
        "Motivation": ["motivation", "stoic", "discipline"],
        "Facts": ["facts", "top 10", "explained"],
        "Gaming": ["gaming", "gameplay"],
        "Mystery": ["mystery", "unsolved"]
    }
    for niche, kws in niches.items():
        if any(k in text for k in kws):
            return niche
    return "Other"


def estimate_revenue(views, country):
    cpm = CPM_RATES.get(country, 1.0)
    return round((views * 0.55 / 1000) * cpm, 2)


def get_video_type(duration):
    if duration < 60:
        return "Shorts"
    elif duration < 300:
        return "Medium"
    return "Long"


def batch_fetch_channels(channel_ids, api_key, cache):
    new_ids = [cid for cid in channel_ids if cid not in cache]
    if not new_ids:
        return cache, False
    
    for i in range(0, len(new_ids), 50):
        batch = new_ids[i:i+50]
        params = {
            "part": "snippet,statistics,brandingSettings",
            "id": ",".join(batch),
            "key": api_key
        }
        data = fetch_json(CHANNELS_URL, params, quota_cost=1)
        if data == "QUOTA":
            return cache, True
        if not data:
            continue
        
        for c in data.get("items", []):
            sn = c["snippet"]
            stats = c["statistics"]
            brand = c.get("brandingSettings", {}).get("image", {})
            
            cache[c["id"]] = {
                "name": sn.get("title", ""),
                "subs": int(stats.get("subscriberCount", 0)),
                "total_views": int(stats.get("viewCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
                "created": sn.get("publishedAt", ""),
                "country": sn.get("country", "N/A"),
                "description": sn.get("description", ""),
                "profile": sn.get("thumbnails", {}).get("default", {}).get("url", ""),
                "banner": brand.get("bannerExternalUrl", "")
            }
    return cache, False


# ------------------------------------------------------------
# QUICK SEARCH BUTTON HANDLERS
# ------------------------------------------------------------
def set_search(query):
    st.session_state.search_query = query
    st.session_state.trigger_search = True


# ------------------------------------------------------------
# MAIN UI
# ------------------------------------------------------------
# Header with HTML Download Button (Top Left)
col_header1, col_header2 = st.columns([1, 4])

with col_header1:
    if st.session_state.results_df is not None and len(st.session_state.results_df) > 0:
        html_report = generate_html_report(
            st.session_state.results_df, 
            st.session_state.search_query
        )
        st.download_button(
            "📥 HTML",
            data=html_report,
            file_name=f"faceless_report_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
            mime="text/html",
            use_container_width=True
        )
    else:
        st.button("📥 HTML", disabled=True, use_container_width=True)

with col_header2:
    st.title("🎯 Faceless Viral Hunter")

st.markdown("**Find monetized faceless channels from last 6 months | High CPM countries only**")

# Quota Display
st.sidebar.header("📊 API Quota")
st.sidebar.metric("Quota Used", f"{st.session_state.quota_used} units")
st.sidebar.caption("Daily limit: 10,000 units")
st.sidebar.progress(min(st.session_state.quota_used / 10000, 1.0))

if st.sidebar.button("🔄 Reset Quota Counter"):
    st.session_state.quota_used = 0
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Filters")
st.sidebar.info("""
**Fixed Settings:**
- 📅 Channels: Last 6 months
- 💰 Monetized only (1000+ subs)
- 🌍 Premium countries
- 📊 Max 5 results
- 👁️ Min 5,000 views
""")

# Search Section
st.markdown("---")
st.markdown("### 🔍 Search")
st.markdown("Enter **niche**, **keywords**, or **titles** - anything you want to find!")

# Quick Search Buttons - FIXED
st.markdown("**⚡ Quick Search:**")
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    if st.button("📖 Reddit", key="btn_reddit", use_container_width=True):
        set_search("Reddit Stories AITA")
        
with col2:
    if st.button("👻 Horror", key="btn_horror", use_container_width=True):
        set_search("Horror Scary Stories")

with col3:
    if st.button("💪 Motivation", key="btn_motivation", use_container_width=True):
        set_search("Stoicism Motivation")

with col4:
    if st.button("📊 Top 10", key="btn_top10", use_container_width=True):
        set_search("Top 10 Facts")

with col5:
    if st.button("🔍 True Crime", key="btn_crime", use_container_width=True):
        set_search("True Crime Documentary")

with col6:
    if st.button("❓ Mystery", key="btn_mystery", use_container_width=True):
        set_search("Unsolved Mysteries")

# Search Input
search_input = st.text_input(
    "🔎 Type your search:",
    value=st.session_state.search_query,
    placeholder="e.g., reddit stories, horror, motivation, top 10 facts...",
    key="search_box"
)

# Update session state if user types
if search_input != st.session_state.search_query:
    st.session_state.search_query = search_input

st.markdown("---")

# Settings Summary
st.info(f"""
📌 **Search Settings:**
- 🔍 Query: **{st.session_state.search_query or 'Not set'}**
- 🌍 Countries: **{', '.join(PREMIUM_COUNTRIES[:5])}...** (Premium CPM)
- 📅 Channels from: **Last 6 months**
- 💰 Requirement: **Monetized (1000+ subs)**
- 📊 Results: **Top 5 only** (Quota saver)
""")


# ------------------------------------------------------------
# SEARCH FUNCTION
# ------------------------------------------------------------
def run_search(query):
    if not query.strip():
        st.error("⚠️ Please enter a search query!")
        return None
    
    all_results = []
    channel_cache = {}
    seen_channels = set()
    quota_exceeded = False
    
    # Last 6 months
    six_months_ago = (datetime.utcnow() - timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    progress = st.progress(0)
    status = st.empty()
    
    stats = {"searched": 0, "passed": 0}
    
    # Search in premium countries only
    search_regions = PREMIUM_COUNTRIES[:3]  # US, CA, GB for quota saving
    
    for idx, region in enumerate(search_regions):
        if quota_exceeded or len(all_results) >= MAX_RESULTS * 3:
            break
        
        progress.progress((idx + 1) / len(search_regions) * 0.4)
        status.markdown(f"🔍 Searching in **{region}**: `{query}`")
        
        search_params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "order": "viewCount",
            "publishedAfter": six_months_ago,
            "maxResults": 50,
            "regionCode": region,
            "relevanceLanguage": "en",
            "videoDuration": "medium",  # Exclude shorts at API level
            "key": API_KEY
        }
        
        data = fetch_json(SEARCH_URL, search_params, quota_cost=100)
        
        if data == "QUOTA":
            quota_exceeded = True
            st.warning("⚠️ API Quota exhausted!")
            break
        
        if not data:
            continue
        
        items = data.get("items", [])
        stats["searched"] += len(items)
        
        # Filter unique channels
        new_items = []
        for item in items:
            cid = item.get("snippet", {}).get("channelId")
            vid = item.get("id", {}).get("videoId")
            if vid and cid and cid not in seen_channels:
                new_items.append(item)
        
        if not new_items:
            continue
        
        video_ids = [i["id"]["videoId"] for i in new_items]
        channel_ids = list({i["snippet"]["channelId"] for i in new_items})
        
        # Fetch video stats
        progress.progress(0.6)
        status.markdown("📊 Getting video statistics...")
        
        video_stats = {}
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]
            vid_data = fetch_json(VIDEOS_URL, {
                "part": "statistics,contentDetails",
                "id": ",".join(batch),
                "key": API_KEY
            }, quota_cost=1)
            
            if vid_data == "QUOTA":
                quota_exceeded = True
                break
            if vid_data:
                for v in vid_data.get("items", []):
                    s = v.get("statistics", {})
                    video_stats[v["id"]] = {
                        "views": int(s.get("viewCount", 0)),
                        "likes": int(s.get("likeCount", 0)),
                        "comments": int(s.get("commentCount", 0)),
                        "duration": parse_duration(v["contentDetails"].get("duration", ""))
                    }
        
        # Fetch channel stats
        progress.progress(0.8)
        status.markdown("📺 Getting channel info...")
        
        channel_cache, quota_hit = batch_fetch_channels(channel_ids, API_KEY, channel_cache)
        if quota_hit:
            quota_exceeded = True
        
        # Process results
        for item in new_items:
            if len(all_results) >= MAX_RESULTS * 3:
                break
            
            sn = item["snippet"]
            vid = item["id"]["videoId"]
            cid = sn["channelId"]
            v_stats = video_stats.get(vid, {})
            ch = channel_cache.get(cid, {})
            
            if not v_stats or not ch:
                continue
            
            views = v_stats.get("views", 0)
            likes = v_stats.get("likes", 0)
            comments = v_stats.get("comments", 0)
            duration = v_stats.get("duration", 0)
            subs = ch.get("subs", 0)
            total_videos = ch.get("video_count", 0)
            total_views = ch.get("total_views", 0)
            avg_views = total_views / max(total_videos, 1)
            country = ch.get("country", "N/A")
            created = ch.get("created", "")
            
            # ========== FILTERS ==========
            
            # Min views: 5000
            if views < 5000:
                continue
            
            # Subscribers: 1000-100000 (monetizable range)
            if subs < 1000 or subs > 100000:
                continue
            
            # Premium countries only
            if country not in PREMIUM_COUNTRIES:
                continue
            
            # Channel created in last 6 months
            if created:
                try:
                    created_date = datetime.strptime(created[:19], "%Y-%m-%dT%H:%M:%S")
                    channel_age_days = (datetime.utcnow() - created_date).days
                    if channel_age_days > 180:  # More than 6 months old
                        continue
                except:
                    continue
            
            # Must be faceless
            is_faceless, faceless_score = detect_faceless(ch)
            if not is_faceless:
                continue
            
            # Must be monetized (high score)
            mon_score = check_monetization(ch)
            if mon_score < 50:  # At least possibly monetized
                continue
            
            # ========== PASSED FILTERS ==========
            
            seen_channels.add(cid)
            stats["passed"] += 1
            
            virality = calculate_virality(views, sn["publishedAt"])
            engagement = calculate_engagement(views, likes, comments)
            niche = detect_niche(sn["title"], sn["channelTitle"], query)
            est_revenue = estimate_revenue(total_views, country)
            vtype = get_video_type(duration)
            
            quality_score = calculate_quality_score(
                views, virality, engagement, mon_score,
                faceless_score, subs, avg_views
            )
            
            # Estimate video breakdown (based on typical faceless channel patterns)
            shorts_pct = 0.3 if "shorts" in ch.get("description", "").lower() else 0.1
            shorts_count = int(total_videos * shorts_pct)
            long_count = int(total_videos * 0.4)
            medium_count = total_videos - shorts_count - long_count
            
            all_results.append({
                "Title": sn["title"],
                "Channel": sn["channelTitle"],
                "ChannelID": cid,
                "Subs": subs,
                "TotalVideos": total_videos,
                "ShortsCount": shorts_count,
                "MediumCount": medium_count,
                "LongCount": long_count,
                "AvgViews": round(avg_views, 0),
                "Views": views,
                "Likes": likes,
                "Comments": comments,
                "Virality": virality,
                "Engagement%": engagement,
                "QualityScore": quality_score,
                "FacelessScore": faceless_score,
                "MonetizationScore": mon_score,
                "EstRevenue": est_revenue,
                "Niche": niche,
                "Country": country,
                "Type": vtype,
                "Duration": duration,
                "DurationStr": f"{duration//60}:{duration%60:02d}",
                "Uploaded": sn["publishedAt"][:10],
                "ChCreated": created[:10] if created else "N/A",
                "ChannelAge": f"{channel_age_days} days",
                "Thumb": sn["thumbnails"]["high"]["url"],
                "Link": f"https://www.youtube.com/watch?v={vid}",
                "ChannelLink": f"https://www.youtube.com/channel/{cid}",
                "Keyword": query
            })
    
    progress.progress(1.0)
    status.empty()
    progress.empty()
    
    if not all_results:
        st.warning("😔 No results found! Try different keywords.")
        return None
    
    # Sort by quality and get top 5
    df = pd.DataFrame(all_results)
    df = df.sort_values("QualityScore", ascending=False).head(MAX_RESULTS).reset_index(drop=True)
    
    # Show stats
    st.markdown("### 📊 Search Stats")
    cols = st.columns(4)
    cols[0].metric("Videos Searched", stats["searched"])
    cols[1].metric("Passed Filters", stats["passed"])
    cols[2].metric("Final Results", len(df))
    cols[3].metric("Quota Used", f"{st.session_state.quota_used}")
    
    return df


# ------------------------------------------------------------
# SEARCH TRIGGER
# ------------------------------------------------------------
# Check for auto-trigger from quick buttons
should_search = st.session_state.trigger_search

# Manual search button
if st.button("🚀 FIND TOP 5 MONETIZED FACELESS CHANNELS", type="primary", use_container_width=True):
    should_search = True

# Run search
if should_search and st.session_state.search_query.strip():
    st.session_state.trigger_search = False
    
    df = run_search(st.session_state.search_query)
    
    if df is not None:
        st.session_state.results_df = df
        
        st.success(f"🎉 **TOP {len(df)} MONETIZED FACELESS CHANNELS** found!")
        st.balloons()
        
        # Display results
        for idx, r in df.iterrows():
            with st.container():
                st.markdown("---")
                
                rank = "🏆 #1" if idx == 0 else ("🥈 #2" if idx == 1 else ("🥉 #3" if idx == 2 else f"⭐ #{idx+1}"))
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"### {rank} - {r['Title']}")
                    st.markdown(f"**📺 [{r['Channel']}]({r['ChannelLink']})** • 👥 {r['Subs']:,} subs • 🌍 {r['Country']} • 📂 {r['Niche']}")
                    st.markdown(f"📅 Channel Age: **{r['ChannelAge']}** • Created: {r['ChCreated']}")
                    
                    # Video Breakdown
                    st.info(f"""
                    📊 **Video Breakdown:**
                    🎬 Total: **{r['TotalVideos']}** | 📱 Shorts: **{r['ShortsCount']}** | ⏱️ Medium: **{r['MediumCount']}** | 🎥 Long: **{r['LongCount']}**
                    """)
                    
                    st.markdown(f"### ⭐ Quality Score: **{r['QualityScore']:.0f}/100**")
                    
                    # Monetization
                    if r['MonetizationScore'] >= 70:
                        st.success(f"💰 Likely Monetized ({r['MonetizationScore']}%) | Est Revenue: ${r['EstRevenue']:,.0f}")
                    else:
                        st.info(f"💰 Possibly Monetized ({r['MonetizationScore']}%)")
                    
                    # Stats
                    cols = st.columns(5)
                    cols[0].metric("👁️ Views", f"{r['Views']:,}")
                    cols[1].metric("🔥 Virality", f"{r['Virality']:,.0f}/day")
                    cols[2].metric("💬 Engage", f"{r['Engagement%']}%")
                    cols[3].metric("📊 Avg/Vid", f"{r['AvgViews']:,.0f}")
                    cols[4].metric("✅ Faceless", f"{r['FacelessScore']}%")
                    
                    st.markdown(f"⏱️ Video: {r['DurationStr']} ({r['Type']}) • 👍 {r['Likes']:,} likes • 📤 Uploaded: {r['Uploaded']}")
                    
                    st.markdown(f"[▶️ **Watch Video**]({r['Link']}) | [📺 **Visit Channel**]({r['ChannelLink']})")
                
                with col2:
                    st.image(r["Thumb"], use_container_width=True)
        
        # Download Section
        st.markdown("---")
        st.markdown("### 📥 Download Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download CSV",
                data=csv,
                file_name=f"faceless_{st.session_state.search_query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            html_report = generate_html_report(df, st.session_state.search_query)
            st.download_button(
                "📥 Download HTML Report",
                data=html_report,
                file_name=f"faceless_report_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
                mime="text/html",
                use_container_width=True
            )
        
        with col3:
            json_data = df.to_json(orient='records', indent=2)
            st.download_button(
                "📥 Download JSON",
                data=json_data,
                file_name=f"faceless_{st.session_state.search_query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True
            )

elif should_search:
    st.error("⚠️ Please enter a search query or click a quick search button!")
    st.session_state.trigger_search = False

# Footer
st.markdown("---")
st.caption(f"Made with ❤️ for Muhammed Rizwan Qamar | Quota Used: {st.session_state.quota_used}/10,000")
