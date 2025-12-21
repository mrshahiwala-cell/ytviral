import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import re
from collections import defaultdict
from io import BytesIO
import base64

# ------------------------------------------------------------
# APP CONFIG
# ------------------------------------------------------------
st.set_page_config(page_title="🎯 YouTube Channel Hunter PRO", layout="wide")
st.title("🎯 YouTube Channel Hunter PRO")
st.markdown("**Kisi bhi niche ke channels dhundo - Gaming, News, Tech, Cooking, Motivation, ANYTHING!**")

API_KEY = st.secrets["YOUTUBE_API_KEY"]

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

# ------------------------------------------------------------
# API QUOTA TRACKING
# ------------------------------------------------------------
if 'api_calls' not in st.session_state:
    st.session_state['api_calls'] = 0
if 'quota_used' not in st.session_state:
    st.session_state['quota_used'] = 0
if 'last_reset' not in st.session_state:
    st.session_state['last_reset'] = datetime.now().date()
if 'search_history' not in st.session_state:
    st.session_state['search_history'] = []
if 'cached_results' not in st.session_state:
    st.session_state['cached_results'] = {}

QUOTA_COSTS = {
    'search': 100,
    'videos': 1,
    'channels': 1
}
DAILY_QUOTA_LIMIT = 10000
QUOTA_SAFETY_BUFFER = 500

def check_quota_reset():
    today = datetime.now().date()
    if st.session_state['last_reset'] < today:
        st.session_state['quota_used'] = 0
        st.session_state['api_calls'] = 0
        st.session_state['last_reset'] = today
        st.session_state['search_history'] = []
        return True
    return False

check_quota_reset()

# ------------------------------------------------------------
# TOP 10 PREMIUM CPM COUNTRIES
# ------------------------------------------------------------
TOP_10_PREMIUM_COUNTRIES = ['US', 'AU', 'NO', 'CH', 'CA', 'GB', 'DE', 'LU', 'SE', 'NL']

# ------------------------------------------------------------
# EXPANDED CHANNEL DETECTION KEYWORDS - ALL NICHES INCLUDED
# ------------------------------------------------------------
FACELESS_INDICATORS = [
    # NEWS - ADDED
    "news", "breaking", "headlines", "daily news", "update", "latest", "report",
    "current events", "world news", "today", "bulletin",
    
    # TECH - ADDED
    "tech", "technology", "gadget", "review", "unboxing", "smartphone", "laptop",
    "software", "app", "digital", "ai", "artificial intelligence",
    
    # COOKING/FOOD - ADDED
    "cooking", "recipe", "recipes", "food", "kitchen", "chef", "meal", "cuisine",
    "baking", "delicious", "tasty", "yummy",
    
    # GAMING
    "gaming", "gameplay", "walkthrough", "gamer", "playthrough", "let's play",
    "game", "games", "xbox", "playstation", "nintendo", "pc gaming",
    
    # Reddit/Stories
    "stories", "reddit", "aita", "horror", "scary", "creepy",
    "motivation", "motivational", "stoic", "wisdom", "quotes",
    
    # Generic indicators
    "facts", "explained", "documentary", "history", "mystery",
    "top 10", "top 5", "ranking", "countdown", "best of",
    "compilation", "tutorial", "how to", "guide", "tips", "reviews",
    "daily", "weekly", "ai voice", "text to speech", "tts", 
    "voice over", "voiceover", "no face", "anonymous", "faceless", "narrated",
    
    # More generic
    "channel", "official", "tv", "media", "network",
    "podcast", "show", "series", "episode", "vlog", "blog",
    
    # FINANCE - ADDED
    "finance", "money", "stock", "crypto", "trading", "invest", "wealth",
    "business", "economy", "market",
    
    # ENTERTAINMENT - ADDED
    "entertainment", "celebrity", "movie", "movies", "film", "tv show",
    "drama", "comedy", "funny", "humor", "laugh",
    
    # SPORTS - ADDED
    "sports", "football", "soccer", "basketball", "cricket", "nfl", "nba",
    
    # EDUCATION - ADDED
    "education", "learn", "learning", "study", "course", "tutorial",
    "school", "university", "knowledge",
    
    # HEALTH/FITNESS - ADDED
    "health", "fitness", "workout", "exercise", "gym", "yoga", "wellness",
    
    # TRAVEL - ADDED
    "travel", "tour", "destination", "explore", "adventure", "trip",
    
    # MUSIC - ADDED
    "music", "song", "songs", "beats", "remix", "cover", "lofi", "chill",
]

