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
st.title("🎯 Faceless Viral Hunter")
st.markdown("**Kuch bhi search karo - Sirf 5 BEST faceless channels milenge!**")

API_KEY = st.secrets["YOUTUBE_API_KEY"]

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

# Fixed settings for quota saving
MAX_RESULTS = 5  # Only show 5 results

# ------------------------------------------------------------
# KEYWORD LISTS
# ------------------------------------------------------------
FACELESS_INDICATORS = [
    "stories", "reddit", "aita", "am i the", "horror", "scary", "creepy",
    "nightmare", "revenge", "update", "confession", "askreddit", "tifu",
    "relationship", "cheating", "karma", "tales", "narration", "narrator",
    "motivation", "motivational", "stoic", "stoicism", "wisdom", "quotes",
    "facts", "explained", "documentary", "history", "mystery", "unsolved",
    "crime", "true crime", "case", "cash cow", "compilation", "top 10",
    "top 5", "ranking", "countdown", "best of", "worst of", "gaming",
    "gameplay", "walkthrough", "tutorial", "how to", "guide", "tips",
    "ai voice", "text to speech", "tts", "automated", "no face",
    "anonymous", "faceless", "voice over", "voiceover", "narrated"
]

FACELESS_DESCRIPTION_KEYWORDS = [
    "ai generated", "text to speech", "tts", "voice over", "narration",
    "reddit stories", "scary stories", "horror stories", "true stories",
    "motivation", "stoicism", "self improvement", "cash cow", "automated",
    "compilation", "no face", "faceless", "anonymous channel"
]

PREMIUM_COUNTRIES = {
    'US', 'CA', 'GB', 'AU', 'NZ', 'DE', 'FR', 'IT', 'ES', 'NL', 'BE', 'AT', 'CH',
    'SE', 'NO', 'DK', 'FI', 'IE', 'LU', 'JP', 'KR', 'SG', 'HK'
}

MONETIZATION_COUNTRIES = {
    'US', 'CA', 'GB', 'AU', 'NZ', 'DE', 'FR', 'IT', 'ES', 'NL', 'BE', 'AT', 'CH',
    'SE', 'NO', 'DK', 'FI', 'IE', 'LU', 'JP', 'KR', 'SG', 'HK', 'IN', 'BR', 'MX',
    'AR', 'PL', 'CZ', 'RO', 'GR', 'PT', 'HU', 'TW', 'TH', 'MY', 'ID', 'PH', 'VN',
    'ZA', 'NG', 'EG', 'PK', 'BD', 'RU', 'UA', 'TR', 'SA', 'AE', 'IL', 'CL', 'CO', 'PE'
}

CPM_RATES = {
    'US': 4.0, 'CA': 3.5, 'GB': 3.5, 'AU': 4.0, 'NZ': 3.0,
    'DE': 3.5, 'FR': 2.5, 'IT': 2.0, 'ES': 2.0, 'NL': 3.0,
    'BE': 2.5, 'AT': 3.0, 'CH': 4.5, 'SE': 3.0, 'NO': 4.0,
    'DK': 3.0, 'FI': 2.5, 'IE': 3.0, 'LU': 3.5, 'JP': 2.5,
    'KR': 2.0, 'SG': 2.5, 'HK': 2.0, 'IN': 0.5, 'BR': 0.8,
    'MX': 0.7, 'PH': 0.3, 'ID': 0.4, 'PK': 0.3, 'N/A': 1.0
}

NICHE_CPM_MULTIPLIERS = {
    "Finance": 2.0, "Tech": 1.5, "Health": 1.4, "Business": 1.6,
    "Education": 1.3, "True Crime": 1.2, "Horror/Scary": 1.0,
    "Reddit Stories": 0.9, "Gaming": 0.8, "Entertainment": 0.7, "Other": 1.0
}


# ------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------
def fetch_json(url, params, retries=2):
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            if "quotaExceeded" in resp.text or resp.status_code == 403:
                return "QUOTA"
        except:
            if attempt < retries - 1:
                continue
            return None
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


def calculate_virality_score(views, published_at):
    try:
        pub_date = datetime.strptime(published_at[:19], "%Y-%m-%dT%H:%M:%S")
        days_since = max((datetime.utcnow() - pub_date).days, 1)
        return round(views / days_since, 2)
    except:
        return 0


def calculate_engagement_rate(views, likes, comments):
    if views == 0:
        return 0
    return round(((likes + comments * 2) / views) * 100, 2)


