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
st.set_page_config(page_title="🎯 Faceless Viral Hunter PRO", layout="wide")
st.title("🎯 Faceless Viral Hunter PRO")
st.markdown("**Reddit Stories, AITA, Horror, Cash Cow, Motivation - FACELESS channels ka king!**")

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

# ALL SEARCHABLE REGIONS (for broader search)
ALL_REGIONS = ['US', 'GB', 'CA', 'AU', 'IN', 'DE', 'FR', 'BR', 'MX', 'JP', 'KR', 'ES', 'IT', 'NL', 'SE', 'NO', 'PL', 'RU', 'PH', 'ID', 'PK', 'ZA', 'NG', 'AE', 'SA']

# ------------------------------------------------------------
# FACELESS DETECTION KEYWORDS
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


# ------------------------------------------------------------
# QUOTA FUNCTIONS
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
    
    opt4_combos = len(keywords) * len(regions) * len(search_orders)
    opt4_quota = opt4_combos * (QUOTA_COSTS['search'] + 5)
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
    <title>Faceless Viral Hunter PRO Report - {datetime.now().strftime("%Y-%m-%d")}</title>
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
        }}
        .header h1 {{ font-size: 2.5rem; font-weight: 700; margin-bottom: 10px; }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.05);
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
        }}
        .stat-card .label {{ font-size: 0.9rem; color: #888; margin-top: 5px; }}
        .video-card {{
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.08);
        }}
        .video-header {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .thumbnail {{ width: 200px; height: 112px; border-radius: 12px; object-fit: cover; }}
        .video-title {{ font-size: 1.2rem; font-weight: 600; color: #fff; }}
        .video-title a {{ color: #fff; text-decoration: none; }}
        .video-title a:hover {{ color: #667eea; }}
        .channel-name {{ color: #667eea; text-decoration: none; font-weight: 500; }}
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
        }}
        .badge-monetized {{ background: rgba(40, 167, 69, 0.2); color: #28a745; }}
        .badge-possibly {{ background: rgba(255, 193, 7, 0.2); color: #ffc107; }}
        .badge-not {{ background: rgba(220, 53, 69, 0.2); color: #dc3545; }}
        .badge-faceless {{ background: rgba(102, 126, 234, 0.2); color: #667eea; }}
        .badge-niche {{ background: rgba(23, 162, 184, 0.2); color: #17a2b8; }}
        .action-link {{
            display: inline-flex;
            padding: 10px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            margin-right: 10px;
            margin-top: 10px;
        }}
        .footer {{ text-align: center; padding: 30px; margin-top: 40px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Faceless Viral Hunter PRO</h1>
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
        
        <h2 style="margin-bottom: 25px;">🎬 Channel Results ({len(df)} found)</h2>
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
        
        faceless_text = "✅ Faceless" if row['Faceless'] == "YES" else "🤔 Maybe Faceless"
        niche = row.get('Niche', 'Other')
        est_revenue = row.get('EstRevenue', 0)
        
        html += f"""
        <div class="video-card">
            <div class="video-header">
                <img src="{row['Thumb']}" alt="Thumbnail" class="thumbnail">
                <div>
                    <h3 class="video-title">
                        <a href="{row['Link']}" target="_blank">{row['Title']}</a>
                    </h3>
                    <a href="{row['ChannelLink']}" target="_blank" class="channel-name">📺 {row['Channel']}</a>
                    <p style="color: #888; margin-top: 8px;">🌍 {row['Country']} • 📅 Created: {row['ChCreated']} • 🎬 {row['TotalVideos']:,} videos</p>
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
                <span class="badge badge-faceless">{faceless_text} ({row['FacelessScore']}%)</span>
                <span class="badge badge-niche">📂 {niche}</span>
            </div>
            <div>
                <a href="{row['Link']}" target="_blank" class="action-link">▶️ Watch Video</a>
                <a href="{row['ChannelLink']}" target="_blank" class="action-link">📺 View Channel</a>
            </div>
        </div>
"""
    
    html += """
        <div class="footer">
            <p>🎯 Faceless Viral Hunter PRO Report</p>
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


def detect_faceless_advanced(channel_data, strictness="Normal"):
    reasons = []
    score = 0
    profile_url = channel_data.get("profile", "")
    banner_url = channel_data.get("banner", "")
    channel_name = channel_data.get("name", "").lower()
    description = channel_data.get("description", "").lower()
    
    if "default.jpg" in profile_url or "s88-c-k-c0x00ffffff-no-rj" in profile_url:
        score += 30
        reasons.append("Default pic")
    
    if not banner_url:
        score += 20
        reasons.append("No banner")
    
    name_matches = sum(1 for kw in FACELESS_INDICATORS if kw in channel_name)
    if name_matches >= 1:
        score += min(name_matches * 15, 30)
        reasons.append(f"Name match")
    
    desc_matches = sum(1 for kw in FACELESS_DESCRIPTION_KEYWORDS if kw in description)
    if desc_matches >= 1:
        score += min(desc_matches * 10, 25)
        reasons.append(f"Desc match")
    
    thresholds = {"Relaxed": 20, "Normal": 35, "Strict": 55}
    threshold = thresholds.get(strictness, 35)
    
    return score >= threshold, min(score, 100), reasons


def get_video_type_label(duration):
    if duration < 60:
        return "Shorts"
    elif duration < 300:
        return "Medium"
    return "Long"


def estimate_revenue(views, country, video_count):
    cpm = CPM_RATES.get(country, 1.0)
    monetized_views = views * 0.55
    revenue = (monetized_views / 1000) * cpm
    monthly_revenue = revenue / max((video_count / 30), 1) if video_count > 0 else 0
    return round(revenue, 2), round(monthly_revenue, 2)


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
        "Tech": ["tech", "technology", "gadget", "review", "unboxing"],
        "Music": ["music", "song", "lyrics", "remix", "cover"],
        "Sports": ["sports", "football", "basketball", "soccer", "cricket"],
        "News": ["news", "breaking", "update", "latest"],
        "Entertainment": ["entertainment", "celebrity", "movie", "film"],
        "Lifestyle": ["lifestyle", "vlog", "daily", "routine"],
        "Food": ["food", "cooking", "recipe", "kitchen"],
        "Travel": ["travel", "tour", "visit", "explore"]
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
# SIDEBAR SETTINGS
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

🔍 **Max Searches Left:** ~{quota_remaining // QUOTA_COSTS['search']}
""")

st.sidebar.progress(min(quota_percentage / 100, 1.0))

if st.sidebar.button("🔄 Reset Quota Counter"):
    st.session_state['quota_used'] = 0
    st.session_state['api_calls'] = 0
    st.rerun()

st.sidebar.markdown("---")

# ============= IMPORTANT CHANGES FOR BETTER RESULTS =============

with st.sidebar.expander("📅 Time Filters", expanded=True):
    days = st.slider("Videos from last X days", 1, 365, 30)  # INCREASED to 30 days
    channel_age = st.selectbox("Channel Created After", ["Any", "2025", "2024", "2023", "2022"], index=0)  # DEFAULT: Any

with st.sidebar.expander("📊 View Filters", expanded=True):
    min_views = st.number_input("Min Views", min_value=0, value=1000, step=500)  # REDUCED from 10000 to 1000
    max_views = st.number_input("Max Views (0=No Limit)", min_value=0, value=0, step=10000)
    min_virality = st.slider("Min Virality (Views/Day)", 0, 10000, 50)  # REDUCED from 500 to 50

with st.sidebar.expander("👥 Subscriber Filters", expanded=True):
    min_subs = st.number_input("Min Subscribers", min_value=0, value=0)  # REDUCED from 100 to 0
    max_subs = st.number_input("Max Subscribers", min_value=0, value=10000000)  # INCREASED

with st.sidebar.expander("🎬 Channel Video Count", expanded=False):
    st.markdown("**Filter by total videos on channel:**")
    min_channel_videos = st.number_input("Min Videos on Channel", min_value=0, max_value=10000, value=0, step=10)
    max_channel_videos = st.number_input("Max Videos on Channel (0=No Limit)", min_value=0, max_value=10000, value=0, step=10)

with st.sidebar.expander("🎬 Video Type", expanded=False):
    video_type = st.selectbox("Video Duration", ["All", "Long (5min+)", "Medium (1-5min)", "Shorts (<1min)"])

with st.sidebar.expander("🎯 Faceless Detection", expanded=True):
    faceless_only = st.checkbox("Only Faceless Channels", value=False)  # CHANGED TO FALSE - IMPORTANT!
    faceless_strictness = st.select_slider("Detection Strictness", options=["Relaxed", "Normal", "Strict"], value="Relaxed")  # CHANGED TO Relaxed

with st.sidebar.expander("💰 Monetization", expanded=False):
    monetized_only = st.checkbox("Only Likely Monetized", value=False)
    min_upload_frequency = st.slider("Min Uploads/Week", 0, 14, 0)

with st.sidebar.expander("🌍 Region Selection", expanded=False):
    premium_only = st.checkbox("Only Premium CPM Countries", value=False)
    
    st.markdown("**Select Regions to Search:**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🌐 Global", use_container_width=True):
            st.session_state['selected_regions'] = ALL_REGIONS[:5]
    with col2:
        if st.button("💎 Premium", use_container_width=True):
            st.session_state['selected_regions'] = TOP_10_PREMIUM_COUNTRIES[:3]
    with col3:
        if st.button("🇺🇸 US Only", use_container_width=True):
            st.session_state['selected_regions'] = ['US']
    
    if 'selected_regions' not in st.session_state:
        st.session_state['selected_regions'] = ['US', 'GB', 'IN']  # Default: US, UK, India
    
    search_regions = st.multiselect(
        "Regions",
        ALL_REGIONS,
        default=st.session_state['selected_regions'],
        help="Fewer regions = Less quota usage"
    )

with st.sidebar.expander("🔍 Search Options", expanded=False):
    search_orders = st.multiselect(
        "Search Order", 
        ["viewCount", "relevance", "date", "rating"], 
        default=["viewCount", "relevance"],  # Added relevance for better results
        help="More orders = Better coverage but more quota"
    )
    use_pagination = st.checkbox("Use Pagination (2x quota)", value=False)
    quota_save_mode = st.checkbox("🛡️ Quota Saving Mode", value=True)


# ------------------------------------------------------------
# KEYWORDS INPUT
# ------------------------------------------------------------
st.markdown("### 🔑 Keywords (Koi Bhi Keyword Dalo!)")

st.info("💡 **Tip:** Ab aap koi bhi keyword daal sakte ho - tech, music, gaming, news, etc. Accurate results milenge!")

default_keywords = """tech review
gaming
news"""

keyword_input = st.text_area("Enter Keywords (One per line)", height=100, value=default_keywords, 
                             help="Koi bhi keyword dalo - ab sab kuch search ho jayega!")

keywords_list = [kw.strip() for line in keyword_input.splitlines() for kw in line.split(",") if kw.strip()]
keywords_count = len(keywords_list)

st.markdown(f"📝 **{keywords_count} keywords** ready for search")

# ------------------------------------------------------------
# QUOTA PREVIEW
# ------------------------------------------------------------
st.markdown("---")
st.markdown("### 📊 Quota Preview")

preview_keywords = list(dict.fromkeys(keywords_list))[:10]  # Allow more keywords
preview_regions = search_regions if search_regions else ['US', 'GB', 'IN']
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

with col2:
    st.metric("📊 Total Quota Needed", f"{quota_estimate['total_quota']:,}")
    
with col3:
    if can_afford:
        st.metric("✅ Available", f"{available:,}")
        st.success("Enough quota!")
    else:
        st.metric("❌ Available", f"{available:,}")
        st.error("Not enough quota!")


# ------------------------------------------------------------
# MAIN ACTION
# ------------------------------------------------------------
if st.button("🚀 HUNT VIRAL VIDEOS", type="primary", use_container_width=True):
    
    if not keyword_input.strip():
        st.error("⚠️ Keywords daal do!")
        st.stop()
    
    keywords = list(dict.fromkeys([kw.strip() for line in keyword_input.splitlines() for kw in line.split(",") if kw.strip()]))[:10]
    
    if len(keywords) == 0:
        st.error("⚠️ Koi valid keyword nahi mila!")
        st.stop()
    
    if not search_regions:
        search_regions = ['US', 'GB', 'IN']
    
    if not search_orders:
        search_orders = ["viewCount", "relevance"]
    
    # Check quota availability
    quota_estimate = calculate_required_quota(keywords, search_regions, search_orders, use_pagination)
    available = get_available_quota()
    
    # Apply quota saving mode if enabled
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
        
        st.warning(f"🛡️ Quota Saving Mode Active! Reduced to: {len(final_keywords)} keywords × {len(final_regions)} regions")
    
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
    results_counter = st.empty()
    
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
                status_text.markdown(f"🔍 **Searching:** `{kw}` | {order} | {region}")
                quota_display.markdown(f"📊 Quota: {st.session_state['quota_used']:,} / {DAILY_QUOTA_LIMIT:,}")
                results_counter.markdown(f"✅ **Found so far:** {stats['final']} channels")
                
                search_params = {
                    "part": "snippet", 
                    "q": kw, 
                    "type": "video", 
                    "order": order,
                    "publishedAfter": published_after, 
                    "maxResults": 50,
                    "regionCode": region, 
                    "safeSearch": "none"  # REMOVED relevanceLanguage for broader results
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
                
                # Filter duplicates
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
                
                # Fetch video stats
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
                
                # Fetch channel stats
                if not quota_exceeded:
                    channel_cache, quota_hit = batch_fetch_channels(channel_ids, API_KEY, channel_cache)
                    if quota_hit:
                        quota_exceeded = True
                
                # Process videos
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
                    
                    # Apply filters - RELAXED
                    if views < min_views:
                        continue
                    if max_views > 0 and views > max_views:
                        continue
                    if subs < min_subs:
                        continue
                    if max_subs > 0 and subs > max_subs:
                        continue
                    
                    if min_channel_videos > 0 and total_videos < min_channel_videos:
                        continue
                    if max_channel_videos > 0 and total_videos > max_channel_videos:
                        continue
                    
                    # Channel age filter
                    if channel_age != "Any":
                        created_year = int(ch.get("created", "2000")[:4]) if ch.get("created") else 2000
                        if created_year < int(channel_age):
                            continue
                    
                    # Faceless detection - NOW OPTIONAL
                    is_faceless, confidence, reasons = detect_faceless_advanced(ch, faceless_strictness)
                    if faceless_only and not is_faceless:
                        continue
                    
                    country = ch.get("country", "N/A")
                    if premium_only and country not in PREMIUM_COUNTRIES:
                        continue
                    
                    # Video type filter
                    vtype = get_video_type_label(duration)
                    if video_type == "Long (5min+)" and duration < 300:
                        continue
                    if video_type == "Medium (1-5min)" and (duration < 60 or duration >= 300):
                        continue
                    if video_type == "Shorts (<1min)" and duration >= 60:
                        continue
                    
                    # Virality filter
                    virality = calculate_virality_score(views, sn["publishedAt"])
                    if virality < min_virality:
                        continue
                    
                    # Upload frequency filter
                    uploads_per_week, uploads_per_month, schedule_desc = calculate_upload_frequency(ch.get("created", ""), total_videos)
                    if min_upload_frequency > 0 and uploads_per_week < min_upload_frequency:
                        continue
                    
                    # Monetization check
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
                        "Faceless": "YES" if is_faceless else "NO",
                        "FacelessScore": confidence,
                        "FacelessReasons": ", ".join(reasons) if reasons else "N/A",
                        "Keyword": kw,
                        "Thumb": sn["thumbnails"]["high"]["url"],
                        "Link": f"https://www.youtube.com/watch?v={vid}",
                        "ChannelLink": f"https://www.youtube.com/channel/{cid}"
                    })
        
        stats["keywords_completed"] += 1
    
    progress_bar.empty()
    status_text.empty()
    quota_display.empty()
    results_counter.empty()
    
    # Final quota status
    st.markdown("### 📊 Search Complete!")
    final_quota_pct = (st.session_state['quota_used'] / DAILY_QUOTA_LIMIT) * 100
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Videos Searched", stats["total_searched"])
    col2.metric("Keywords Done", f"{stats['keywords_completed']}/{len(final_keywords)}")
    col3.metric("Channels Found", stats["final"])
    col4.metric("Quota Used", f"{final_quota_pct:.1f}%")
    
    if quota_exceeded:
        st.warning(f"⚠️ **Quota Limit Reached!** Partial results shown. Reset at midnight PT.")
    
    if not all_results:
        st.warning("""
        😔 **Koi result nahi mila!** 
        
        **Try these:**
        1. 📉 Min Views kam karo (e.g., 500)
        2. 📅 Days badao (e.g., 60 days)
        3. 🌍 More regions add karo
        4. 🔤 Different keywords try karo
        5. ✅ Make sure "Only Faceless" is OFF
        """)
        st.stop()
    
    df = pd.DataFrame(all_results)
    df = df.sort_values("Views", ascending=False).reset_index(drop=True)
    
    st.success(f"🎉 **{len(df)} CHANNELS** found!")
    st.balloons()
    
    # Sorting options
    col1, col2 = st.columns(2)
    with col1:
        sort_by = st.selectbox("Sort By", ["Views", "Virality", "Engagement%", "Subs", "TotalVideos", "MonetizationScore", "EstRevenue"])
    with col2:
        sort_order = st.selectbox("Order", ["Descending", "Ascending"])
    
    df = df.sort_values(by=sort_by, ascending=(sort_order == "Ascending"))
    
    # Display results
    for idx, r in df.iterrows():
        with st.container():
            st.markdown("---")
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### {r['Title']}")
                st.markdown(f"**📺 [{r['Channel']}]({r['ChannelLink']})** • 👥 {r['Subs']:,} subs • 🎬 {r['TotalVideos']} videos • 🌍 {r['Country']} • 📂 {r['Niche']}")
                
                if "LIKELY" in r['MonetizationStatus']:
                    st.success(f"💰 {r['MonetizationStatus']} ({r['MonetizationScore']}%)")
                elif "POSSIBLY" in r['MonetizationStatus']:
                    st.info(f"💰 {r['MonetizationStatus']} ({r['MonetizationScore']}%)")
                else:
                    st.warning(f"💰 {r['MonetizationStatus']} ({r['MonetizationScore']}%)")
                
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("👁️ Views", f"{r['Views']:,}")
                col_b.metric("🔥 Virality", f"{r['Virality']:,}/day")
                col_c.metric("💬 Engagement", f"{r['Engagement%']}%")
                col_d.metric("📤 Uploads", f"{r['UploadsPerWeek']:.1f}/wk")
                
                st.markdown(f"⏱️ {r['DurationStr']} ({r['Type']}) • 👍 {r['Likes']:,} • 💬 {r['Comments']:,} • 📤 {r['Uploaded']}")
                
                if r['Faceless'] == "YES":
                    st.success(f"✅ Faceless Channel ({r['FacelessScore']}%)")
                
                st.markdown(f"🔑 `{r['Keyword']}` | [▶️ Watch Video]({r['Link']}) | [📺 View Channel]({r['ChannelLink']})")
            
            with col2:
                st.image(r["Thumb"], use_container_width=True)
    
    # Download section
    st.markdown("---")
    st.markdown("### 📥 Download Results")
    
    download_cols = st.columns(3)
    
    with download_cols[0]:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download CSV",
            data=csv,
            file_name=f"viral_videos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with download_cols[1]:
        html_report = generate_html_report(df, stats, quota_exceeded)
        st.download_button(
            "📥 Download HTML Report",
            data=html_report,
            file_name=f"viral_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html",
            use_container_width=True
        )
    
    with download_cols[2]:
        json_data = df.to_json(orient='records', indent=2)
        st.download_button(
            "📥 Download JSON",
            data=json_data,
            file_name=f"viral_videos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with st.expander("📋 View Full Table"):
        st.dataframe(df[["Title", "Channel", "Views", "Virality", "Subs", "TotalVideos", "Niche", "Country", "Faceless"]], use_container_width=True, height=400)

# Footer
st.markdown("---")
st.caption("Made with ❤️ for Muhammed Rizwan Qamar | Faceless Viral Hunter PRO 2025")
