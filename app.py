import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import re

# ============================================================
# APP CONFIG
# ============================================================
st.set_page_config(page_title="🎯 YouTube Channel Hunter PRO", layout="wide")
st.title("🎯 YouTube Channel Hunter PRO")
st.markdown("**Faceless Channels + Har Niche ke Channels - Sab Milenge!**")

API_KEY = st.secrets["YOUTUBE_API_KEY"]

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

# ============================================================
# SESSION STATE
# ============================================================
if 'api_calls' not in st.session_state:
    st.session_state['api_calls'] = 0
if 'quota_used' not in st.session_state:
    st.session_state['quota_used'] = 0
if 'last_reset' not in st.session_state:
    st.session_state['last_reset'] = datetime.now().date()

QUOTA_COSTS = {'search': 100, 'videos': 1, 'channels': 1}
DAILY_QUOTA_LIMIT = 10000
QUOTA_SAFETY_BUFFER = 500

def check_quota_reset():
    today = datetime.now().date()
    if st.session_state['last_reset'] < today:
        st.session_state['quota_used'] = 0
        st.session_state['api_calls'] = 0
        st.session_state['last_reset'] = today

check_quota_reset()

# ============================================================
# COUNTRIES & CPM DATA
# ============================================================
TOP_10_PREMIUM_COUNTRIES = ['US', 'AU', 'NO', 'CH', 'CA', 'GB', 'DE', 'LU', 'SE', 'NL']

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

# ============================================================
# FACELESS KEYWORDS
# ============================================================
FACELESS_NAME_KEYWORDS = [
    "reddit", "stories", "story", "aita", "askreddit", "confession",
    "entitled", "revenge", "petty", "malicious", "nuclear",
    "horror", "scary", "creepy", "nightmare", "paranormal", "ghost",
    "true crime", "crime", "murder", "case", "unsolved", "mystery",
    "motivation", "motivational", "stoic", "stoicism", "wisdom", "mindset",
    "discipline", "success", "sigma", "alpha", "masculine",
    "facts", "fact", "explained", "education", "documentary", "history",
    "compilation", "top 10", "top 5", "top 20", "best of", "ranking",
    "ai", "generated", "automated", "voice", "tts", "narrator",
    "gameplay", "walkthrough", "no commentary", "longplay",
    "quiz", "trivia", "test", "challenge",
    "sleep", "relaxing", "asmr", "ambient", "meditation",
]

FACELESS_DESC_KEYWORDS = [
    "ai generated", "text to speech", "tts", "voice over", "narration",
    "automated", "compilation", "no face", "faceless", "anonymous",
    "reddit stories", "true stories", "real stories",
    "facts about", "things you", "did you know",
    "top 10", "top 5", "best of", "worst of",
    "motivational", "inspirational", "life lessons",
    "horror stories", "scary stories", "creepy stories",
    "no commentary", "gameplay", "walkthrough",
]