def calculate_quality_score(views, virality, engagement, monetization_score, faceless_score, subs, avg_views):
    """Calculate overall quality score (0-100)"""
    score = 0
    
    # Virality (25 points)
    if virality >= 10000:
        score += 25
    elif virality >= 5000:
        score += 20
    elif virality >= 2000:
        score += 15
    elif virality >= 1000:
        score += 10
    elif virality >= 500:
        score += 5
    
    # Engagement (20 points)
    if engagement >= 10:
        score += 20
    elif engagement >= 5:
        score += 15
    elif engagement >= 2:
        score += 10
    elif engagement >= 1:
        score += 5
    
    # Monetization (20 points)
    score += monetization_score * 0.2
    
    # Faceless confidence (15 points)
    score += faceless_score * 0.15
    
    # Channel size sweet spot 1K-20K (10 points)
    if 5000 <= subs <= 20000:
        score += 10
    elif 1000 <= subs < 5000:
        score += 7
    elif subs > 20000:
        score += 5
    
    # Avg views (10 points)
    if avg_views >= 20000:
        score += 10
    elif avg_views >= 10000:
        score += 8
    elif avg_views >= 5000:
        score += 5
    elif avg_views >= 2000:
        score += 3
    
    return min(round(score, 1), 100)


def calculate_upload_frequency(created_date, total_videos):
    try:
        if not created_date or total_videos == 0:
            return 0, "N/A"
        created = datetime.strptime(created_date[:19], "%Y-%m-%dT%H:%M:%S")
        days_active = max((datetime.utcnow() - created).days, 1)
        weeks_active = max(days_active / 7, 1)
        uploads_per_week = round(total_videos / weeks_active, 2)
        
        if uploads_per_week >= 7:
            schedule = f"🔥 Daily+ ({uploads_per_week:.1f}/week)"
        elif uploads_per_week >= 3:
            schedule = f"📈 Active ({uploads_per_week:.1f}/week)"
        elif uploads_per_week >= 1:
            schedule = f"✅ Regular ({uploads_per_week:.1f}/week)"
        else:
            schedule = f"📅 Occasional"
        
        return uploads_per_week, schedule
    except:
        return 0, "N/A"


def check_monetization_status(channel_data):
    score = 0
    subs = channel_data.get("subs", 0)
    total_videos = channel_data.get("video_count", 0)
    created = channel_data.get("created", "")
    country = channel_data.get("country", "N/A")
    total_views = channel_data.get("total_views", 0)
    
    if subs >= 1000:
        score += 30
    elif subs >= 500:
        score += 10
    
    if created:
        try:
            created_date = datetime.strptime(created[:19], "%Y-%m-%dT%H:%M:%S")
            days_old = (datetime.utcnow() - created_date).days
            if days_old >= 30:
                score += 15
        except:
            pass
    
    if country in MONETIZATION_COUNTRIES:
        score += 15
    
    estimated_watch_hours = (total_views * 3.2) / 60
    if estimated_watch_hours >= 4000:
        score += 25
    elif estimated_watch_hours >= 2000:
        score += 15
    
    if total_videos >= 50:
        score += 10
    elif total_videos >= 20:
        score += 5
    
    if score >= 70:
        status = "🟢 LIKELY MONETIZED"
    elif score >= 50:
        status = "🟡 POSSIBLY MONETIZED"
    elif score >= 30:
        status = "🟠 CLOSE"
    else:
        status = "🔴 NOT MONETIZED"
    
    return status, score


def detect_faceless(channel_data, strictness="Normal"):
    score = 0
    profile_url = channel_data.get("profile", "")
    banner_url = channel_data.get("banner", "")
    channel_name = channel_data.get("name", "").lower()
    description = channel_data.get("description", "").lower()
    
    if "default.jpg" in profile_url or "s88-c-k-c0x00ffffff-no-rj" in profile_url:
        score += 30
    
    if not banner_url:
        score += 20
    
    name_matches = sum(1 for kw in FACELESS_INDICATORS if kw in channel_name)
    if name_matches >= 1:
        score += min(name_matches * 15, 30)
    
    desc_matches = sum(1 for kw in FACELESS_DESCRIPTION_KEYWORDS if kw in description)
    if desc_matches >= 1:
        score += min(desc_matches * 10, 25)
    
    thresholds = {"Relaxed": 20, "Normal": 35, "Strict": 55}
    threshold = thresholds.get(strictness, 35)
    
    return score >= threshold, min(score, 100)