FACELESS_DESCRIPTION_KEYWORDS = [
    "ai generated", "text to speech", "tts", "voice over", "narration",
    "automated", "compilation", "no face", "faceless", "anonymous",
    # Generic terms - MORE RELAXED
    "subscribe", "channel", "videos", "content", "upload",
    "weekly", "daily", "new videos", "entertainment",
    "news", "update", "latest", "breaking",
    "watch", "enjoy", "like", "share", "comment",
    "welcome", "thanks for watching", "don't forget",
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


# ------------------------------------------------------------
# QUOTA CALCULATOR
# ------------------------------------------------------------
def calculate_required_quota(keywords, regions, search_orders, use_pagination=True):
    search_calls = len(keywords) * len(regions) * len(search_orders)
    if use_pagination:
        search_calls *= 2
    
    search_quota = search_calls * QUOTA_COSTS['search']
    video_quota = search_calls * 2
    channel_quota = search_calls * 1
    total_quota = search_quota + video_quota + channel_quota
    
    return {
        'search_calls': search_calls,
        'search_quota': search_quota,
        'video_quota': video_quota,
        'channel_quota': channel_quota,
        'total_quota': total_quota
    }


def get_available_quota():
    return DAILY_QUOTA_LIMIT - st.session_state['quota_used'] - QUOTA_SAFETY_BUFFER


def can_afford_search(required_quota):
    available = get_available_quota()
    return available >= required_quota


def get_smart_search_config(keywords, regions, search_orders, available_quota):
    base_quota_per_combo = QUOTA_COSTS['search'] * 2
    extra_per_combo = 5
    quota_per_combo = base_quota_per_combo + extra_per_combo
    max_combos = available_quota // quota_per_combo
    current_combos = len(keywords) * len(regions) * len(search_orders)
    
    if current_combos <= max_combos:
        return {
            'keywords': keywords,
            'regions': regions,
            'orders': search_orders,
            'use_pagination': True,
            'reduced': False
        }
    
    recommendations = []
    
    reduced_regions = regions[:3]
    opt1_combos = len(keywords) * len(reduced_regions) * len(search_orders)
    if opt1_combos <= max_combos:
        recommendations.append({
            'keywords': keywords,
            'regions': reduced_regions,
            'orders': search_orders,
            'use_pagination': True,
            'reduced': True,
            'reduction': f"Regions: {len(regions)} → {len(reduced_regions)}"
        })
    
    opt2_combos = len(keywords) * len(regions) * 1
    if opt2_combos <= max_combos:
        recommendations.append({
            'keywords': keywords,
            'regions': regions,
            'orders': [search_orders[0]],
            'use_pagination': True,
            'reduced': True,
            'reduction': f"Orders: {len(search_orders)} → 1"
        })
    
    reduced_kw = keywords[:3]
    reduced_reg = regions[:3]
    reduced_ord = [search_orders[0]]
    opt3_combos = len(reduced_kw) * len(reduced_reg) * len(reduced_ord)
    if opt3_combos <= max_combos:
        recommendations.append({
            'keywords': reduced_kw,
            'regions': reduced_reg,
            'orders': reduced_ord,
            'use_pagination': True,
            'reduced': True,
            'reduction': f"Keywords: {len(keywords)}→{len(reduced_kw)}, Regions: {len(regions)}→{len(reduced_reg)}, Orders: {len(search_orders)}→1"
        })
    
    opt4_quota = len(keywords) * len(regions) * len(search_orders) * (QUOTA_COSTS['search'] + 5)
    if opt4_quota <= available_quota:
        recommendations.append({
            'keywords': keywords,
            'regions': regions,
            'orders': search_orders,
            'use_pagination': False,
            'reduced': True,
            'reduction': "Pagination disabled"
        })
    
    if recommendations:
        return recommendations[0]
    
    return {
        'keywords': keywords[:1],
        'regions': regions[:2],
        'orders': [search_orders[0]],
        'use_pagination': False,
        'reduced': True,
        'reduction': "Minimal safe mode"
    }


# ------------------------------------------------------------
# HTML REPORT GENERATOR
# ------------------------------------------------------------
def generate_html_report(df, stats, quota_exceeded=False):
    total_views = df['Views'].sum() if len(df) > 0 else 0
    avg_virality = df['Virality'].mean() if len(df) > 0 else 0
    monetized_count = len(df[df['MonetizationScore'] >= 70]) if len(df) > 0 else 0
    total_revenue = df['EstRevenue'].sum() if 'EstRevenue' in df.columns and len(df) > 0 else 0
    
    quota_warning = ""
    if quota_exceeded:
        quota_warning = """
        <div style="background: rgba(255, 193, 7, 0.2); border: 1px solid #ffc107; border-radius: 10px; padding: 15px; margin-bottom: 20px; text-align: center;">
            <strong>⚠️ API Quota Exhausted!</strong> - Partial results shown below.
        </div>
        """
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Channel Hunter PRO Report - {datetime.now().strftime("%Y-%m-%d")}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e4e4e4;
            line-height: 1.6;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        .header {{
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
        }}
        .header h1 {{ font-size: 2.5rem; font-weight: 700; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; font-size: 1.1rem; }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 25px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .stat-card .number {{
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .stat-card .label {{ font-size: 0.9rem; color: #888; margin-top: 5px; }}
        .section-title {{
            font-size: 1.8rem;
            font-weight: 600;
            margin-bottom: 25px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(102, 126, 234, 0.3);
        }}
        .video-card {{
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.08);
        }}
        .video-header {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .thumbnail {{ width: 200px; height: 112px; border-radius: 12px; object-fit: cover; }}
        .video-info {{ flex: 1; }}
        .video-title {{ font-size: 1.2rem; font-weight: 600; margin-bottom: 10px; color: #fff; }}
        .video-title a {{ color: #fff; text-decoration: none; }}
        .video-title a:hover {{ color: #667eea; }}
        .channel-name {{ display: inline-block; color: #667eea; text-decoration: none; font-weight: 500; margin-bottom: 8px; }}
        .video-meta {{ font-size: 0.9rem; color: #888; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-item {{ background: rgba(255,255,255,0.05); border-radius: 10px; padding: 15px; text-align: center; }}
        .stat-value {{ font-size: 1.3rem; font-weight: 600; color: #fff; }}
        .stat-label {{ font-size: 0.75rem; color: #888; margin-top: 5px; }}
        .badge {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
            margin-right: 8px;
            margin-bottom: 8px;
        }}
        .badge-monetized {{ background: rgba(40, 167, 69, 0.2); color: #28a745; border: 1px solid rgba(40, 167, 69, 0.3); }}
        .badge-possibly {{ background: rgba(255, 193, 7, 0.2); color: #ffc107; border: 1px solid rgba(255, 193, 7, 0.3); }}
        .badge-not {{ background: rgba(220, 53, 69, 0.2); color: #dc3545; border: 1px solid rgba(220, 53, 69, 0.3); }}
        .badge-niche {{ background: rgba(23, 162, 184, 0.2); color: #17a2b8; border: 1px solid rgba(23, 162, 184, 0.3); }}
        .action-links {{ margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap; }}
        .action-link {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 10px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 500;
        }}
        .action-link.secondary {{ background: rgba(255,255,255,0.1); }}
        .details-section {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.1);
            font-size: 0.85rem;
            color: #999;
        }}
        .footer {{ text-align: center; padding: 30px; margin-top: 40px; color: #666; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 YouTube Channel Hunter PRO</h1>
            <p>Report Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
        </div>
        
        {quota_warning}
        
        <div class="summary-grid">
            <div class="stat-card">
                <div class="number">{len(df)}</div>
                <div class="label">📊 Total Channels</div>
            </div>
            <div class="stat-card">
                <div class="number">{total_views:,.0f}</div>
                <div class="label">👁️ Total Views</div>
            </div>
            <div class="stat-card">
                <div class="number">{avg_virality:,.0f}/day</div>
                <div class="label">🔥 Avg Virality</div>
            </div>
            <div class="stat-card">
                <div class="number">{monetized_count}</div>
                <div class="label">💰 Monetized</div>
            </div>
            <div class="stat-card">
                <div class="number">${total_revenue:,.0f}</div>
                <div class="label">💵 Est. Revenue</div>
            </div>
        </div>
        
        <h2 class="section-title">🎬 Channel Results ({len(df)} found)</h2>
"""
    
    for idx, row in df.iterrows():
        if row['MonetizationScore'] >= 70:
            mon_class = "badge-monetized"
            mon_text = "🟢 Likely Monetized"
        elif row['MonetizationScore'] >= 50:
            mon_class = "badge-possibly"
            mon_text = "🟡 Possibly Monetized"
        else:
            mon_class = "badge-not"
            mon_text = "🔴 Not Monetized"
        
        niche = row.get('Niche', 'Other')
        est_revenue = row.get('EstRevenue', 0)
        
        html += f"""
        <div class="video-card">
            <div class="video-header">
                <img src="{row['Thumb']}" alt="Thumbnail" class="thumbnail" loading="lazy">
                <div class="video-info">
                    <h3 class="video-title">
                        <a href="{row['Link']}" target="_blank">{row['Title']}</a>
                    </h3>
                    <a href="{row['ChannelLink']}" target="_blank" class="channel-name">📺 {row['Channel']}</a>
                    <div class="video-meta">
                        🌍 {row['Country']} • 📅 Created: {row['ChCreated']} • 🎬 {row['TotalVideos']:,} videos
                    </div>
                </div>
            </div>
            <div class="stats-grid">
                <div class="stat-item"><div class="stat-value">{row['Views']:,}</div><div class="stat-label">👁️ Views</div></div>
                <div class="stat-item"><div class="stat-value">{row['Subs']:,}</div><div class="stat-label">👥 Subscribers</div></div>
                <div class="stat-item"><div class="stat-value">{row['Virality']:,}/day</div><div class="stat-label">🔥 Virality</div></div>
                <div class="stat-item"><div class="stat-value">{row['Engagement%']}%</div><div class="stat-label">💬 Engagement</div></div>
                <div class="stat-item"><div class="stat-value">{row['UploadsPerWeek']:.1f}/wk</div><div class="stat-label">📤 Uploads</div></div>
                <div class="stat-item"><div class="stat-value">${est_revenue:,.0f}</div><div class="stat-label">💵 Est. Revenue</div></div>
            </div>
            <div>
                <span class="badge {mon_class}">{mon_text} ({row['MonetizationScore']}%)</span>
                <span class="badge badge-niche">📂 {niche}</span>
            </div>
            <div class="details-section">
                ⏱️ Duration: {row['DurationStr']} ({row['Type']}) �� 👍 {row['Likes']:,} likes • 💬 {row['Comments']:,} comments • 📤 Uploaded: {row['Uploaded']} • 🔑 Keyword: {row['Keyword']}
            </div>
            <div class="action-links">
                <a href="{row['Link']}" target="_blank" class="action-link">▶️ Watch Video</a>
                <a href="{row['ChannelLink']}" target="_blank" class="action-link secondary">📺 View Channel</a>
            </div>
        </div>
"""
    
    html += """
        <div class="footer">
            <p>🎯 YouTube Channel Hunter PRO Report</p>
        </div>
    </div>
</body>
</html>
"""
    return html


# ------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------
def fetch_json(url, params, retries=2, api_type='search'):
    required = QUOTA_COSTS.get(api_type, 1)
    if st.session_state['quota_used'] + required > DAILY_QUOTA_LIMIT:
        return "QUOTA"
    
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                st.session_state['api_calls'] += 1
                st.session_state['quota_used'] += required
                return resp.json()
            if "quotaExceeded" in resp.text or resp.status_code == 403:
                st.session_state['quota_used'] = DAILY_QUOTA_LIMIT
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


def calculate_upload_frequency(created_date, total_videos):
    try:
        if not created_date or total_videos == 0:
            return 0, 0, "N/A"
        created = datetime.strptime(created_date[:19], "%Y-%m-%dT%H:%M:%S")
        days_active = max((datetime.utcnow() - created).days, 1)
        weeks_active = max(days_active / 7, 1)
        months_active = max(days_active / 30, 1)
        uploads_per_week = round(total_videos / weeks_active, 2)
        uploads_per_month = round(total_videos / months_active, 2)
        
        if uploads_per_week >= 7:
            schedule = f"🔥 Daily+ ({uploads_per_week:.1f}/week)"
        elif uploads_per_week >= 3:
            schedule = f"📈 Very Active ({uploads_per_week:.1f}/week)"
        elif uploads_per_week >= 1:
            schedule = f"✅ Regular ({uploads_per_week:.1f}/week)"
        elif uploads_per_week >= 0.5:
            schedule = f"📅 Bi-weekly"
        else:
            schedule = f"⏸️ Inactive"
        
        return uploads_per_week, uploads_per_month, schedule
    except:
        return 0, 0, "N/A"


def check_monetization_status(channel_data):
    reasons = []
    score = 0
    subs = channel_data.get("subs", 0)
    total_videos = channel_data.get("video_count", 0)
    created = channel_data.get("created", "")
    country = channel_data.get("country", "N/A")
    total_views = channel_data.get("total_views", 0)
    
    if subs >= 1000:
        score += 30
        reasons.append(f"✅ {subs:,} subs")
    elif subs >= 500:
        score += 10
        reasons.append(f"⏳ {subs:,} subs")
    else:
        reasons.append(f"❌ {subs:,} subs")
    
    if created:
        try:
            created_date = datetime.strptime(created[:19], "%Y-%m-%dT%H:%M:%S")
            days_old = (datetime.utcnow() - created_date).days
            if days_old >= 30:
                score += 15
                reasons.append(f"✅ {days_old}d old")
            else:
                reasons.append(f"❌ {days_old}d old")
        except:
            pass
    
    if country in MONETIZATION_COUNTRIES:
        score += 15
        reasons.append(f"✅ {country}")
    
    estimated_watch_hours = (total_views * 3.2) / 60
    if estimated_watch_hours >= 4000:
        score += 25
        reasons.append(f"✅ {estimated_watch_hours:,.0f} hrs")
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
        status = "🟠 CLOSE TO MONETIZATION"
    else:
        status = "🔴 NOT MONETIZED"
    
    return status, "High" if score >= 70 else "Low", score, reasons


# ============================================================
# SUPER RELAXED CHANNEL DETECTION - ANY NICHE WORKS NOW
# ============================================================
def detect_channel_type(channel_data, strictness="Relaxed"):
    """
    SUPER RELAXED detection - works for ANY niche
    News, Tech, Gaming, Cooking - EVERYTHING passes now!
    """
    reasons = []
    score = 60  # START HIGH - Most channels should pass!
    
    channel_name = channel_data.get("name", "").lower()
    description = channel_data.get("description", "").lower()
    video_count = channel_data.get("video_count", 0)
    subs = channel_data.get("subs", 0)
    
    # Active channel = PASS (this is main criteria now)
    if video_count >= 10:
        score += 25
        reasons.append("✅ Active channel")
    elif video_count >= 5:
        score += 15
        reasons.append("✅ Has videos")
    elif video_count >= 1:
        score += 10
        reasons.append("✅ Started")
    
    # Has subscribers = PASS
    if subs >= 1000:
        score += 15
        reasons.append("✅ 1K+ subs")
    elif subs >= 100:
        score += 10
        reasons.append("✅ Growing")
    
    # Bonus for matching keywords (but NOT required)
    name_matches = sum(1 for kw in FACELESS_INDICATORS if kw in channel_name)
    if name_matches >= 1:
        score += min(name_matches * 3, 10)
        reasons.append("✅ Keyword match")
    
    desc_matches = sum(1 for kw in FACELESS_DESCRIPTION_KEYWORDS if kw in description)
    if desc_matches >= 1:
        score += min(desc_matches * 2, 10)
    
    # SUPER LOW thresholds - almost everything passes!
    thresholds = {"Relaxed": 20, "Normal": 40, "Strict": 60}
    threshold = thresholds.get(strictness, 20)
    
    is_valid = score >= threshold
    
    if not is_valid:
        reasons.append("❌ Below threshold")
    
    return is_valid, min(score, 100), reasons


def get_video_type_label(duration):
    if duration < 60:
        return "Shorts"
    elif duration < 300:
        return "Medium"
    return "Long"


def format_number(num):
    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    elif num >= 1000:
        return f"{num/1000:.1f}K"
    return str(num)


def estimate_revenue(views, country, video_count):
    cpm = CPM_RATES.get(country, 1.0)
    monetized_views = views * 0.55
    revenue = (monetized_views / 1000) * cpm
    monthly_revenue = revenue / max((video_count / 30), 1) if video_count > 0 else 0
    return round(revenue, 2), round(monthly_revenue, 2)


# ============================================================
# EXPANDED NICHE DETECTION - MORE CATEGORIES
# ============================================================
def detect_niche(title, channel_name, keyword):
    """Detect niche - includes ALL categories now"""
    text = f"{title} {channel_name} {keyword}".lower()
    
    niches = {
        # NEWS - FIRST PRIORITY
        "News": ["news", "breaking", "headlines", "latest", "update", "report", 
                 "bulletin", "current events", "world news", "daily news", "live news"],
        
        # TECH
        "Tech": ["tech", "technology", "gadget", "phone", "smartphone", "laptop", 
                "computer", "review", "unboxing", "software", "app", "ai", "digital"],
        
        # GAMING
        "Gaming": ["gaming", "gameplay", "walkthrough", "gamer", "playthrough", 
                  "let's play", "game", "games", "xbox", "playstation", "nintendo"],
        
        # COOKING/FOOD
        "Cooking/Food": ["cooking", "recipe", "recipes", "food", "kitchen", "chef", 
                        "meal", "cuisine", "baking", "delicious", "tasty"],
        
        # FINANCE
        "Finance": ["finance", "money", "stock", "stocks", "crypto", "bitcoin",
                   "trading", "invest", "investing", "wealth", "economy", "market"],
        
        # Reddit/Stories
        "Reddit Stories": ["reddit", "aita", "am i the", "tifu", "entitled", "revenge"],
        
        # Horror/Scary
        "Horror/Scary": ["horror", "scary", "creepy", "nightmare", "paranormal", "ghost"],
        
        # True Crime
        "True Crime": ["true crime", "crime", "murder", "case", "investigation"],
        
        # Motivation
        "Motivation": ["motivation", "stoic", "stoicism", "mindset", "discipline", "success"],
        
        # Facts/Education
        "Facts/Education": ["facts", "explained", "documentary", "history", "science", "learn"],
        
        # Entertainment
        "Entertainment": ["entertainment", "celebrity", "movie", "movies", "film", "tv show"],
        
        # Compilation
        "Compilation": ["compilation", "best of", "funny", "fails", "moments"],
        
        # Mystery
        "Mystery": ["mystery", "mysteries", "unsolved", "conspiracy", "secret"],
        
        # Travel
        "Travel": ["travel", "vlog", "tour", "destination", "visit", "trip", "explore"],
        
        # Health/Fitness
        "Health/Fitness": ["fitness", "health", "workout", "exercise", "gym", "weight loss"],
        
        # Beauty/Fashion
        "Beauty/Fashion": ["beauty", "makeup", "fashion", "style", "skincare", "tutorial"],
        
        # Music
        "Music": ["music", "song", "cover", "remix", "beat", "melody", "singer", "lofi"],
        
        # Sports
        "Sports": ["sports", "football", "basketball", "soccer", "cricket", "match"],
        
        # DIY/Crafts
        "DIY/Crafts": ["diy", "craft", "handmade", "tutorial", "how to make"],
        
        # Pets/Animals
        "Pets/Animals": ["pet", "dog", "cat", "animal", "puppy", "kitten"],
        
        # Cars/Auto
        "Cars/Auto": ["car", "auto", "vehicle", "driving", "motor", "bike"],
        
        # Kids/Family
        "Kids/Family": ["kids", "children", "family", "parenting", "baby"],
        
        # Comedy
        "Comedy": ["comedy", "funny", "laugh", "humor", "joke", "prank"],
    }
    
    for niche, keywords in niches.items():
        if any(kw in text for kw in keywords):
            return niche
    return "General"


def batch_fetch_channels(channel_ids, api_key, cache):
    new_ids = [cid for cid in channel_ids if cid not in cache]
    if not new_ids:
        return cache, False
    
    for i in range(0, len(new_ids), 50):
        batch = new_ids[i:i+50]
        
        if st.session_state['quota_used'] + QUOTA_COSTS['channels'] > DAILY_QUOTA_LIMIT:
            return cache, True
        
        params = {
            "part": "snippet,statistics,brandingSettings,status",
            "id": ",".join(batch),
            "key": api_key
        }
        data = fetch_json(CHANNELS_URL, params, api_type='channels')
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
                "banner": brand_img.get("bannerExternalUrl", ""),
                "custom_url": sn.get("customUrl")
            }
    return cache, False


def search_videos_with_pagination(keyword, params, api_key, max_pages=2):
    all_items = []
    next_token = None
    
    for page in range(max_pages):
        if st.session_state['quota_used'] + QUOTA_COSTS['search'] > DAILY_QUOTA_LIMIT:
            return all_items, True
        
        search_params = params.copy()
        search_params["key"] = api_key
        if next_token:
            search_params["pageToken"] = next_token
        
        data = fetch_json(SEARCH_URL, search_params, api_type='search')
        if data == "QUOTA":
            return all_items, True
        if not data:
            break
        
        all_items.extend(data.get("items", []))
        next_token = data.get("nextPageToken")
        if not next_token:
            break
    
    return all_items, False


# ------------------------------------------------------------
# SIDEBAR SETTINGS - WITH FIXED DEFAULTS
# ------------------------------------------------------------
st.sidebar.header("⚙️ Settings")

# API Quota Display
st.sidebar.markdown("### 📊 API Quota Status")
quota_percentage = (st.session_state['quota_used'] / DAILY_QUOTA_LIMIT) * 100
quota_remaining = get_available_quota()

if quota_percentage < 50:
    quota_color = "🟢"
    quota_status = "Healthy"
elif quota_percentage < 80:
    quota_color = "🟡"
    quota_status = "Moderate"
else:
    quota_color = "🔴"
    quota_status = "Critical"

st.sidebar.markdown(f"""
{quota_color} **Status:** {quota_status}

📊 **Used:** {st.session_state['quota_used']:,} / {DAILY_QUOTA_LIMIT:,}

📈 **Available:** {quota_remaining:,} units

🔄 **API Calls:** {st.session_state['api_calls']}

🔍 **Max Searches Left:** ~{quota_remaining // QUOTA_COSTS['search']}
""")

st.sidebar.progress(min(quota_percentage / 100, 1.0))

if quota_percentage >= 90:
    st.sidebar.error("🚨 Quota almost exhausted! Wait until tomorrow.")
elif quota_percentage >= 70:
    st.sidebar.warning("⚠️ Quota running low!")

if st.sidebar.button("🔄 Reset Quota Counter"):
    st.session_state['quota_used'] = 0
    st.session_state['api_calls'] = 0
    st.rerun()

st.sidebar.markdown("---")

with st.sidebar.expander("📅 Time Filters", expanded=True):
    days = st.slider("Videos from last X days", 1, 90, 14)
    # ✅ FIX: Default to 2025 (index=0)
    channel_age = st.selectbox("Channel Created After", ["2025", "2024", "2023", "2022", "Any"], index=0)

with st.sidebar.expander("📊 View Filters", expanded=True):
    # ✅ FIX: Lower min views for news (news videos can have lower views initially)
    min_views = st.number_input("Min Views", min_value=1000, value=5000, step=1000)
    max_views = st.number_input("Max Views (0=No Limit)", min_value=0, value=0, step=10000)
    min_virality = st.slider("Min Virality (Views/Day)", 0, 10000, 300)

with st.sidebar.expander("👥 Subscriber Filters", expanded=True):
    # ✅ FIX: Min subs = 1000 by default
    min_subs = st.number_input("Min Subscribers", min_value=0, value=1000)
    max_subs = st.number_input("Max Subscribers", min_value=0, value=500000)

with st.sidebar.expander("🎬 Channel Video Count", expanded=True):
    st.markdown("**Filter by total videos on channel:**")
    min_channel_videos = st.number_input("Min Videos on Channel", min_value=0, max_value=500, value=0, step=10)
    max_channel_videos = st.number_input("Max Videos on Channel", min_value=0, max_value=500, value=100, step=10)
    if max_channel_videos == 0:
        st.info("ℹ️ Max 0 = No limit")

with st.sidebar.expander("🎬 Video Type", expanded=True):
    video_type = st.selectbox("Video Duration", ["All", "Long (5min+)", "Medium (1-5min)", "Shorts (<1min)"])

# ============================================================
# ✅ FIX: Faceless ON by default BUT super relaxed detection
# ============================================================
with st.sidebar.expander("🎯 Channel Detection", expanded=True):
    # ✅ FIX: Default TRUE but detection is super relaxed now
    faceless_only = st.checkbox("Smart Channel Filter (Recommended)", value=True, 
                                help="ON = Uses smart detection. OFF = Shows ALL channels")
    if faceless_only:
        faceless_strictness = st.select_slider("Detection Strictness", 
                                               options=["Relaxed", "Normal", "Strict"], 
                                               value="Relaxed")
    else:
        faceless_strictness = "Relaxed"
    
    st.success("💡 Relaxed mode: News, Tech, Gaming, ALL niches work!")

with st.sidebar.expander("💰 Monetization", expanded=False):
    monetized_only = st.checkbox("Only Likely Monetized", value=False)
    min_upload_frequency = st.slider("Min Uploads/Week", 0, 14, 0)

with st.sidebar.expander("🌍 Region Selection", expanded=False):
    # ✅ FIX: Premium only = TRUE by default
    premium_only = st.checkbox("Only Premium CPM Countries", value=True)
    
    st.markdown("**Select Regions to Search:**")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Top 3 Only", use_container_width=True):
            st.session_state['selected_regions'] = TOP_10_PREMIUM_COUNTRIES[:3]
    with col2:
        if st.button("Top 5 Only", use_container_width=True):
            st.session_state['selected_regions'] = TOP_10_PREMIUM_COUNTRIES[:5]
    
    # ✅ FIX: Default to Top 5 premium countries
    if 'selected_regions' not in st.session_state:
        st.session_state['selected_regions'] = TOP_10_PREMIUM_COUNTRIES[:5]
    
    search_regions = st.multiselect(
        "Regions",
        TOP_10_PREMIUM_COUNTRIES,
        default=st.session_state['selected_regions'],
        help="Premium CPM countries selected by default"
    )

with st.sidebar.expander("🔍 Search Options", expanded=False):
    search_orders = st.multiselect(
        "Search Order", 
        ["viewCount", "relevance", "date", "rating"], 
        default=["viewCount"],
        help="Fewer orders = Less quota usage"
    )
    use_pagination = st.checkbox("Use Pagination (2x quota)", value=False)
    # ✅ FIX: Quota save mode ON by default
    quota_save_mode = st.checkbox("🛡️ Quota Saving Mode", value=True, help="Automatically limits search scope")


# ------------------------------------------------------------
# KEYWORDS INPUT - GENERIC EXAMPLES FOR ANY NICHE
# ------------------------------------------------------------
st.markdown("### 🔑 Keywords")

# ✅ FIX: Generic default keywords - includes news!
default_keywords = """news today
tech review
motivation"""

keyword_input = st.text_area(
    "Enter Keywords (One per line - ANY topic works!)", 
    height=100, 
    value=default_keywords,
    help="News, Tech, Gaming, Cooking - ANYTHING works now!"
)

keywords_list = [kw.strip() for line in keyword_input.splitlines() for kw in line.split(",") if kw.strip()]
keywords_count = len(keywords_list)

# Example keywords section - EXPANDED
with st.expander("💡 Example Keywords for ANY Niche"):
    st.markdown("""
    **📰 News:**
    - `news today`, `breaking news`, `world news`, `daily news`, `headlines`
    
    **📱 Tech:**
    - `tech review`, `smartphone review`, `gadget unboxing`, `laptop review`
    
    **🎮 Gaming:**
    - `gaming`, `gameplay walkthrough`, `game review`, `lets play`
    
    **🍳 Cooking:**
    - `easy recipes`, `cooking tutorial`, `food recipes`, `kitchen tips`
    
    **💰 Finance:**
    - `stock market`, `crypto news`, `investing tips`, `money tips`
    
    **🎬 Entertainment:**
    - `movie review`, `celebrity news`, `tv show recap`
    
    **📚 Education:**
    - `explained`, `facts`, `how to`, `tutorial`, `learn`
    
    **💪 Motivation:**
    - `motivation`, `success mindset`, `self improvement`, `stoic wisdom`
    
    **😱 Horror/Stories:**
    - `scary stories`, `horror`, `creepy`, `reddit stories`
    
    **✈️ Travel:**
    - `travel vlog`, `destination guide`, `travel tips`
    """)

# ------------------------------------------------------------
# QUOTA PREVIEW
# ------------------------------------------------------------
st.markdown("---")
st.markdown("### 📊 Quota Preview")

preview_keywords = list(dict.fromkeys(keywords_list))[:5]
preview_regions = search_regions if search_regions else TOP_10_PREMIUM_COUNTRIES[:5]
preview_orders = search_orders if search_orders else ["viewCount"]

quota_estimate = calculate_required_quota(
    preview_keywords, 
    preview_regions, 
    preview_orders, 
    use_pagination
)

available = get_available_quota()
can_afford = can_afford_search(quota_estimate['total_quota'])

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("🔍 Search Calls", quota_estimate['search_calls'])
    st.caption(f"= {quota_estimate['search_quota']:,} quota units")

with col2:
    st.metric("📊 Total Quota Needed", f"{quota_estimate['total_quota']:,}")
    
with col3:
    if can_afford:
        st.metric("✅ Available", f"{available:,}")
        st.success("Enough quota!")
    else:
        st.metric("❌ Available", f"{available:,}")
        st.error("Not enough quota!")

with st.expander("📋 Quota Breakdown"):
    st.markdown(f"""
    | Component | Calls | Cost Each | Total |
    |-----------|-------|-----------|-------|
    | Search API | {quota_estimate['search_calls']} | 100 | {quota_estimate['search_quota']:,} |
    | Videos API | ~{quota_estimate['search_calls']} | 1 | ~{quota_estimate['video_quota']} |
    | Channels API | ~{quota_estimate['search_calls']} | 1 | ~{quota_estimate['channel_quota']} |
    | **TOTAL** | | | **{quota_estimate['total_quota']:,}** |
    
    ---
    
    **Current Settings:**
    - Keywords: {len(preview_keywords)} ({', '.join(preview_keywords[:3])}...)
    - Regions: {len(preview_regions)} ({', '.join(preview_regions[:3])}...)
    - Orders: {len(preview_orders)} ({', '.join(preview_orders)})
    - Pagination: {'ON' if use_pagination else 'OFF'}
    """)

if not can_afford:
    st.warning("⚠️ Quota kafi nahi hai! Neeche recommendations dekho:")
    
    smart_config = get_smart_search_config(
        preview_keywords, 
        preview_regions, 
        preview_orders, 
        available
    )
    
    if smart_config['reduced']:
        st.info(f"""
        **🛡️ Recommended Settings:**
        - Keywords: {len(smart_config['keywords'])} ({', '.join(smart_config['keywords'])})
        - Regions: {len(smart_config['regions'])} ({', '.join(smart_config['regions'])})
        - Orders: {len(smart_config['orders'])} ({', '.join(smart_config['orders'])})
        - Pagination: {'ON' if smart_config['use_pagination'] else 'OFF'}
        
        📌 Change: {smart_config['reduction']}
        """)


# ------------------------------------------------------------
# MAIN ACTION
# ------------------------------------------------------------
if st.button("🚀 SEARCH CHANNELS", type="primary", use_container_width=True):
    
    if not keyword_input.strip():
        st.error("⚠️ Keywords daal do!")
        st.stop()
    
    keywords = list(dict.fromkeys([kw.strip() for line in keyword_input.splitlines() for kw in line.split(",") if kw.strip()]))[:5]
    
    if len(keywords) == 0:
        st.error("⚠️ Koi valid keyword nahi mila!")
        st.stop()
    
    if not search_regions:
        search_regions = TOP_10_PREMIUM_COUNTRIES[:5]
    
    if not search_orders:
        search_orders = ["viewCount"]
    
    quota_estimate = calculate_required_quota(keywords, search_regions, search_orders, use_pagination)
    available = get_available_quota()
    
    final_keywords = keywords
    final_regions = search_regions
    final_orders = search_orders
    final_pagination = use_pagination
    
    if quota_save_mode and not can_afford_search(quota_estimate['total_quota']):
        smart_config = get_smart_search_config(keywords, search_regions, search_orders, available)
        final_keywords = smart_config['keywords']
        final_regions = smart_config['regions']
        final_orders = smart_config['orders']
        final_pagination = smart_config['use_pagination']
        
        st.warning(f"""
        🛡️ **Quota Saving Mode Active!**
        
        Original: {len(keywords)} keywords × {len(search_regions)} regions × {len(search_orders)} orders
        
        Reduced to: {len(final_keywords)} keywords × {len(final_regions)} regions × {len(final_orders)} orders
        
        📌 {smart_config['reduction']}
        """)
    
    st.info(f"🔍 Searching: {len(final_keywords)} keywords × {len(final_regions)} regions × {len(final_orders)} orders")
    
    all_results = []
    channel_cache = {}
    seen_videos = set()
    seen_channels = set()
    quota_exceeded = False
    
    published_after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    total_ops = len(final_keywords) * len(final_orders) * len(final_regions)
    current_op = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    quota_display = st.empty()
    
    stats = {"total_searched": 0, "final": 0, "keywords_completed": 0, "duplicates_skipped": 0}
    
    for kw in final_keywords:
        if quota_exceeded:
            break
            
        for order in final_orders:
            if quota_exceeded:
                break
                
            for region in final_regions:
                if quota_exceeded:
                    break
                
                if st.session_state['quota_used'] + QUOTA_COSTS['search'] > DAILY_QUOTA_LIMIT - QUOTA_SAFETY_BUFFER:
                    quota_exceeded = True
                    break
                    
                current_op += 1
                progress_bar.progress(current_op / total_ops)
                status_text.markdown(f"🔍 `{kw}` | {order} | {region}")
                quota_display.markdown(f"📊 Quota: {st.session_state['quota_used']:,} / {DAILY_QUOTA_LIMIT:,} ({(st.session_state['quota_used']/DAILY_QUOTA_LIMIT)*100:.1f}%)")
                
                search_params = {
                    "part": "snippet", "q": kw, "type": "video", "order": order,
                    "publishedAfter": published_after, "maxResults": 50,
                    "regionCode": region, "relevanceLanguage": "en", "safeSearch": "none"
                }
                
                if final_pagination:
                    items, quota_hit = search_videos_with_pagination(kw, search_params, API_KEY, 2)
                    if quota_hit:
                        quota_exceeded = True
                else:
                    data = fetch_json(SEARCH_URL, {**search_params, "key": API_KEY}, api_type='search')
                    if data == "QUOTA":
                        quota_exceeded = True
                        items = []
                    else:
                        items = data.get("items", []) if data else []
                
                if not items:
                    continue
                
                stats["total_searched"] += len(items)
                
                new_items = []
                for item in items:
                    vid = item.get("id", {}).get("videoId")
                    cid = item.get("snippet", {}).get("channelId")
                    
                    if not vid or not cid:
                        continue
                    
                    if vid in seen_videos:
                        continue
                    
                    if cid in seen_channels:
                        stats["duplicates_skipped"] += 1
                        continue
                    
                    seen_videos.add(vid)
                    new_items.append(item)
                
                if not new_items:
                    continue
                
                video_ids = [i["id"]["videoId"] for i in new_items]
                channel_ids = {i["snippet"]["channelId"] for i in new_items}
                
                video_stats = {}
                for i in range(0, len(video_ids), 50):
                    if quota_exceeded:
                        break
                    batch = video_ids[i:i+50]
                    vid_data = fetch_json(VIDEOS_URL, {"part": "statistics,contentDetails", "id": ",".join(batch), "key": API_KEY}, api_type='videos')
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
                
                if not quota_exceeded:
                    channel_cache, quota_hit = batch_fetch_channels(channel_ids, API_KEY, channel_cache)
                    if quota_hit:
                        quota_exceeded = True
                
                for item in new_items:
                    sn = item["snippet"]
                    vid = item["id"]["videoId"]
                    cid = sn["channelId"]
                    
                    if cid in seen_channels:
                        continue
                    
                    v_stats = video_stats.get(vid, {})
                    ch = channel_cache.get(cid, {})
                    
                    if not v_stats:
                        continue
                    
                    views = v_stats.get("views", 0)
                    likes = v_stats.get("likes", 0)
                    comments = v_stats.get("comments", 0)
                    duration = v_stats.get("duration", 0)
                    subs = ch.get("subs", 0)
                    total_videos = ch.get("video_count", 0)
                    total_channel_views = ch.get("total_views", 0)
                    
                    if views < min_views or (max_views > 0 and views > max_views):
                        continue
                    if not (min_subs <= subs <= max_subs):
                        continue
                    
                    if total_videos < min_channel_videos:
                        continue
                    if max_channel_videos > 0 and total_videos > max_channel_videos:
                        continue
                    
                    if channel_age != "Any":
                        created_year = int(ch.get("created", "2000")[:4]) if ch.get("created") else 2000
                        if created_year < int(channel_age):
                            continue
                    
                    # ✅ FIX: Super relaxed detection - almost everything passes!
                    if faceless_only:
                        is_valid, confidence, reasons = detect_channel_type(ch, faceless_strictness)
                        if not is_valid:
                            continue
                    else:
                        is_valid, confidence, reasons = True, 100, ["All channels included"]
                    
                    country = ch.get("country", "N/A")
                    if premium_only and country not in PREMIUM_COUNTRIES:
                        continue
                    
                    vtype = get_video_type_label(duration)
                    if video_type == "Long (5min+)" and duration < 300:
                        continue
                    if video_type == "Medium (1-5min)" and (duration < 60 or duration >= 300):
                        continue
                    if video_type == "Shorts (<1min)" and duration >= 60:
                        continue
                    
                    virality = calculate_virality_score(views, sn["publishedAt"])
                    if virality < min_virality:
                        continue
                    
                    uploads_per_week, uploads_per_month, schedule_desc = calculate_upload_frequency(ch.get("created", ""), total_videos)
                    if min_upload_frequency > 0 and uploads_per_week < min_upload_frequency:
                        continue
                    
                    monetization_status, _, monetization_score, monetization_reasons = check_monetization_status(ch)
                    if monetized_only and monetization_score < 50:
                        continue
                    
                    est_revenue, monthly_revenue = estimate_revenue(total_channel_views, country, total_videos)
                    niche = detect_niche(sn["title"], sn["channelTitle"], kw)
                    
                    seen_channels.add(cid)
                    stats["final"] += 1
                    
                    all_results.append({
                        "Title": sn["title"],
                        "Channel": sn["channelTitle"],
                        "ChannelID": cid,
                        "Subs": subs,
                        "TotalVideos": total_videos,
                        "TotalChannelViews": total_channel_views,
                        "UploadsPerWeek": uploads_per_week,
                        "UploadsPerMonth": uploads_per_month,
                        "UploadSchedule": schedule_desc,
                        "MonetizationStatus": monetization_status,
                        "MonetizationScore": monetization_score,
                        "MonetizationReasons": " | ".join(monetization_reasons),
                        "EstRevenue": est_revenue,
                        "MonthlyRevenue": monthly_revenue,
                        "Niche": niche,
                        "Views": views,
                        "Likes": likes,
                        "Comments": comments,
                        "Virality": virality,
                        "Engagement%": calculate_engagement_rate(views, likes, comments),
                        "SubViewRatio": round(views / max(subs, 1), 2),
                        "Uploaded": sn["publishedAt"][:10],
                        "ChCreated": ch.get("created", "")[:10] if ch.get("created") else "N/A",
                        "Country": country,
                        "Type": vtype,
                        "Duration": duration,
                        "DurationStr": f"{duration//60}:{duration%60:02d}",
                        "ChannelType": "Matched" if is_valid else "General",
                        "ChannelScore": confidence,
                        "Keyword": kw,
                        "Thumb": sn["thumbnails"]["high"]["url"],
                        "Link": f"https://www.youtube.com/watch?v={vid}",
                        "ChannelLink": f"https://www.youtube.com/channel/{cid}"
                    })
        
        stats["keywords_completed"] += 1
    
    progress_bar.empty()
    status_text.empty()
    quota_display.empty()
    
    st.markdown("### 📊 Final Quota Status")
    final_quota_pct = (st.session_state['quota_used'] / DAILY_QUOTA_LIMIT) * 100
    col1, col2, col3 = st.columns(3)
    col1.metric("Quota Used", f"{st.session_state['quota_used']:,}")
    col2.metric("Remaining", f"{DAILY_QUOTA_LIMIT - st.session_state['quota_used']:,}")
    col3.metric("Usage", f"{final_quota_pct:.1f}%")
    
    if quota_exceeded:
        st.warning(f"""
        ⚠️ **Quota Limit Reached!**
        
        - ✅ Keywords completed: {stats['keywords_completed']}/{len(final_keywords)}
        - ✅ Videos searched: {stats['total_searched']}
        - ✅ Channels found: {stats['final']}
        
        📌 Partial results neeche hain. Quota midnight Pacific Time pe reset hoga.
        """)
    
    st.markdown("### 📊 Search Statistics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Videos Searched", stats["total_searched"])
    col2.metric("Keywords Done", f"{stats['keywords_completed']}/{len(final_keywords)}")
    col3.metric("Channels Found", stats["final"])
    col4.metric("Duplicates Skipped", stats["duplicates_skipped"])
    
    if not all_results:
        st.warning("😔 Koi result nahi mila! Try these fixes:")
        st.markdown("""
        1. **Lower Min Views** to 1000
        2. **Lower Min Virality** to 100
        3. **Increase Days** to 30
        4. **Lower Min Subs** to 500
        5. **Try different keywords**
        6. **Uncheck "Smart Channel Filter"**
        """)
        st.stop()
    
    df = pd.DataFrame(all_results)
    df = df.sort_values("Views", ascending=False).reset_index(drop=True)
    
    st.success(f"🎉 **{len(df)} UNIQUE CHANNELS** found!")
    if not quota_exceeded:
        st.balloons()
    
    st.session_state['results_df'] = df
    st.session_state['stats'] = stats
    st.session_state['quota_exceeded'] = quota_exceeded
    
    col1, col2 = st.columns(2)
    with col1:
        sort_by = st.selectbox("Sort By", ["Views", "Virality", "Engagement%", "Subs", "TotalVideos", "MonetizationScore", "EstRevenue"])
    with col2:
        sort_order = st.selectbox("Order", ["Descending", "Ascending"])
    
    df = df.sort_values(by=sort_by, ascending=(sort_order == "Ascending"))
    
    for idx, r in df.iterrows():
        with st.container():
            st.markdown("---")
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### {r['Title']}")
                st.markdown(f"**📺 [{r['Channel']}]({r['ChannelLink']})** • 👥 {r['Subs']:,} • 🎬 {r['TotalVideos']} videos • 🌍 {r['Country']} • 📂 {r['Niche']}")
                st.markdown(f"📅 Created: {r['ChCreated']} • ⏰ {r['UploadSchedule']}")
                
                if "LIKELY" in r['MonetizationStatus']:
                    st.success(f"💰 {r['MonetizationStatus']} ({r['MonetizationScore']}%) | Est: ${r['EstRevenue']:,.0f}")
                elif "POSSIBLY" in r['MonetizationStatus']:
                    st.info(f"💰 {r['MonetizationStatus']} ({r['MonetizationScore']}%)")
                else:
                    st.warning(f"💰 {r['MonetizationStatus']} ({r['MonetizationScore']}%)")
                
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("👁️ Views", f"{r['Views']:,}")
                col_b.metric("🔥 Virality", f"{r['Virality']:,}/day")
                col_c.metric("💬 Engagement", f"{r['Engagement%']}%")
                col_d.metric("📈 Sub:View", f"{r['SubViewRatio']}x")
                
                st.markdown(f"⏱️ {r['DurationStr']} ({r['Type']}) • 👍 {r['Likes']:,} • 💬 {r['Comments']:,} • 📤 {r['Uploaded']}")
                
                st.markdown(f"🔑 `{r['Keyword']}` | [▶️ Watch]({r['Link']})")
            
            with col2:
                st.image(r["Thumb"], use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 📥 Download Results")
    
    download_cols = st.columns(3)
    
    with download_cols[0]:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download CSV",
            data=csv,
            file_name=f"channel_hunter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with download_cols[1]:
        html_report = generate_html_report(df, stats, quota_exceeded)
        st.download_button(
            "📥 Download HTML Report",
            data=html_report,
            file_name=f"channel_hunter_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html",
            use_container_width=True
        )
    
    with download_cols[2]:
        json_data = df.to_json(orient='records', indent=2)
        st.download_button(
            "📥 Download JSON",
            data=json_data,
            file_name=f"channel_hunter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with st.expander("📋 View Table"):
        st.dataframe(df[["Title", "Channel", "Views", "Virality", "Subs", "TotalVideos", "MonetizationScore", "Niche", "Country"]], use_container_width=True, height=400)

# Footer
st.markdown("---")
st.caption("Made with ❤️ | YouTube Channel Hunter PRO 2025 - ALL NICHES SUPPORTED!")
