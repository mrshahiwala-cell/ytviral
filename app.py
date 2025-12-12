import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import re
import json
import time
from io import BytesIO

# ------------------------------------------------------------
# APP CONFIG
# ------------------------------------------------------------
st.set_page_config(page_title="🎯 Faceless Viral Hunter PRO + AI", layout="wide")
st.title("🎯 Faceless Viral Hunter PRO")
st.markdown("**Reddit Stories, AITA, Horror, Cash Cow, Motivation + 🤖 Gemini AI!**")

# API Keys
YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", "")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

GEMINI_AVAILABLE = bool(GEMINI_API_KEY)

# API URLs
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# ------------------------------------------------------------
# CONSTANTS
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
# GEMINI AI FUNCTIONS
# ------------------------------------------------------------
def call_gemini_api(prompt, max_retries=3):
    """Call Gemini API with proper error handling"""
    if not GEMINI_API_KEY:
        return False, None, "Gemini API key not configured"
    
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 8192,
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if "candidates" in result and len(result["candidates"]) > 0:
                    text = result["candidates"][0]["content"]["parts"][0].get("text", "")
                    return True, text, None
                return False, None, "Empty response"
            elif response.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            else:
                return False, None, f"API error: {response.status_code}"
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                continue
            return False, None, "Timeout"
        except Exception as e:
            return False, None, str(e)
    
    return False, None, "Max retries exceeded"


def parse_json_from_response(text):
    """Extract JSON from Gemini response"""
    if not text:
        return None
    
    try:
        return json.loads(text.strip())
    except:
        pass
    
    # Try to find JSON in code blocks
    patterns = [r'```json\s*([\s\S]*?)\s*```', r'```\s*([\s\S]*?)\s*```', r'\{[\s\S]*\}']
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match.strip())
            except:
                continue
    
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
    except:
        pass
    
    return None


def ai_analyze_title(title, views=0):
    """Analyze YouTube title with AI"""
    prompt = f"""Analyze this YouTube video title:
Title: "{title}"
Views: {views:,}

Return ONLY JSON:
{{"hook_score": 8, "curiosity_score": 9, "emotion_score": 7, "overall_score": 8, "why_it_works": "explanation", "power_words": ["word1", "word2"], "improvement_tips": ["tip1", "tip2"], "similar_titles": ["title1", "title2", "title3"]}}"""
    
    success, response, error = call_gemini_api(prompt)
    if success:
        result = parse_json_from_response(response)
        return (True, result, None) if result else (True, {"raw": response}, None)
    return False, None, error


def ai_generate_ideas(niche, count=10):
    """Generate video ideas"""
    prompt = f"""Generate {count} viral video ideas for "{niche}" faceless YouTube channel.
Return ONLY JSON:
{{"ideas": [{{"title": "title", "hook": "hook", "description": "desc", "length": "8-12 min", "viral_potential": "high", "difficulty": "easy"}}]}}"""
    
    success, response, error = call_gemini_api(prompt)
    if success:
        result = parse_json_from_response(response)
        return (True, result, None) if result else (False, None, "Parse error")
    return False, None, error


def ai_generate_script(title, niche, length=10):
    """Generate video script"""
    prompt = f"""Write YouTube script for faceless channel:
Title: "{title}", Niche: {niche}, Length: {length} min

Return ONLY JSON:
{{"title": "{title}", "duration": "{length} min", "hook": "first 30 sec", "full_script": "complete script", "tags": ["tag1", "tag2"], "description": "SEO description"}}"""
    
    success, response, error = call_gemini_api(prompt)
    if success:
        result = parse_json_from_response(response)
        return (True, result, None) if result else (True, {"full_script": response}, None)
    return False, None, error