def get_video_type_label(duration):
    if duration < 60:
        return "Shorts"
    elif duration < 300:
        return "Medium"
    return "Long"


def estimate_revenue(views, country, video_count, niche="Other"):
    base_cpm = CPM_RATES.get(country, 1.0)
    niche_multiplier = NICHE_CPM_MULTIPLIERS.get(niche, 1.0)
    cpm = base_cpm * niche_multiplier
    monetized_views = views * 0.55
    revenue = (monetized_views / 1000) * cpm
    return round(revenue, 2)


def detect_niche(title, channel_name, keyword):
    text = f"{title} {channel_name} {keyword}".lower()
    niches = {
        "Reddit Stories": ["reddit", "aita", "am i the", "tifu", "entitled", "revenge"],
        "Horror/Scary": ["horror", "scary", "creepy", "nightmare", "paranormal"],
        "True Crime": ["true crime", "crime", "murder", "case", "investigation"],
        "Motivation": ["motivation", "stoic", "stoicism", "mindset", "discipline"],
        "Facts/Education": ["facts", "explained", "documentary", "history", "top 10"],
        "Gaming": ["gaming", "gameplay", "walkthrough", "gamer"],
        "Compilation": ["compilation", "best of", "funny", "fails"],
        "Mystery": ["mystery", "mysteries", "unsolved", "conspiracy"],
        "Finance": ["money", "invest", "stock", "crypto", "finance", "wealth"],
        "Tech": ["tech", "technology", "gadget", "software"],
        "Health": ["health", "fitness", "diet", "workout"]
    }
    for niche, keywords in niches.items():
        if any(kw in text for kw in keywords):
            return niche
    return "Other"


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
        data = fetch_json(CHANNELS_URL, params)
        if data == "QUOTA":
            return cache, True
        if not data:
            continue
        
        for c in data.get("items", []):
            sn = c["snippet"]
            stats = c["statistics"]
            brand = c.get("brandingSettings", {})
            brand_img = brand.get("image", {})
            
            cache[c["id"]] = {
                "name": sn.get("title", ""),
                "subs": int(stats.get("subscriberCount", 0)),
                "total_views": int(stats.get("viewCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
                "created": sn.get("publishedAt", ""),
                "country": sn.get("country", "N/A"),
                "description": sn.get("description", ""),
                "profile": sn.get("thumbnails", {}).get("default", {}).get("url", ""),
                "banner": brand_img.get("bannerExternalUrl", "")
            }
    return cache, False


# ------------------------------------------------------------
# HTML REPORT GENERATOR
# ------------------------------------------------------------
def generate_html_report(df):
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Faceless Viral Hunter Report - {datetime.now().strftime("%Y-%m-%d")}</title>
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
        .header h1 {{ font-size: 2rem; margin-bottom: 8px; }}
        .card {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .card-header {{ display: flex; gap: 15px; margin-bottom: 15px; }}
        .thumb {{ width: 180px; height: 100px; border-radius: 8px; object-fit: cover; }}
        .card-title {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 8px; }}
        .card-title a {{ color: #fff; text-decoration: none; }}
        .channel {{ color: #667eea; font-weight: 500; }}
        .stats {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 12px 0; }}
        .stat {{ background: rgba(255,255,255,0.08); padding: 8px 12px; border-radius: 8px; font-size: 0.85rem; }}
        .badge {{ display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; margin-right: 5px; }}
        .badge-green {{ background: rgba(40, 167, 69, 0.2); color: #28a745; }}
        .badge-blue {{ background: rgba(102, 126, 234, 0.2); color: #667eea; }}
        .btn {{ display: inline-block; padding: 8px 16px; background: #667eea; color: white; text-decoration: none; border-radius: 6px; margin-right: 8px; font-size: 0.85rem; }}
        .footer {{ text-align: center; padding: 20px; color: #666; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Faceless Viral Hunter Report</h1>
            <p>Generated: {datetime.now().strftime("%B %d, %Y")}</p>
        </div>
"""
    
    for idx, row in df.iterrows():
        html += f"""
        <div class="card">
            <div class="card-header">
                <img src="{row['Thumb']}" class="thumb">
                <div>
                    <div class="card-title"><a href="{row['Link']}" target="_blank">{row['Title']}</a></div>
                    <a href="{row['ChannelLink']}" target="_blank" class="channel">📺 {row['Channel']}</a>
                    <div style="font-size: 0.85rem; color: #888; margin-top: 5px;">
                        🌍 {row['Country']} • 📅 {row['ChCreated']} • 🎬 {row['TotalVideos']} videos • 📂 {row['Niche']}
                    </div>
                </div>
            </div>
            <div class="stats">
                <div class="stat">👁️ {row['Views']:,} views</div>
                <div class="stat">👥 {row['Subs']:,} subs</div>
                <div class="stat">🔥 {row['Virality']:,}/day</div>
                <div class="stat">💬 {row['Engagement%']}%</div>
                <div class="stat">⭐ Quality: {row['QualityScore']:.0f}/100</div>
                <div class="stat">💰 ${row['EstRevenue']:,.0f}</div>
            </div>
            <div>
                <span class="badge badge-green">💰 {row['MonetizationScore']}% Monetized</span>
                <span class="badge badge-blue">✅ Faceless {row['FacelessScore']}%</span>
            </div>
            <div style="margin-top: 12px;">
                <a href="{row['Link']}" target="_blank" class="btn">▶️ Watch</a>
                <a href="{row['ChannelLink']}" target="_blank" class="btn" style="background: rgba(255,255,255,0.1);">📺 Channel</a>
            </div>
        </div>
"""
    
    html += """
        <div class="footer">
            <p>🎯 Faceless Viral Hunter | Made for Muhammed Rizwan Qamar</p>
        </div>
    </div>
</body>
</html>
"""
    return html


# ------------------------------------------------------------
# SIDEBAR - OPTIONAL ADVANCED FILTERS
# ------------------------------------------------------------
st.sidebar.header("⚙️ Advanced Filters (Optional)")

with st.sidebar.expander("📊 Filters", expanded=False):
    days = st.slider("Videos from last X days", 1, 90, 30)
    
    st.markdown("**👥 Subscribers**")
    min_subs = st.number_input("Min Subs", min_value=0, value=1000, step=100)
    max_subs = st.number_input("Max Subs", min_value=0, value=20000, step=1000)
    
    st.markdown("**🎬 Channel Videos**")
    min_videos = st.number_input("Min Videos", min_value=0, value=0, step=5)
    max_videos = st.number_input("Max Videos", min_value=0, value=500, step=50)
    
    st.markdown("**👁️ Views**")
    min_views = st.number_input("Min Views", min_value=1000, value=5000, step=1000)
    
    min_virality = st.slider("Min Virality (views/day)", 0, 5000, 100)
    
    video_type = st.selectbox("Video Duration", ["All", "Long (5min+)", "Medium (1-5min)", "Shorts (<1min)"])
    exclude_shorts = st.checkbox("Exclude Shorts", value=True)
    
    faceless_strictness = st.select_slider("Faceless Detection", ["Relaxed", "Normal", "Strict"], value="Normal")


# ------------------------------------------------------------
# MAIN SEARCH BOX
# ------------------------------------------------------------
st.markdown("---")
st.markdown("### 🔍 Search Box")
st.markdown("**Kuch bhi likho** - Keywords, Niches, Titles, Topics - Jo chahiye!")

search_query = st.text_input(
    "Search anything...",
    placeholder="e.g., reddit stories, horror, motivation, top 10, true crime...",
    help="Koi bhi keyword, niche, ya title type karo"
)

# Quick search buttons
st.markdown("**Quick Search:**")
cols = st.columns(6)
quick_searches = ["Reddit Stories", "Horror", "Motivation", "Top 10 Facts", "True Crime", "Stoicism"]
for i, qs in enumerate(quick_searches):
    if cols[i].button(qs, use_container_width=True):
        search_query = qs

st.markdown("---")

# Show current filters summary
st.info(f"""
📌 **Current Settings:**
- Subscribers: **{min_subs:,} - {max_subs:,}**
- Videos: **{min_videos} - {max_videos}**
- Min Views: **{min_views:,}+**
- Results: **Top 5 Best Channels**
""")


# ------------------------------------------------------------
# MAIN SEARCH BUTTON
# ------------------------------------------------------------
if st.button("🚀 FIND TOP 5 FACELESS CHANNELS", type="primary", use_container_width=True):
    
    if not search_query.strip():
        st.error("⚠️ Please enter a search query!")
        st.stop()
    
    all_results = []
    channel_cache = {}
    seen_channels = set()
    quota_exceeded = False
    
    published_after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    stats = {"searched": 0, "passed_filters": 0}
    
    # Search with different orders to get variety
    search_orders = ["viewCount", "relevance"]
    
    for order_idx, order in enumerate(search_orders):
        if quota_exceeded or len(all_results) >= MAX_RESULTS * 3:  # Get more to filter
            break
        
        progress_bar.progress((order_idx + 1) / len(search_orders) * 0.5)
        status_text.markdown(f"🔍 Searching: `{search_query}` ({order})...")
        
        search_params = {
            "part": "snippet",
            "q": search_query,
            "type": "video",
            "order": order,
            "publishedAfter": published_after,
            "maxResults": 50,
            "regionCode": "US",
            "relevanceLanguage": "en",
            "safeSearch": "none"
        }
        
        # Duration filter
        if exclude_shorts or video_type == "Long (5min+)":
            search_params["videoDuration"] = "long" if video_type == "Long (5min+)" else "medium"
        elif video_type == "Medium (1-5min)":
            search_params["videoDuration"] = "medium"
        elif video_type == "Shorts (<1min)":
            search_params["videoDuration"] = "short"
        
        data = fetch_json(SEARCH_URL, {**search_params, "key": API_KEY})
        
        if data == "QUOTA":
            quota_exceeded = True
            st.warning("⚠️ API Quota exhausted!")
            break
        
        if not data:
            continue
        
        items = data.get("items", [])
        stats["searched"] += len(items)
        
        # Filter out already seen channels
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
        progress_bar.progress(0.6)
        status_text.markdown("📊 Getting video stats...")
        
        video_stats = {}
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]
            vid_data = fetch_json(VIDEOS_URL, {
                "part": "statistics,contentDetails",
                "id": ",".join(batch),
                "key": API_KEY
            })
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
        progress_bar.progress(0.8)
        status_text.markdown("📺 Getting channel info...")
        
        channel_cache, quota_hit = batch_fetch_channels(channel_ids, API_KEY, channel_cache)
        if quota_hit:
            quota_exceeded = True
        
        # Process results
        for item in new_items:
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
            total_channel_views = ch.get("total_views", 0)
            avg_views = total_channel_views / max(total_videos, 1)
            
            # ============ APPLY FILTERS ============
            
            # Shorts filter
            if exclude_shorts and duration < 60:
                continue
            
            # Views filter (5000+)
            if views < min_views:
                continue
            
            # Subscriber filter (1000 - 20000)
            if not (min_subs <= subs <= max_subs):
                continue
            
            # Video count filter (0 - 500)
            if total_videos < min_videos or (max_videos > 0 and total_videos > max_videos):
                continue
            
            # Virality filter
            virality = calculate_virality_score(views, sn["publishedAt"])
            if virality < min_virality:
                continue
            
            # Faceless detection
            is_faceless, faceless_score = detect_faceless(ch, faceless_strictness)
            if not is_faceless:
                continue
            
            # Duration type filter
            vtype = get_video_type_label(duration)
            if video_type == "Long (5min+)" and duration < 300:
                continue
            if video_type == "Medium (1-5min)" and (duration < 60 or duration >= 300):
                continue
            if video_type == "Shorts (<1min)" and duration >= 60:
                continue
            
            # ============ PASSED ALL FILTERS ============
            
            seen_channels.add(cid)
            stats["passed_filters"] += 1
            
            country = ch.get("country", "N/A")
            niche = detect_niche(sn["title"], sn["channelTitle"], search_query)
            engagement = calculate_engagement_rate(views, likes, comments)
            monetization_status, monetization_score = check_monetization_status(ch)
            uploads_per_week, schedule = calculate_upload_frequency(ch.get("created", ""), total_videos)
            
            quality_score = calculate_quality_score(
                views, virality, engagement, monetization_score,
                faceless_score, subs, avg_views
            )
            
            est_revenue = estimate_revenue(total_channel_views, country, total_videos, niche)
            
            all_results.append({
                "Title": sn["title"],
                "Channel": sn["channelTitle"],
                "ChannelID": cid,
                "Subs": subs,
                "TotalVideos": total_videos,
                "AvgViews": round(avg_views, 0),
                "Views": views,
                "Likes": likes,
                "Comments": comments,
                "Virality": virality,
                "Engagement%": engagement,
                "QualityScore": quality_score,
                "FacelessScore": faceless_score,
                "MonetizationStatus": monetization_status,
                "MonetizationScore": monetization_score,
                "EstRevenue": est_revenue,
                "UploadsPerWeek": uploads_per_week,
                "Schedule": schedule,
                "Niche": niche,
                "Country": country,
                "Type": vtype,
                "Duration": duration,
                "DurationStr": f"{duration//60}:{duration%60:02d}",
                "Uploaded": sn["publishedAt"][:10],
                "ChCreated": ch.get("created", "")[:10] if ch.get("created") else "N/A",
                "Thumb": sn["thumbnails"]["high"]["url"],
                "Link": f"https://www.youtube.com/watch?v={vid}",
                "ChannelLink": f"https://www.youtube.com/channel/{cid}",
                "Keyword": search_query
            })
    
    progress_bar.progress(1.0)
    status_text.empty()
    progress_bar.empty()
    
    # Show stats
    st.markdown("### 📊 Search Stats")
    col1, col2, col3 = st.columns(3)
    col1.metric("Videos Searched", stats["searched"])
    col2.metric("Passed Filters", stats["passed_filters"])
    col3.metric("Final Results", min(len(all_results), MAX_RESULTS))
    
    if not all_results:
        st.warning("😔 No results found! Try different keywords or adjust filters.")
        st.stop()
    
    # Sort by quality and get top 5
    df = pd.DataFrame(all_results)
    df = df.sort_values("QualityScore", ascending=False).head(MAX_RESULTS).reset_index(drop=True)
    
    st.success(f"🎉 **TOP {len(df)} FACELESS CHANNELS** for: `{search_query}`")
    st.balloons()
    
    # Display results
    for idx, r in df.iterrows():
        with st.container():
            st.markdown("---")
            
            # Quality indicator
            if r['QualityScore'] >= 70:
                q_badge = "🏆"
            elif r['QualityScore'] >= 50:
                q_badge = "⭐"
            else:
                q_badge = "📊"
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### {q_badge} #{idx+1} - {r['Title']}")
                st.markdown(f"**📺 [{r['Channel']}]({r['ChannelLink']})** • 👥 {r['Subs']:,} subs • 🎬 {r['TotalVideos']} videos • 📊 Avg: {r['AvgViews']:,.0f}/vid")
                st.markdown(f"🌍 {r['Country']} • 📅 Created: {r['ChCreated']} • ⏰ {r['Schedule']} • 📂 {r['Niche']}")
                
                # Quality score prominent
                st.markdown(f"### ⭐ Quality Score: **{r['QualityScore']:.0f}/100**")
                
                # Monetization
                if "LIKELY" in r['MonetizationStatus']:
                    st.success(f"💰 {r['MonetizationStatus']} | Est Revenue: ${r['EstRevenue']:,.0f}")
                elif "POSSIBLY" in r['MonetizationStatus']:
                    st.info(f"💰 {r['MonetizationStatus']} ({r['MonetizationScore']}%)")
                else:
                    st.warning(f"💰 {r['MonetizationStatus']} ({r['MonetizationScore']}%)")
                
                # Stats
                cols = st.columns(5)
                cols[0].metric("👁️ Views", f"{r['Views']:,}")
                cols[1].metric("🔥 Virality", f"{r['Virality']:,.0f}/day")
                cols[2].metric("💬 Engage", f"{r['Engagement%']}%")
                cols[3].metric("👍 Likes", f"{r['Likes']:,}")
                cols[4].metric("💬 Comments", f"{r['Comments']:,}")
                
                st.markdown(f"⏱️ Duration: {r['DurationStr']} ({r['Type']}) • 📤 Uploaded: {r['Uploaded']}")
                
                st.success(f"✅ Faceless Confidence: **{r['FacelessScore']}%**")
                
                st.markdown(f"[▶️ **Watch Video**]({r['Link']}) | [📺 **Visit Channel**]({r['ChannelLink']})")
            
            with col2:
                st.image(r["Thumb"], use_container_width=True)
    
    # Download section
    st.markdown("---")
    st.markdown("### 📥 Download Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download CSV",
            data=csv,
            file_name=f"faceless_top5_{search_query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        html_report = generate_html_report(df)
        st.download_button(
            "📥 Download HTML",
            data=html_report,
            file_name=f"faceless_report_{search_query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html",
            use_container_width=True
        )
    
    with col3:
        json_data = df.to_json(orient='records', indent=2)
        st.download_button(
            "📥 Download JSON",
            data=json_data,
            file_name=f"faceless_top5_{search_query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )

# Footer
st.markdown("---")
st.caption("Made with ❤️ for Muhammed Rizwan Qamar | Faceless Viral Hunter 2025")