# ============================================================
# NICHE CATEGORIES
# ============================================================
NICHE_CATEGORIES = {
    "Reddit Stories": ["reddit", "aita", "askreddit", "tifu", "entitled", "revenge"],
    "Horror/Scary": ["horror", "scary", "creepy", "nightmare", "paranormal", "ghost"],
    "True Crime": ["true crime", "crime", "murder", "case", "unsolved"],
    "Motivation": ["motivation", "stoic", "stoicism", "mindset", "discipline", "sigma"],
    "Facts/Education": ["facts", "explained", "documentary", "history", "science"],
    "Compilation": ["compilation", "best of", "fails", "moments", "highlights"],
    "Top Lists": ["top 10", "top 5", "ranking", "countdown", "best", "worst"],
    "Mystery": ["mystery", "mysteries", "unsolved", "conspiracy", "secret"],
    "Quiz/Trivia": ["quiz", "trivia", "test", "challenge", "guess"],
    "Sleep/ASMR": ["sleep", "asmr", "relaxing", "calm", "ambient", "meditation"],
    "News": ["news", "breaking", "headlines", "latest", "update", "report"],
    "Tech": ["tech", "technology", "gadget", "smartphone", "laptop", "review", "unboxing"],
    "Gaming": ["gaming", "gameplay", "walkthrough", "gamer", "playthrough", "game"],
    "Cooking/Food": ["cooking", "recipe", "food", "kitchen", "chef", "meal", "baking"],
    "Finance": ["finance", "money", "stock", "crypto", "trading", "invest", "wealth"],
    "Entertainment": ["entertainment", "celebrity", "movie", "film", "tv show"],
    "Travel": ["travel", "vlog", "tour", "destination", "explore", "adventure"],
    "Health/Fitness": ["fitness", "health", "workout", "exercise", "gym", "yoga"],
    "Beauty/Fashion": ["beauty", "makeup", "fashion", "style", "skincare"],
    "Music": ["music", "song", "cover", "remix", "beat", "lofi"],
    "Sports": ["sports", "football", "basketball", "soccer", "cricket", "nfl"],
    "DIY/Crafts": ["diy", "craft", "handmade", "tutorial", "how to make"],
    "Pets/Animals": ["pet", "dog", "cat", "animal", "puppy", "kitten"],
    "Cars/Auto": ["car", "auto", "vehicle", "driving", "motor", "supercar"],
    "Comedy": ["comedy", "funny", "laugh", "humor", "joke", "prank", "meme"],
    "Kids/Family": ["kids", "children", "family", "parenting", "baby", "toys"],
    "Vlogs": ["vlog", "daily", "day in my life", "routine", "lifestyle"],
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def get_available_quota():
    return DAILY_QUOTA_LIMIT - st.session_state['quota_used'] - QUOTA_SAFETY_BUFFER

def fetch_json(url, params, api_type='search'):
    required = QUOTA_COSTS.get(api_type, 1)
    if st.session_state['quota_used'] + required > DAILY_QUOTA_LIMIT:
        return "QUOTA"
    
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            st.session_state['api_calls'] += 1
            st.session_state['quota_used'] += required
            return resp.json()
        if "quotaExceeded" in resp.text or resp.status_code == 403:
            st.session_state['quota_used'] = DAILY_QUOTA_LIMIT
            return "QUOTA"
    except Exception as e:
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

def calculate_virality(views, published_at):
    try:
        pub_date = datetime.strptime(published_at[:19], "%Y-%m-%dT%H:%M:%S")
        days = max((datetime.utcnow() - pub_date).days, 1)
        return round(views / days, 2)
    except:
        return 0

def calculate_engagement(views, likes, comments):
    if views == 0:
        return 0
    return round(((likes + comments * 2) / views) * 100, 2)

def get_upload_frequency(created_date, total_videos):
    try:
        if not created_date or total_videos == 0:
            return 0, "N/A"
        created = datetime.strptime(created_date[:19], "%Y-%m-%dT%H:%M:%S")
        weeks = max((datetime.utcnow() - created).days / 7, 1)
        per_week = round(total_videos / weeks, 2)
        
        if per_week >= 7:
            return per_week, f"🔥 Daily+ ({per_week:.1f}/wk)"
        elif per_week >= 3:
            return per_week, f"📈 Active ({per_week:.1f}/wk)"
        elif per_week >= 1:
            return per_week, f"✅ Regular ({per_week:.1f}/wk)"
        else:
            return per_week, f"⏸️ Slow ({per_week:.1f}/wk)"
    except:
        return 0, "N/A"

def check_monetization(channel_data):
    score = 0
    subs = channel_data.get("subs", 0)
    total_videos = channel_data.get("video_count", 0)
    created = channel_data.get("created", "")
    country = channel_data.get("country", "N/A")
    total_views = channel_data.get("total_views", 0)
    
    if subs >= 1000:
        score += 30
    elif subs >= 500:
        score += 15
    
    if created:
        try:
            days_old = (datetime.utcnow() - datetime.strptime(created[:19], "%Y-%m-%dT%H:%M:%S")).days
            if days_old >= 30:
                score += 15
        except:
            pass
    
    if country in MONETIZATION_COUNTRIES:
        score += 15
    
    watch_hours = (total_views * 3.2) / 60
    if watch_hours >= 4000:
        score += 25
    elif watch_hours >= 2000:
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

def estimate_revenue(views, country):
    cpm = CPM_RATES.get(country, 1.0)
    return round((views * 0.55 / 1000) * cpm, 2)

def get_video_type(duration):
    if duration < 60:
        return "Shorts"
    elif duration < 300:
        return "Medium"
    return "Long"

def is_faceless_channel(channel_data):
    name = channel_data.get("name", "").lower()
    desc = channel_data.get("description", "").lower()
    
    score = 0
    matched = []
    
    for kw in FACELESS_NAME_KEYWORDS:
        if kw in name:
            score += 15
            matched.append(f"Name: {kw}")
            if score >= 30:
                break
    
    for kw in FACELESS_DESC_KEYWORDS:
        if kw in desc:
            score += 10
            matched.append(f"Desc: {kw}")
            if score >= 50:
                break
    
    video_count = channel_data.get("video_count", 0)
    if video_count >= 100:
        score += 15
        matched.append("100+ videos")
    elif video_count >= 50:
        score += 10
        matched.append("50+ videos")
    
    return score >= 25, score, matched[:5]

def detect_niche(title, channel_name, keyword):
    text = f"{title} {channel_name} {keyword}".lower()
    
    for niche, keywords in NICHE_CATEGORIES.items():
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
            "part": "snippet,statistics,brandingSettings",
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
            
            cache[c["id"]] = {
                "name": sn.get("title", ""),
                "subs": int(stats.get("subscriberCount", 0)),
                "total_views": int(stats.get("viewCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
                "created": sn.get("publishedAt", ""),
                "country": sn.get("country", "N/A"),
                "description": sn.get("description", ""),
            }
    return cache, False

# ============================================================
# HTML REPORT
# ============================================================
def generate_html_report(df, search_mode):
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>YouTube Channel Hunter Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #e4e4e4; padding: 20px; }}
        .header {{ text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 15px; margin-bottom: 30px; }}
        .header h1 {{ font-size: 2rem; margin-bottom: 10px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .stat {{ background: rgba(255,255,255,0.05); padding: 20px; border-radius: 10px; text-align: center; }}
        .stat .num {{ font-size: 1.8rem; font-weight: bold; color: #667eea; }}
        .stat .label {{ font-size: 0.9rem; color: #888; }}
        .card {{ background: rgba(255,255,255,0.03); border-radius: 12px; padding: 20px; margin-bottom: 15px; border: 1px solid rgba(255,255,255,0.1); }}
        .card-header {{ display: flex; gap: 15px; margin-bottom: 15px; }}
        .thumb {{ width: 160px; height: 90px; border-radius: 8px; object-fit: cover; }}
        .title {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 8px; }}
        .title a {{ color: #fff; text-decoration: none; }}
        .channel {{ color: #667eea; font-weight: 500; }}
        .meta {{ font-size: 0.85rem; color: #888; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 10px; margin: 15px 0; }}
        .metric {{ background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; text-align: center; }}
        .metric .val {{ font-size: 1.1rem; font-weight: 600; }}
        .metric .lbl {{ font-size: 0.7rem; color: #888; }}
        .badge {{ display: inline-block; padding: 4px 10px; border-radius: 15px; font-size: 0.75rem; margin-right: 5px; }}
        .badge-green {{ background: rgba(40,167,69,0.2); color: #28a745; }}
        .badge-blue {{ background: rgba(23,162,184,0.2); color: #17a2b8; }}
        .badge-purple {{ background: rgba(102,126,234,0.2); color: #667eea; }}
        .links a {{ color: #667eea; text-decoration: none; margin-right: 15px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 YouTube Channel Hunter Report</h1>
        <p>Mode: {search_mode} | Generated: {datetime.now().strftime("%B %d, %Y")}</p>
    </div>
    
    <div class="stats">
        <div class="stat"><div class="num">{len(df)}</div><div class="label">Channels</div></div>
        <div class="stat"><div class="num">{df['Views'].sum():,.0f}</div><div class="label">Total Views</div></div>
        <div class="stat"><div class="num">{df['Virality'].mean():,.0f}/day</div><div class="label">Avg Virality</div></div>
        <div class="stat"><div class="num">${df['EstRevenue'].sum():,.0f}</div><div class="label">Est. Revenue</div></div>
    </div>
"""
    
    for _, r in df.iterrows():
        html += f"""
    <div class="card">
        <div class="card-header">
            <img src="{r['Thumb']}" class="thumb">
            <div>
                <div class="title"><a href="{r['Link']}" target="_blank">{r['Title']}</a></div>
                <div class="channel">📺 <a href="{r['ChannelLink']}" target="_blank">{r['Channel']}</a></div>
                <div class="meta">🌍 {r['Country']} • 📅 {r['ChCreated']} • 🎬 {r['TotalVideos']} videos</div>
            </div>
        </div>
        <div class="metrics">
            <div class="metric"><div class="val">{r['Views']:,}</div><div class="lbl">Views</div></div>
            <div class="metric"><div class="val">{r['Subs']:,}</div><div class="lbl">Subs</div></div>
            <div class="metric"><div class="val">{r['Virality']:,}/d</div><div class="lbl">Virality</div></div>
            <div class="metric"><div class="val">${r['EstRevenue']:,.0f}</div><div class="lbl">Revenue</div></div>
        </div>
        <div>
            <span class="badge badge-green">{r['MonetizationStatus']}</span>
            <span class="badge badge-blue">📂 {r['Niche']}</span>
        </div>
        <div class="links">
            <a href="{r['Link']}" target="_blank">▶️ Watch</a>
            <a href="{r['ChannelLink']}" target="_blank">📺 Channel</a>
        </div>
    </div>
"""
    
    html += "</body></html>"
    return html

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.header("⚙️ Settings")

# Quota
st.sidebar.markdown("### 📊 Quota Status")
quota_pct = (st.session_state['quota_used'] / DAILY_QUOTA_LIMIT) * 100
available_quota = get_available_quota()

if quota_pct < 50:
    st.sidebar.success(f"🟢 {st.session_state['quota_used']:,}/{DAILY_QUOTA_LIMIT:,}")
elif quota_pct < 80:
    st.sidebar.warning(f"🟡 {st.session_state['quota_used']:,}/{DAILY_QUOTA_LIMIT:,}")
else:
    st.sidebar.error(f"🔴 {st.session_state['quota_used']:,}/{DAILY_QUOTA_LIMIT:,}")

st.sidebar.progress(min(quota_pct / 100, 1.0))

if st.sidebar.button("🔄 Reset Quota"):
    st.session_state['quota_used'] = 0
    st.session_state['api_calls'] = 0
    st.rerun()

st.sidebar.markdown("---")

# Search Mode
st.sidebar.markdown("### 🎯 Search Mode")
search_mode = st.sidebar.radio(
    "Channel Type",
    ["🤖 Faceless Only", "🌐 All Channels", "🎯 Smart (Both)"],
    index=2
)

st.sidebar.markdown("---")

# Filters
with st.sidebar.expander("📅 Time Filters", expanded=True):
    days = st.slider("Videos from last X days", 1, 90, 14)
    channel_age = st.selectbox("Channel Created After", ["2025", "2024", "2023", "2022", "Any"], index=0)

with st.sidebar.expander("📊 View Filters", expanded=True):
    min_views = st.number_input("Min Views", min_value=100, value=5000, step=1000)
    max_views = st.number_input("Max Views (0=No Limit)", min_value=0, value=0, step=10000)
    min_virality = st.slider("Min Virality", 0, 5000, 200)

with st.sidebar.expander("👥 Subscriber Filters", expanded=True):
    min_subs = st.number_input("Min Subscribers", min_value=0, value=1000)
    max_subs = st.number_input("Max Subscribers", min_value=0, value=500000)

with st.sidebar.expander("🎬 Channel Videos", expanded=False):
    min_videos = st.number_input("Min Videos", min_value=0, value=5)
    max_videos = st.number_input("Max Videos (0=No Limit)", min_value=0, value=0)

with st.sidebar.expander("⏱️ Video Duration", expanded=False):
    video_type = st.selectbox("Duration", ["All", "Long (5min+)", "Medium (1-5min)", "Shorts (<1min)"])

with st.sidebar.expander("💰 Monetization", expanded=False):
    monetized_only = st.checkbox("Only Likely Monetized", value=False)

with st.sidebar.expander("🌍 Region", expanded=False):
    premium_only = st.checkbox("Premium CPM Countries Only", value=True)
    
    if 'selected_regions' not in st.session_state:
        st.session_state['selected_regions'] = TOP_10_PREMIUM_COUNTRIES[:5]
    
    search_regions = st.multiselect(
        "Regions",
        TOP_10_PREMIUM_COUNTRIES,
        default=st.session_state['selected_regions']
    )

with st.sidebar.expander("🔍 Options", expanded=False):
    search_order = st.selectbox("Sort", ["viewCount", "relevance", "date"])
    quota_save = st.checkbox("🛡️ Quota Save Mode", value=True)

# ============================================================
# MAIN CONTENT
# ============================================================
st.markdown("### 🔑 Keywords")

if search_mode == "🤖 Faceless Only":
    default_kw = "reddit stories\nscary stories\nmotivation\ntop 10 facts"
elif search_mode == "🌐 All Channels":
    default_kw = "news today\ntech review\ngaming\ncooking recipes"
else:
    default_kw = "reddit stories\nnews today\ntech review\nmotivation"

keyword_input = st.text_area("Keywords (one per line)", value=default_kw, height=120)
keywords = [kw.strip() for kw in keyword_input.splitlines() if kw.strip()][:5]

with st.expander("💡 Keyword Examples"):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**🤖 Faceless:**\n- reddit stories\n- scary stories\n- motivation\n- top 10 facts")
    with col2:
        st.markdown("**📰 News/Tech:**\n- news today\n- tech review\n- smartphone\n- crypto")
    with col3:
        st.markdown("**🎮 Other:**\n- gaming\n- cooking\n- fitness\n- travel vlog")

# Quota estimate
regions_count = len(search_regions) if search_regions else 5
estimated_quota = len(keywords) * regions_count * 100 + 50
st.markdown(f"📊 **Quota:** ~{estimated_quota:,} needed | {available_quota:,} available")

# ============================================================
# SEARCH
# ============================================================
if st.button("🚀 SEARCH CHANNELS", type="primary", use_container_width=True):
    
    if not keywords:
        st.error("❌ Enter keywords!")
        st.stop()
    
    if not search_regions:
        search_regions = TOP_10_PREMIUM_COUNTRIES[:3]
    
    if quota_save and estimated_quota > available_quota:
        keywords = keywords[:2]
        search_regions = search_regions[:2]
        st.warning("🛡️ Reduced search to save quota")
    
    st.info(f"🔍 {len(keywords)} keywords × {len(search_regions)} regions")
    
    all_results = []
    channel_cache = {}
    seen_channels = set()
    quota_exceeded = False
    
    published_after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    progress = st.progress(0)
    status = st.empty()
    
    total_ops = len(keywords) * len(search_regions)
    current_op = 0
    
    for kw in keywords:
        if quota_exceeded:
            break
            
        for region in search_regions:
            if quota_exceeded:
                break
            
            current_op += 1
            progress.progress(current_op / total_ops)
            status.markdown(f"🔍 `{kw}` | {region}")
            
            params = {
                "part": "snippet",
                "q": kw,
                "type": "video",
                "order": search_order,
                "publishedAfter": published_after,
                "maxResults": 50,
                "regionCode": region,
                "relevanceLanguage": "en",
                "key": API_KEY
            }
            
            data = fetch_json(SEARCH_URL, params, 'search')
            if data == "QUOTA":
                quota_exceeded = True
                break
            if not data:
                continue
            
            items = data.get("items", [])
            if not items:
                continue
            
            video_ids = []
            channel_ids = set()
            
            for item in items:
                vid = item.get("id", {}).get("videoId")
                cid = item.get("snippet", {}).get("channelId")
                if vid and cid:
                    video_ids.append(vid)
                    channel_ids.add(cid)
            
            video_stats = {}
            for i in range(0, len(video_ids), 50):
                batch = video_ids[i:i+50]
                vid_data = fetch_json(VIDEOS_URL, {
                    "part": "statistics,contentDetails",
                    "id": ",".join(batch),
                    "key": API_KEY
                }, 'videos')
                
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
            
            if quota_exceeded:
                break
            
            channel_cache, quota_hit = batch_fetch_channels(channel_ids, API_KEY, channel_cache)
            if quota_hit:
                quota_exceeded = True
                break
            
            for item in items:
                sn = item["snippet"]
                vid = item["id"].get("videoId")
                cid = sn.get("channelId")
                
                if not vid or not cid or cid in seen_channels:
                    continue
                
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
                country = ch.get("country", "N/A")
                
                # Filters
                if views < min_views or (max_views > 0 and views > max_views):
                    continue
                if subs < min_subs or subs > max_subs:
                    continue
                if total_videos < min_videos or (max_videos > 0 and total_videos > max_videos):
                    continue
                
                if channel_age != "Any":
                    try:
                        if int(ch.get("created", "2000")[:4]) < int(channel_age):
                            continue
                    except:
                        pass
                
                if premium_only and country not in PREMIUM_COUNTRIES:
                    continue
                
                vtype = get_video_type(duration)
                if video_type == "Long (5min+)" and duration < 300:
                    continue
                if video_type == "Medium (1-5min)" and (duration < 60 or duration >= 300):
                    continue
                if video_type == "Shorts (<1min)" and duration >= 60:
                    continue
                
                virality = calculate_virality(views, sn["publishedAt"])
                if virality < min_virality:
                    continue
                
                is_faceless, faceless_score, faceless_reasons = is_faceless_channel(ch)
                
                if search_mode == "🤖 Faceless Only" and not is_faceless:
                    continue
                
                mon_status, mon_score = check_monetization(ch)
                if monetized_only and mon_score < 70:
                    continue
                
                engagement = calculate_engagement(views, likes, comments)
                uploads_per_week, schedule = get_upload_frequency(ch.get("created"), total_videos)
                est_revenue = estimate_revenue(ch.get("total_views", 0), country)
                niche = detect_niche(sn["title"], sn["channelTitle"], kw)
                
                seen_channels.add(cid)
                
                all_results.append({
                    "Title": sn["title"],
                    "Channel": sn["channelTitle"],
                    "Subs": subs,
                    "TotalVideos": total_videos,
                    "Views": views,
                    "Likes": likes,
                    "Comments": comments,
                    "Virality": virality,
                    "Engagement": engagement,
                    "Schedule": schedule,
                    "MonetizationStatus": mon_status,
                    "MonetizationScore": mon_score,
                    "EstRevenue": est_revenue,
                    "Niche": niche,
                    "IsFaceless": is_faceless,
                    "FacelessScore": faceless_score,
                    "FacelessReasons": ", ".join(faceless_reasons) if faceless_reasons else "N/A",
                    "Country": country,
                    "Type": vtype,
                    "Duration": f"{duration//60}:{duration%60:02d}",
                    "Uploaded": sn["publishedAt"][:10],
                    "ChCreated": ch.get("created", "")[:10] if ch.get("created") else "N/A",
                    "Keyword": kw,
                    "Thumb": sn["thumbnails"]["high"]["url"],
                    "Link": f"https://www.youtube.com/watch?v={vid}",
                    "ChannelLink": f"https://www.youtube.com/channel/{cid}"
                })
    
    progress.empty()
    status.empty()
    
    st.markdown("### 📊 Quota Used")
    col1, col2 = st.columns(2)
    col1.metric("Used", f"{st.session_state['quota_used']:,}")
    col2.metric("Remaining", f"{DAILY_QUOTA_LIMIT - st.session_state['quota_used']:,}")
    
    if quota_exceeded:
        st.warning("⚠️ Quota exhausted!")
    
    if not all_results:
        st.error("😔 No results! Try lowering filters.")
        st.stop()
    
    df = pd.DataFrame(all_results)
    
    if search_mode == "🎯 Smart (Both)":
        df = df.sort_values(["IsFaceless", "Views"], ascending=[False, False])
    else:
        df = df.sort_values("Views", ascending=False)
    
    df = df.reset_index(drop=True)
    
    st.success(f"🎉 **{len(df)} CHANNELS** found!")
    st.balloons()
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total", len(df))
    col2.metric("Faceless", len(df[df['IsFaceless'] == True]))
    col3.metric("Monetized", len(df[df['MonetizationScore'] >= 70]))
    col4.metric("Views", f"{df['Views'].sum():,.0f}")
    
    # Sort
    col1, col2 = st.columns(2)
    sort_by = col1.selectbox("Sort By", ["Views", "Virality", "Subs", "MonetizationScore", "FacelessScore"])
    sort_order = col2.selectbox("Order", ["Descending", "Ascending"])
    df = df.sort_values(by=sort_by, ascending=(sort_order == "Ascending"))
    
    # Results
    for idx, r in df.iterrows():
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            badge = "🤖 FACELESS" if r['IsFaceless'] else "👤 Regular"
            st.markdown(f"### {r['Title']}")
            st.markdown(f"**📺 [{r['Channel']}]({r['ChannelLink']})** | {badge}")
            st.markdown(f"👥 {r['Subs']:,} • 🎬 {r['TotalVideos']} • 🌍 {r['Country']} • 📂 {r['Niche']}")
            
            if "LIKELY" in r['MonetizationStatus']:
                st.success(f"💰 {r['MonetizationStatus']} | ${r['EstRevenue']:,.0f}")
            else:
                st.info(f"💰 {r['MonetizationStatus']}")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Views", f"{r['Views']:,}")
            c2.metric("Virality", f"{r['Virality']:,}/d")
            c3.metric("Engagement", f"{r['Engagement']}%")
            c4.metric("Faceless", r['FacelessScore'])
            
            st.markdown(f"🔑 `{r['Keyword']}` | [▶️ Watch]({r['Link']})")
        
        with col2:
            st.image(r["Thumb"], use_container_width=True)
    
    # Downloads
    st.markdown("---")
    st.markdown("### 📥 Downloads")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.download_button(
            "📥 CSV",
            df.to_csv(index=False).encode('utf-8'),
            f"channels_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            use_container_width=True
        )
    
    with col2:
        st.download_button(
            "📥 HTML",
            generate_html_report(df, search_mode),
            f"report_{datetime.now().strftime('%Y%m%d')}.html",
            "text/html",
            use_container_width=True
        )
    
    with col3:
        st.download_button(
            "📥 JSON",
            df.to_json(orient='records', indent=2),
            f"channels_{datetime.now().strftime('%Y%m%d')}.json",
            "application/json",
            use_container_width=True
        )

st.markdown("---")
st.caption("🎯 YouTube Channel Hunter PRO | 2025")