def ai_analyze_niche(niche):
    """Analyze niche"""
    prompt = f"""Analyze "{niche}" niche for faceless YouTube:
Return ONLY JSON:
{{"overview": "desc", "market_size": "large", "competition": "medium", "monetization": {{"cpm": "$2-5", "affiliate": "high"}}, "audience": {{"age": "18-35", "countries": ["US", "UK"]}}, "content_strategy": {{"video_length": "8-15 min", "upload_frequency": "3-5/week"}}, "growth_tips": ["tip1"], "risks": ["risk1"], "time_to_monetization": "3-6 months"}}"""
    
    success, response, error = call_gemini_api(prompt)
    if success:
        result = parse_json_from_response(response)
        return (True, result, None) if result else (False, None, "Parse error")
    return False, None, error


def ai_seo_optimize(title, niche):
    """SEO optimization"""
    prompt = f"""SEO optimize for YouTube:
Title: "{title}", Niche: {niche}

Return ONLY JSON:
{{"optimized_title": "title max 70 chars", "description": "300+ word desc", "tags": ["tag1", "tag2"], "hashtags": ["#tag1"], "keywords": {{"primary": ["kw1"], "secondary": ["kw2"]}}, "thumbnail_text": "3 WORDS"}}"""
    
    success, response, error = call_gemini_api(prompt)
    if success:
        result = parse_json_from_response(response)
        return (True, result, None) if result else (False, None, "Parse error")
    return False, None, error


