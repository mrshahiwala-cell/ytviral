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
# HTML REPORT GENERATOR
# ------------------------------------------------------------
def generate_html_report(df, stats, quota_exceeded=False):
    """Generate beautiful HTML report with clickable links"""
    
    total_views = df['Views'].sum() if len(df) > 0 else 0
    avg_virality = df['Virality'].mean() if len(df) > 0 else 0
    monetized_count = len(df[df['MonetizationScore'] >= 70]) if len(df) > 0 else 0
    total_revenue = df['EstRevenue'].sum() if 'EstRevenue' in df.columns and len(df) > 0 else 0
    
    quota_warning = ""
    if quota_exceeded:
        quota_warning = """
        <div style="background: rgba(255, 193, 7, 0.2); border: 1px solid #ffc107; border-radius: 10px; padding: 15px; margin-bottom: 20px; text-align: center;">
            <strong>⚠️ API Quota Exhausted!</strong> - Partial results shown below. Full quota resets at midnight Pacific Time.
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
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
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
            transition: all 0.3s ease;
        }}
        .video-card:hover {{
            background: rgba(255,255,255,0.06);
            border-color: rgba(102, 126, 234, 0.3);
        }}
        .video-header {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .thumbnail {{ width: 200px; height: 112px; border-radius: 12px; object-fit: cover; flex-shrink: 0; }}
        .video-info {{ flex: 1; }}
        .video-title {{ font-size: 1.2rem; font-weight: 600; margin-bottom: 10px; color: #fff; }}
        .video-title a {{ color: #fff; text-decoration: none; }}
        .video-title a:hover {{ color: #667eea; }}
        .channel-name {{ display: inline-block; color: #667eea; text-decoration: none; font-weight: 500; margin-bottom: 8px; }}
        .channel-name:hover {{ text-decoration: underline; }}
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
        .badge-faceless {{ background: rgba(102, 126, 234, 0.2); color: #667eea; border: 1px solid rgba(102, 126, 234, 0.3); }}
        .badge-niche {{ background: rgba(23, 162, 184, 0.2); color: #17a2b8; border: 1px solid rgba(23, 162, 184, 0.3); }}
        .badge-shorts {{ background: rgba(255, 0, 80, 0.2); color: #ff0050; border: 1px solid rgba(255, 0, 80, 0.3); }}
        .badge-long {{ background: rgba(0, 150, 136, 0.2); color: #009688; border: 1px solid rgba(0, 150, 136, 0.3); }}
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
            transition: all 0.3s;
        }}
        .action-link:hover {{ transform: translateY(-2px); box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4); }}
        .action-link.secondary {{ background: rgba(255,255,255,0.1); }}
        .details-section {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.1);
            font-size: 0.85rem;
            color: #999;
        }}
        .footer {{ text-align: center; padding: 30px; margin-top: 40px; color: #666; font-size: 0.9rem; }}
        @media (max-width: 768px) {{
            .video-header {{ flex-direction: column; }}
            .thumbnail {{ width: 100%; height: auto; aspect-ratio: 16/9; }}
            .header h1 {{ font-size: 1.8rem; }}
        }}
        @media print {{
            body {{ background: white; color: black; }}
            .video-card {{ break-inside: avoid; border: 1px solid #ddd; }}
        }}
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
        
        faceless_text = "✅ Faceless" if row['Faceless'] == "YES" else "🤔 Maybe Faceless"
        niche = row.get('Niche', 'Other')
        est_revenue = row.get('EstRevenue', 0)
        shorts_count = row.get('ShortsCount', 'N/A')
        long_count = row.get('LongCount', 'N/A')
        
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
                    <div class="video-meta" style="margin-top: 5px;">
                        <span class="badge badge-shorts">🎬 Shorts: {shorts_count}</span>
                        <span class="badge badge-long">🎥 Long: {long_count}</span>
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
                <span class="badge badge-faceless">{faceless_text} ({row['FacelessScore']}%)</span>
                <span class="badge badge-niche">📂 {niche}</span>
            </div>
            <div class="details-section">
                ⏱️ Duration: {row['DurationStr']} ({row['Type']}) • 👍 {row['Likes']:,} likes • 💬 {row['Comments']:,} comments • 📤 Uploaded: {row['Uploaded']} • 🔑 Keyword: {row['Keyword']}
            </div>
            <div class="action-links">
                <a href="{row['Link']}" target="_blank" class="action-link">▶️ Watch Video</a>
                <a href="{row['ChannelLink']}" target="_blank" class="action-link secondary">📺 View Channel</a>
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
        "Mystery": ["mystery", "mysteries", "unsolved", "conspiracy"]
    }
    for niche, keywords in niches.items():
        if any(kw in text for kw in keywords):
            return niche
    return "Other"


def batch_fetch_channels(channel_ids, api_key, cache):
    """Returns (cache, quota_exceeded)"""
    new_ids = [cid for cid in channel_ids if cid not in cache]
    if not new_ids:
        return cache, False
    
    for i in range(0, len(new_ids), 50):
        batch = new_ids[i:i+50]
        params = {
            "part": "snippet,statistics,brandingSettings,status",
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
                "banner": brand_img.get("bannerExternalUrl", ""),
                "custom_url": sn.get("customUrl")
            }
    return cache, False


# ------------------------------------------------------------
# 🆕 NEW: FETCH CHANNEL VIDEOS TO COUNT SHORTS VS LONG
# ------------------------------------------------------------
def fetch_channel_video_counts(channel_id, api_key):
    """Fetch recent videos from channel and count shorts vs long"""
    try:
        # Get channel's recent videos (up to 50)
        search_params = {
            "part": "id",
            "channelId": channel_id,
            "type": "video",
            "maxResults": 50,
            "order": "date",
            "key": api_key
        }
        
        data = fetch_json(SEARCH_URL, search_params)
        if data == "QUOTA" or not data:
            return None, None, True if data == "QUOTA" else False
        
        video_ids = [item["id"]["videoId"] for item in data.get("items", []) if item.get("id", {}).get("videoId")]
        
        if not video_ids:
            return 0, 0, False
        
        # Get video durations
        vid_params = {
            "part": "contentDetails",
            "id": ",".join(video_ids),
            "key": api_key
        }
        
        vid_data = fetch_json(VIDEOS_URL, vid_params)
        if vid_data == "QUOTA":
            return None, None, True
        if not vid_data:
            return 0, 0, False
        
        shorts_count = 0
        long_count = 0
        
        for v in vid_data.get("items", []):
            duration = parse_duration(v["contentDetails"].get("duration", ""))
            if duration < 60:
                shorts_count += 1
            elif duration >= 60:
                long_count += 1
        
        return shorts_count, long_count, False
        
    except Exception as e:
        return 0, 0, False


def search_videos_with_pagination(keyword, params, api_key, max_pages=2):
    """Returns (items, quota_exceeded)"""
    all_items = []
    next_token = None
    
    for page in range(max_pages):
        search_params = params.copy()
        search_params["key"] = api_key
        if next_token:
            search_params["pageToken"] = next_token
        
        data = fetch_json(SEARCH_URL, search_params)
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

st.sidebar.info("⚡ **API Quota Saving Mode**: Maximum 5 keywords allowed!")

with st.sidebar.expander("📅 Time Filters", expanded=True):
    days = st.slider("Videos from last X days", 1, 90, 14)
    channel_age = st.selectbox("Channel Created After", ["2025", "2024", "2023", "2022", "Any"], index=1)

with st.sidebar.expander("📊 View Filters", expanded=True):
    min_views = st.number_input("Min Views", min_value=1000, value=10000, step=1000)
    max_views = st.number_input("Max Views (0=No Limit)", min_value=0, value=0, step=10000)
    min_virality = st.slider("Min Virality (Views/Day)", 0, 10000, 500)

with st.sidebar.expander("👥 Subscriber Filters", expanded=True):
    min_subs = st.number_input("Min Subscribers", min_value=0, value=100)
    max_subs = st.number_input("Max Subscribers", min_value=0, value=500000)

with st.sidebar.expander("🎬 Channel Video Count Filter", expanded=True):
    st.markdown("**Filter channels by total videos uploaded:**")
    min_channel_videos = st.number_input("Min Videos on Channel", min_value=0, value=0, step=10)
    max_channel_videos = st.number_input("Max Videos on Channel", min_value=0, value=300, step=10)
    st.caption("💡 0-300 range helps find newer channels")

with st.sidebar.expander("📹 Video Type Filter", expanded=True):
    st.markdown("**Filter by Shorts vs Long videos:**")
    video_type = st.selectbox(
        "Video Duration Type", 
        ["All", "Long Only (5min+)", "Medium (1-5min)", "Shorts Only (<1min)", "Long + Medium (No Shorts)"],
        help="Shorts = under 60 seconds, Long = 5+ minutes"
    )

with st.sidebar.expander("🎯 Faceless Detection", expanded=True):
    faceless_only = st.checkbox("Only Faceless Channels", value=True)
    faceless_strictness = st.select_slider("Detection Strictness", options=["Relaxed", "Normal", "Strict"], value="Normal")

with st.sidebar.expander("💰 Monetization", expanded=False):
    monetized_only = st.checkbox("Only Likely Monetized", value=False)
    min_upload_frequency = st.slider("Min Uploads/Week", 0, 14, 0)

with st.sidebar.expander("🌍 Region", expanded=False):
    premium_only = st.checkbox("Only Premium CPM Countries", value=False)
    search_regions = st.multiselect("Search Regions", ["US", "GB", "CA", "AU", "IN", "PH"], default=["US"])

with st.sidebar.expander("🔍 Search Settings", expanded=False):
    search_orders = st.multiselect("Search Order", ["viewCount", "relevance", "date", "rating"], default=["viewCount"])
    use_pagination = st.checkbox("Use Pagination (uses more quota)", value=False)
    fetch_shorts_long_count = st.checkbox("Fetch Shorts/Long counts per channel", value=True, help="Shows exact shorts vs long count for each channel (uses extra API quota)")
    st.caption("💡 Pagination OFF = saves quota")


# ------------------------------------------------------------
# KEYWORDS
# ------------------------------------------------------------
st.markdown("### 🔑 Keywords (Max 5)")

default_keywords = """reddit stories
aita
true horror stories
motivation
top 10 facts"""

keyword_input = st.text_area("Enter Keywords (One per line, MAX 5)", height=150, value=default_keywords)

# Quick templates
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("📖 Reddit"):
        keyword_input = "reddit stories\naita\npro revenge\nnuclear revenge\nmalicious compliance"
with col2:
    if st.button("👻 Horror"):
        keyword_input = "true horror stories\nscary stories\ncreepypasta\nmr nightmare\nparanormal"
with col3:
    if st.button("💪 Motivation"):
        keyword_input = "stoicism\nmotivation\nself improvement\nmarcus aurelius\nsigma mindset"
with col4:
    if st.button("📺 Cash Cow"):
        keyword_input = "top 10\nfacts about\nexplained\ndocumentary\ntrue crime"


# ------------------------------------------------------------
# MAIN ACTION
# ------------------------------------------------------------
if st.button("🚀 HUNT FACELESS VIRAL VIDEOS", type="primary", use_container_width=True):
    
    if not keyword_input.strip():
        st.error("⚠️ Keywords daal do!")
        st.stop()
    
    # Limit to 5 keywords
    all_keywords = list(dict.fromkeys([kw.strip() for line in keyword_input.splitlines() for kw in line.split(",") if kw.strip()]))
    
    if len(all_keywords) > 5:
        keywords = all_keywords[:5]
        st.info(f"🔍 Using first 5 keywords: {', '.join(keywords)}")
    else:
        keywords = all_keywords
        st.info(f"🔍 Using {len(keywords)} keywords: {', '.join(keywords)}")
    
    all_results = []
    channel_cache = {}
    channel_shorts_long_cache = {}  # Cache for shorts/long counts
    seen_videos = set()
    quota_exceeded = False
    
    published_after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    total_ops = len(keywords) * len(search_orders) * len(search_regions)
    current_op = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    quota_warning = st.empty()
    
    stats = {"total_searched": 0, "final": 0, "keywords_completed": 0, "filtered_by_video_count": 0, "filtered_by_type": 0}
    
    # Main search loop
    for kw in keywords:
        if quota_exceeded:
            break
            
        for order in search_orders:
            if quota_exceeded:
                break
                
            for region in search_regions:
                if quota_exceeded:
                    break
                    
                current_op += 1
                progress_bar.progress(current_op / total_ops)
                status_text.markdown(f"🔍 `{kw}` | {order} | {region}")
                
                search_params = {
                    "part": "snippet", "q": kw, "type": "video", "order": order,
                    "publishedAfter": published_after, "maxResults": 50,
                    "regionCode": region, "relevanceLanguage": "en", "safeSearch": "none"
                }
                
                if use_pagination:
                    items, quota_hit = search_videos_with_pagination(kw, search_params, API_KEY, 2)
                    if quota_hit:
                        quota_exceeded = True
                        quota_warning.warning("⚠️ API Quota khatam ho gaya!")
                else:
                    data = fetch_json(SEARCH_URL, {**search_params, "key": API_KEY})
                    if data == "QUOTA":
                        quota_exceeded = True
                        quota_warning.warning("⚠️ API Quota khatam ho gaya!")
                        items = []
                    else:
                        items = data.get("items", []) if data else []
                
                if not items:
                    continue
                
                stats["total_searched"] += len(items)
                
                new_items = [item for item in items if item.get("id", {}).get("videoId") and item["id"]["videoId"] not in seen_videos]
                for item in new_items:
                    seen_videos.add(item["id"]["videoId"])
                
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
                    vid_data = fetch_json(VIDEOS_URL, {"part": "statistics,contentDetails", "id": ",".join(batch), "key": API_KEY})
                    if vid_data == "QUOTA":
                        quota_exceeded = True
                        quota_warning.warning("⚠️ API Quota khatam ho gaya!")
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
                        quota_warning.warning("⚠️ API Quota khatam ho gaya!")
                
                # Process videos
                for item in new_items:
                    sn = item["snippet"]
                    vid = item["id"]["videoId"]
                    cid = sn["channelId"]
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
                    
                    # Filters
                    if views < min_views or (max_views > 0 and views > max_views):
                        continue
                    if not (min_subs <= subs <= max_subs):
                        continue
                    
                    # Channel video count filter
                    if max_channel_videos > 0:
                        if total_videos < min_channel_videos or total_videos > max_channel_videos:
                            stats["filtered_by_video_count"] += 1
                            continue
                    elif total_videos < min_channel_videos:
                        stats["filtered_by_video_count"] += 1
                        continue
                    
                    if channel_age != "Any":
                        created_year = int(ch.get("created", "2000")[:4]) if ch.get("created") else 2000
                        if created_year < int(channel_age):
                            continue
                    
                    if faceless_only:
                        is_faceless, confidence, reasons = detect_faceless_advanced(ch, faceless_strictness)
                        if not is_faceless:
                            continue
                    else:
                        is_faceless, confidence, reasons = detect_faceless_advanced(ch, faceless_strictness)
                    
                    country = ch.get("country", "N/A")
                    if premium_only and country not in PREMIUM_COUNTRIES:
                        continue
                    
                    # Video type filter
                    vtype = get_video_type_label(duration)
                    
                    if video_type == "Long Only (5min+)" and duration < 300:
                        stats["filtered_by_type"] += 1
                        continue
                    elif video_type == "Medium (1-5min)" and (duration < 60 or duration >= 300):
                        stats["filtered_by_type"] += 1
                        continue
                    elif video_type == "Shorts Only (<1min)" and duration >= 60:
                        stats["filtered_by_type"] += 1
                        continue
                    elif video_type == "Long + Medium (No Shorts)" and duration < 60:
                        stats["filtered_by_type"] += 1
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
                    
                    # 🆕 Fetch shorts/long counts for this channel (if enabled and not already cached)
                    shorts_count = "N/A"
                    long_count = "N/A"
                    
                    if fetch_shorts_long_count and not quota_exceeded:
                        if cid in channel_shorts_long_cache:
                            shorts_count, long_count = channel_shorts_long_cache[cid]
                        else:
                            status_text.markdown(f"📊 Fetching video breakdown for `{sn['channelTitle'][:30]}...`")
                            s_count, l_count, quota_hit = fetch_channel_video_counts(cid, API_KEY)
                            if quota_hit:
                                quota_exceeded = True
                                quota_warning.warning("⚠️ API Quota khatam ho gaya!")
                            elif s_count is not None:
                                shorts_count = s_count
                                long_count = l_count
                                channel_shorts_long_cache[cid] = (shorts_count, long_count)
                    
                    est_revenue, monthly_revenue = estimate_revenue(total_channel_views, country, total_videos)
                    niche = detect_niche(sn["title"], sn["channelTitle"], kw)
                    
                    stats["final"] += 1
                    
                    all_results.append({
                        "Title": sn["title"],
                        "Channel": sn["channelTitle"],
                        "ChannelID": cid,
                        "Subs": subs,
                        "TotalVideos": total_videos,
                        "ShortsCount": shorts_count,
                        "LongCount": long_count,
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
                        "Faceless": "YES" if is_faceless else "MAYBE",
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
    
    # Show quota warning if exceeded
    if quota_exceeded:
        st.warning(f"""
        ⚠️ **API Quota Khatam Ho Gaya!**
        
        - ✅ Keywords completed: **{stats['keywords_completed']}/{len(keywords)}**
        - ✅ Videos searched: **{stats['total_searched']}**
        - ✅ Results found: **{stats['final']}**
        
        📌 Quota midnight Pacific Time pe reset hota hai.
        """)
    
    # Stats
    st.markdown("### 📊 Statistics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Searched", stats["total_searched"])
    col2.metric("Keywords Done", f"{stats['keywords_completed']}/{len(keywords)}")
    col3.metric("Results Found", stats["final"])
    col4.metric("Filtered (Video Count)", stats["filtered_by_video_count"])
    
    if stats["filtered_by_type"] > 0:
        st.caption(f"📹 {stats['filtered_by_type']} videos filtered by type (Shorts/Long)")
    
    # Show results if any
    if not all_results:
        st.warning("😔 Koi result nahi mila! Filters adjust karo ya kal phir try karo.")
        st.stop()
    
    df = pd.DataFrame(all_results)
    df = df.sort_values("Views", ascending=False).drop_duplicates(subset="ChannelID", keep="first").reset_index(drop=True)
    
    if quota_exceeded:
        st.success(f"🎉 **{len(df)} PARTIAL RESULTS** (Quota limit tak jo mile)")
    else:
        st.success(f"🎉 **{len(df)} FACELESS VIRAL VIDEOS** found!")
        st.balloons()
    
    # Store in session state
    st.session_state['results_df'] = df
    st.session_state['stats'] = stats
    st.session_state['quota_exceeded'] = quota_exceeded
    
    # Video Type Summary
    st.markdown("### 📹 Video Type Breakdown (Current Video)")
    type_counts = df['Type'].value_counts()
    type_cols = st.columns(3)
    with type_cols[0]:
        shorts_count = type_counts.get('Shorts', 0)
        st.metric("🎬 Shorts (<1min)", shorts_count)
    with type_cols[1]:
        medium_count = type_counts.get('Medium', 0)
        st.metric("📺 Medium (1-5min)", medium_count)
    with type_cols[2]:
        long_count = type_counts.get('Long', 0)
        st.metric("🎥 Long (5min+)", long_count)
    
    # Sorting
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
                st.markdown(f"**📺 [{r['Channel']}]({r['ChannelLink']})** • 👥 {r['Subs']:,} • 🎬 {r['TotalVideos']} videos • 🌍 {r['Country']} • 📂 {r['Niche']}")
                
                # 🆕 SHORTS & LONG COUNT DISPLAY
                shorts_display = r['ShortsCount'] if r['ShortsCount'] != "N/A" else "?"
                long_display = r['LongCount'] if r['LongCount'] != "N/A" else "?"
                st.markdown(f"📅 Created: {r['ChCreated']} • ⏰ {r['UploadSchedule']} • 🎬 **Shorts: {shorts_display}** | 🎥 **Long: {long_display}**")
                
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
                
                type_emoji = "🎬" if r['Type'] == "Shorts" else "📺" if r['Type'] == "Medium" else "🎥"
                st.markdown(f"⏱️ {r['DurationStr']} **{type_emoji} {r['Type']}** • 👍 {r['Likes']:,} • 💬 {r['Comments']:,} • 📤 {r['Uploaded']}")
                
                if r['Faceless'] == "YES":
                    st.success(f"✅ Faceless ({r['FacelessScore']}%)")
                else:
                    st.info(f"🤔 Maybe Faceless ({r['FacelessScore']}%)")
                
                st.markdown(f"🔑 `{r['Keyword']}` | [▶️ Watch]({r['Link']})")
            
            with col2:
                st.image(r["Thumb"], use_container_width=True)
    
    # Download Section
    st.markdown("---")
    st.markdown("### 📥 Download Results")
    
    if quota_exceeded:
        st.info("📌 Ye partial results hain - quota khatam hone se pehle jo mile.")
    
    download_cols = st.columns(3)
    
    with download_cols[0]:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download CSV",
            data=csv,
            file_name=f"faceless_viral_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with download_cols[1]:
        html_report = generate_html_report(df, stats, quota_exceeded)
        st.download_button(
            "📥 Download HTML Report",
            data=html_report,
            file_name=f"faceless_viral_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html",
            use_container_width=True
        )
    
    with download_cols[2]:
        json_data = df.to_json(orient='records', indent=2)
        st.download_button(
            "📥 Download JSON",
            data=json_data,
            file_name=f"faceless_viral_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    # Table View
    with st.expander("📋 View Table"):
        st.dataframe(df[["Title", "Channel", "Views", "Virality", "Subs", "TotalVideos", "ShortsCount", "LongCount", "Type", "MonetizationScore", "Niche", "Country", "Faceless"]], use_container_width=True, height=400)

# Footer
st.markdown("---")
st.caption("Made with ❤️ for Muhammed Rizwan Qamar | Faceless Viral Hunter PRO 2025")