# ------------------------------------------------------------
# HTML REPORT GENERATOR
# ------------------------------------------------------------
def generate_html_report(df, stats, quota_exceeded=False):
    """Generate HTML report"""
    total_views = df['Views'].sum() if len(df) > 0 else 0
    avg_virality = df['Virality'].mean() if len(df) > 0 else 0
    monetized_count = len(df[df['MonetizationScore'] >= 70]) if len(df) > 0 else 0
    total_revenue = df['EstRevenue'].sum() if 'EstRevenue' in df.columns and len(df) > 0 else 0
    
    quota_warning = ""
    if quota_exceeded:
        quota_warning = '<div style="background:#fff3cd;padding:15px;border-radius:10px;margin:20px 0;text-align:center;"><b>⚠️ API Quota Exhausted - Partial Results</b></div>'
    
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Faceless Viral Hunter Report</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Arial,sans-serif;background:#1a1a2e;color:#e4e4e4;padding:20px}}
.container{{max-width:1400px;margin:0 auto}}
.header{{text-align:center;padding:30px;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:15px;margin-bottom:20px}}
.header h1{{font-size:2rem;margin-bottom:10px}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:15px;margin-bottom:30px}}
.stat{{background:rgba(255,255,255,0.05);padding:20px;border-radius:10px;text-align:center}}
.stat .num{{font-size:1.8rem;color:#667eea;font-weight:bold}}
.stat .label{{font-size:0.9rem;color:#888}}
.card{{background:rgba(255,255,255,0.03);border-radius:15px;padding:20px;margin-bottom:15px;border:1px solid rgba(255,255,255,0.1)}}
.card-header{{display:flex;gap:15px}}
.thumb{{width:180px;height:100px;border-radius:10px;object-fit:cover}}
.card-info{{flex:1}}
.card-title{{font-size:1.1rem;font-weight:bold;margin-bottom:8px}}
.card-title a{{color:#fff;text-decoration:none}}
.card-title a:hover{{color:#667eea}}
.channel{{color:#667eea;text-decoration:none}}
.metrics{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin:15px 0}}
.metric{{background:rgba(255,255,255,0.05);padding:10px;border-radius:8px;text-align:center}}
.metric .val{{font-size:1.1rem;font-weight:bold}}
.metric .lbl{{font-size:0.7rem;color:#888}}
.badge{{display:inline-block;padding:5px 10px;border-radius:15px;font-size:0.8rem;margin-right:5px}}
.badge-green{{background:rgba(40,167,69,0.2);color:#28a745}}
.badge-yellow{{background:rgba(255,193,7,0.2);color:#ffc107}}
.badge-blue{{background:rgba(102,126,234,0.2);color:#667eea}}
.links{{margin-top:10px}}
.links a{{display:inline-block;padding:8px 15px;background:#667eea;color:#fff;text-decoration:none;border-radius:5px;margin-right:10px}}
.footer{{text-align:center;padding:20px;color:#666}}
</style></head>
<body><div class="container">
<div class="header"><h1>🎯 Faceless Viral Hunter PRO Report</h1><p>{datetime.now().strftime("%B %d, %Y %I:%M %p")}</p></div>
{quota_warning}
<div class="stats">
<div class="stat"><div class="num">{len(df)}</div><div class="label">Channels</div></div>
<div class="stat"><div class="num">{total_views:,.0f}</div><div class="label">Total Views</div></div>
<div class="stat"><div class="num">{avg_virality:,.0f}/day</div><div class="label">Avg Virality</div></div>
<div class="stat"><div class="num">{monetized_count}</div><div class="label">Monetized</div></div>
<div class="stat"><div class="num">${total_revenue:,.0f}</div><div class="label">Est Revenue</div></div>
</div>
<h2 style="margin-bottom:20px">🎬 Results ({len(df)})</h2>"""
    
    for idx, row in df.iterrows():
        mon_badge = "badge-green" if row['MonetizationScore'] >= 70 else "badge-yellow"
        html += f"""
<div class="card">
<div class="card-header">
<img src="{row['Thumb']}" class="thumb">
<div class="card-info">
<div class="card-title"><a href="{row['Link']}" target="_blank">{row['Title'][:80]}</a></div>
<a href="{row['ChannelLink']}" class="channel" target="_blank">📺 {row['Channel']}</a>
<span> • 🌍 {row['Country']} • 📅 {row['ChCreated']} • 🎬 {row['TotalVideos']} videos</span>
</div></div>
<div class="metrics">
<div class="metric"><div class="val">{row['Views']:,}</div><div class="lbl">Views</div></div>
<div class="metric"><div class="val">{row['Subs']:,}</div><div class="lbl">Subs</div></div>
<div class="metric"><div class="val">{row['TotalVideos']}</div><div class="lbl">Videos</div></div>
<div class="metric"><div class="val">{row['Virality']:,}/d</div><div class="lbl">Virality</div></div>
<div class="metric"><div class="val">{row['Engagement%']}%</div><div class="lbl">Engage</div></div>
<div class="metric"><div class="val">${row.get('EstRevenue', 0):,.0f}</div><div class="lbl">Revenue</div></div>
</div>
<div>
<span class="badge {mon_badge}">{row['MonetizationStatus']} ({row['MonetizationScore']}%)</span>
<span class="badge badge-blue">{'✅ Faceless' if row['Faceless']=='YES' else '🤔 Maybe'} ({row['FacelessScore']}%)</span>
<span class="badge badge-blue">📂 {row.get('Niche', 'Other')}</span>
<span class="badge badge-blue">⏰ {row['UploadSchedule']}</span>
</div>
<div class="links">
<a href="{row['Link']}" target="_blank">▶️ Watch</a>
<a href="{row['ChannelLink']}" target="_blank">📺 Channel</a>
</div></div>"""
    
    html += '<div class="footer">Made with ❤️ for Muhammed Rizwan Qamar | Faceless Viral Hunter PRO 2025</div></div></body></html>'
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


def parse_duration(duration):
    if not duration:
        return 0
    total = 0
    for val, unit in re.findall(r"(\d+)([HMS])", duration):
        if unit == "H": total += int(val) * 3600
        elif unit == "M": total += int(val) * 60
        elif unit == "S": total += int(val)
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
            schedule = f"🔥 Daily+ ({uploads_per_week:.1f}/wk)"
        elif uploads_per_week >= 3:
            schedule = f"📈 Active ({uploads_per_week:.1f}/wk)"
        elif uploads_per_week >= 1:
            schedule = f"✅ Regular ({uploads_per_week:.1f}/wk)"
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
        status = "🟡 POSSIBLY"
    elif score >= 30:
        status = "🟠 CLOSE"
    else:
        status = "🔴 NOT YET"
    
    return status, score, reasons


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
        reasons.append(f"Name match ({name_matches})")
    
    desc_matches = sum(1 for kw in FACELESS_DESCRIPTION_KEYWORDS if kw in description)
    if desc_matches >= 1:
        score += min(desc_matches * 10, 25)
        reasons.append(f"Desc match ({desc_matches})")
    
    thresholds = {"Relaxed": 20, "Normal": 35, "Strict": 55}
    threshold = thresholds.get(strictness, 35)
    
    return score >= threshold, min(score, 100), reasons


def get_video_type_label(duration):
    if duration < 60: return "Shorts"
    elif duration < 300: return "Medium"
    return "Long"


def format_number(num):
    if num >= 1000000: return f"{num/1000000:.1f}M"
    elif num >= 1000: return f"{num/1000:.1f}K"
    return str(num)


def estimate_revenue(views, country, video_count):
    cpm = CPM_RATES.get(country, 1.0)
    revenue = (views * 0.55 / 1000) * cpm
    monthly = revenue / max(video_count / 30, 1) if video_count > 0 else 0
    return round(revenue, 2), round(monthly, 2)


def detect_niche(title, channel_name, keyword):
    text = f"{title} {channel_name} {keyword}".lower()
    niches = {
        "Reddit Stories": ["reddit", "aita", "am i the", "tifu", "entitled", "revenge"],
        "Horror/Scary": ["horror", "scary", "creepy", "nightmare", "paranormal"],
        "True Crime": ["true crime", "crime", "murder", "case"],
        "Motivation": ["motivation", "stoic", "stoicism", "mindset", "discipline"],
        "Facts/Education": ["facts", "explained", "documentary", "history", "top 10"],
        "Gaming": ["gaming", "gameplay", "walkthrough"],
        "Compilation": ["compilation", "best of", "fails"],
        "Mystery": ["mystery", "unsolved", "conspiracy"]
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
        data = fetch_json(CHANNELS_URL, {
            "part": "snippet,statistics,brandingSettings",
            "id": ",".join(batch),
            "key": api_key
        })
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
                "banner": brand.get("bannerExternalUrl", ""),
                "custom_url": sn.get("customUrl")
            }
    return cache, False


def search_videos_with_pagination(keyword, params, api_key, max_pages=2):
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
# SIDEBAR SETTINGS - ALL RESTORED
# ------------------------------------------------------------
st.sidebar.header("⚙️ Advanced Settings")

# API Status
with st.sidebar.expander("🔌 API Status", expanded=False):
    if YOUTUBE_API_KEY:
        st.success("✅ YouTube API: Connected")
    else:
        st.error("❌ YouTube API: Missing")
    
    if GEMINI_AVAILABLE:
        st.success("✅ Gemini AI: Connected")
    else:
        st.warning("⚠️ Gemini AI: Not configured")
        st.caption("Add GEMINI_API_KEY for AI features")

with st.sidebar.expander("📅 Time Filters", expanded=True):
    days = st.slider("Videos from last X days", 1, 90, 14)
    channel_age = st.selectbox(
        "Channel Created After",
        ["2025", "2024", "2023", "2022", "Any"],
        index=1
    )

with st.sidebar.expander("📊 View Filters", expanded=True):
    min_views = st.number_input("Min Views", min_value=1000, value=10000, step=1000)
    max_views = st.number_input("Max Views (0=No Limit)", min_value=0, value=0, step=10000)
    min_virality = st.slider("Min Virality (Views/Day)", 0, 10000, 500)

with st.sidebar.expander("👥 Subscriber Filters", expanded=True):
    min_subs = st.number_input("Min Subscribers", min_value=0, value=100)
    max_subs = st.number_input("Max Subscribers", min_value=0, value=500000)

# NEW: Video Count Filter
with st.sidebar.expander("🎬 Channel Video Count Filter", expanded=True):
    min_videos = st.number_input("Min Videos on Channel", min_value=0, value=0, step=10, 
                                  help="Channels with at least this many videos")
    max_videos = st.number_input("Max Videos on Channel (0=No Limit)", min_value=0, value=0, step=50,
                                  help="Channels with at most this many videos (0 = unlimited)")
    st.caption("Filter channels by total video count")

with st.sidebar.expander("⏱️ Video Duration", expanded=True):
    video_type = st.selectbox("Video Duration", ["All", "Long (5min+)", "Medium (1-5min)", "Shorts (<1min)"])

with st.sidebar.expander("🎯 Faceless Detection", expanded=True):
    faceless_only = st.checkbox("Only Faceless Channels", value=True)
    faceless_strictness = st.select_slider(
        "Detection Strictness",
        options=["Relaxed", "Normal", "Strict"],
        value="Normal"
    )

with st.sidebar.expander("💰 Monetization Filter", expanded=False):
    monetized_only = st.checkbox("Only Likely Monetized Channels", value=False)
    min_upload_frequency = st.slider("Min Uploads per Week", 0.0, 14.0, 0.0, 0.5)

with st.sidebar.expander("🌍 Region Filters", expanded=False):
    premium_only = st.checkbox("Only Premium CPM Countries", value=False)
    search_regions = st.multiselect(
        "Search in Regions",
        ["US", "GB", "CA", "AU", "IN", "PH", "DE", "FR"],
        default=["US"]
    )

with st.sidebar.expander("🔍 Search Settings", expanded=False):
    search_orders = st.multiselect(
        "Search Order",
        ["viewCount", "relevance", "date", "rating"],
        default=["viewCount", "relevance"]
    )
    use_pagination = st.checkbox("Use Pagination (More Results)", value=True)

with st.sidebar.expander("📤 Export Settings", expanded=False):
    export_formats = st.multiselect(
        "Export Formats",
        ["CSV", "HTML Report", "JSON"],
        default=["CSV", "HTML Report"]
    )


# ------------------------------------------------------------
# MAIN TABS
# ------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Viral Hunter",
    "🎯 Title Analyzer",
    "💡 Idea Generator",
    "📝 Script Writer",
    "📊 Niche Analyzer"
])


# ============================================================
# TAB 1: VIRAL HUNTER - FULL RESTORED
# ============================================================
with tab1:
    st.markdown("### 🔑 Keywords / Titles")
    
    default_keywords = """reddit stories
aita
am i the asshole
reddit relationship advice
reddit cheating stories
true horror stories
scary stories
mr nightmare type
creepypasta
pro revenge reddit
nuclear revenge
malicious compliance
entitled parents
choosing beggars
tifu reddit
best reddit posts
askreddit
reddit updates
relationship drama
motivation
stoicism
stoic quotes
self improvement
marcus aurelius
dark psychology
sigma mindset
cash cow
top 10 facts
explained documentary
true crime
unsolved mysteries
conspiracy theories
history facts
scary mysteries
creepy compilations"""
    
    keyword_input = st.text_area(
        "Enter Keywords (One per line)",
        height=200,
        value=default_keywords
    )
    
    # Quick keyword templates
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📖 Reddit Niche"):
            st.session_state['kw'] = "reddit stories\naita\nam i the asshole\npro revenge\nnuclear revenge"
    with col2:
        if st.button("👻 Horror Niche"):
            st.session_state['kw'] = "true horror stories\nscary stories\ncreepypasta\nmr nightmare"
    with col3:
        if st.button("💪 Motivation"):
            st.session_state['kw'] = "stoicism\nmotivation\nself improvement\nmarcus aurelius"
    with col4:
        if st.button("📺 Cash Cow"):
            st.session_state['kw'] = "top 10\nfacts about\nexplained\ntrue crime"
    
    # Main search button
    if st.button("🚀 HUNT FACELESS VIRAL VIDEOS", type="primary", use_container_width=True):
        
        if not keyword_input.strip():
            
