import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import re
from collections import defaultdict
from io import BytesIO
import base64
import json

# ------------------------------------------------------------
# APP CONFIG
# ------------------------------------------------------------
st.set_page_config(page_title="🎯 Faceless Viral Hunter PRO MAX", layout="wide")
st.title("🎯 Faceless Viral Hunter PRO MAX")
st.markdown("**Reddit Stories, AITA, Horror, Cash Cow, Motivation - FACELESS channels ka king!**")

# Initialize session state
if 'saved_searches' not in st.session_state:
    st.session_state.saved_searches = {}
if 'blacklist' not in st.session_state:
    st.session_state.blacklist = set()
if 'whitelist' not in st.session_state:
    st.session_state.whitelist = set()
if 'search_history' not in st.session_state:
    st.session_state.search_history = []

API_KEY = st.secrets["YOUTUBE_API_KEY"]

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

MAX_KEYWORDS = 5

# ------------------------------------------------------------
# ENHANCED KEYWORD LISTS
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

# Clickbait words for title analysis
CLICKBAIT_WORDS = [
    "shocking", "unbelievable", "you won't believe", "amazing", "incredible",
    "insane", "crazy", "mind-blowing", "secret", "exposed", "revealed",
    "warning", "must watch", "don't miss", "finally", "breaking"
]

# Power words for titles
POWER_WORDS = [
    "ultimate", "complete", "proven", "exclusive", "essential", "powerful",
    "instant", "guaranteed", "free", "new", "best", "top", "first"
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

# Niche-specific CPM multipliers
NICHE_CPM_MULTIPLIERS = {
    "Finance": 2.0,
    "Tech": 1.5,
    "Health": 1.4,
    "Business": 1.6,
    "Education": 1.3,
    "True Crime": 1.2,
    "Horror/Scary": 1.0,
    "Reddit Stories": 0.9,
    "Gaming": 0.8,
    "Entertainment": 0.7,
    "Other": 1.0
}

# Related keywords suggestions
RELATED_KEYWORDS = {
    "reddit": ["reddit stories", "aita", "askreddit", "tifu", "entitled parents", "pro revenge", "nuclear revenge", "malicious compliance", "relationship advice reddit"],
    "horror": ["scary stories", "creepypasta", "true horror", "nightmare fuel", "paranormal", "ghost stories", "mr nightmare", "horror compilation"],
    "motivation": ["stoicism", "self improvement", "discipline", "success mindset", "sigma male", "marcus aurelius", "motivational speech", "life advice"],
    "facts": ["top 10", "amazing facts", "did you know", "mind blowing facts", "interesting facts", "educational", "explained"],
    "crime": ["true crime", "murder mystery", "unsolved cases", "crime documentary", "serial killer", "cold case", "investigation"]
}


# ------------------------------------------------------------
# NEW ANALYSIS FUNCTIONS
# ------------------------------------------------------------

def analyze_title(title):
    """Analyze title for CTR optimization"""
    analysis = {
        "length": len(title),
        "word_count": len(title.split()),
        "has_numbers": bool(re.search(r'\d+', title)),
        "has_emoji": bool(re.search(r'[^\w\s,.\-!?]', title)),
        "capital_ratio": sum(1 for c in title if c.isupper()) / max(len(title), 1) * 100,
        "has_question": "?" in title,
        "has_brackets": bool(re.search(r'[\[\]\(\)]', title)),
        "clickbait_words": [],
        "power_words": [],
        "ctr_score": 0
    }
    
    title_lower = title.lower()
    
    # Check for clickbait words
    for word in CLICKBAIT_WORDS:
        if word in title_lower:
            analysis["clickbait_words"].append(word)
    
    # Check for power words
    for word in POWER_WORDS:
        if word in title_lower:
            analysis["power_words"].append(word)
    
    # Calculate CTR Score (0-100)
    score = 50  # Base score
    
    # Optimal length (50-60 chars)
    if 40 <= analysis["length"] <= 70:
        score += 10
    elif analysis["length"] > 100:
        score -= 10
    
    # Numbers increase CTR
    if analysis["has_numbers"]:
        score += 10
    
    # Emojis can increase CTR
    if analysis["has_emoji"]:
        score += 5
    
    # Questions increase engagement
    if analysis["has_question"]:
        score += 5
    
    # Brackets increase CTR (e.g., [UPDATED], (2024))
    if analysis["has_brackets"]:
        score += 5
    
    # Power words boost
    score += min(len(analysis["power_words"]) * 5, 15)
    
    # Clickbait words (moderate amount is good)
    if 1 <= len(analysis["clickbait_words"]) <= 2:
        score += 10
    elif len(analysis["clickbait_words"]) > 3:
        score -= 5  # Too clickbaity can hurt
    
    analysis["ctr_score"] = min(max(score, 0), 100)
    
    return analysis


def calculate_growth_rate(channel_data):
    """Estimate channel growth rate"""
    subs = channel_data.get("subs", 0)
    total_views = channel_data.get("total_views", 0)
    video_count = channel_data.get("video_count", 0)
    created = channel_data.get("created", "")
    
    if not created or subs == 0:
        return 0, "Unknown", "N/A"
    
    try:
        created_date = datetime.strptime(created[:19], "%Y-%m-%dT%H:%M:%S")
        days_active = max((datetime.utcnow() - created_date).days, 1)
        months_active = max(days_active / 30, 1)
        
        # Subscribers per month
        subs_per_month = subs / months_active
        
        # Views per month
        views_per_month = total_views / months_active
        
        # Growth score (weighted)
        if subs_per_month >= 10000:
            growth_score = 100
            growth_label = "🚀 Explosive"
        elif subs_per_month >= 5000:
            growth_score = 85
            growth_label = "🔥 Very Fast"
        elif subs_per_month >= 2000:
            growth_score = 70
            growth_label = "📈 Fast"
        elif subs_per_month >= 1000:
            growth_score = 55
            growth_label = "✅ Good"
        elif subs_per_month >= 500:
            growth_score = 40
            growth_label = "📊 Moderate"
        elif subs_per_month >= 100:
            growth_score = 25
            growth_label = "🐢 Slow"
        else:
            growth_score = 10
            growth_label = "⏸️ Very Slow"
        
        growth_details = f"{subs_per_month:,.0f} subs/month | {views_per_month:,.0f} views/month"
        
        return growth_score, growth_label, growth_details
    except:
        return 0, "Unknown", "N/A"


def calculate_channel_health(channel_data, video_stats):
    """Calculate overall channel health score"""
    score = 0
    factors = []
    
    subs = channel_data.get("subs", 0)
    total_views = channel_data.get("total_views", 0)
    video_count = channel_data.get("video_count", 0)
    
    # Average views per video
    avg_views = total_views / max(video_count, 1)
    
    # Sub to view ratio (healthy channels have good ratio)
    view_sub_ratio = total_views / max(subs, 1)
    
    # Consistency score (based on upload frequency)
    uploads_per_week = video_stats.get("uploads_per_week", 0)
    
    # 1. Subscriber health (25 points)
    if subs >= 100000:
        score += 25
        factors.append("✅ Strong subscriber base")
    elif subs >= 10000:
        score += 20
        factors.append("✅ Good subscriber base")
    elif subs >= 1000:
        score += 15
        factors.append("📊 Decent subscribers")
    else:
        score += 5
        factors.append("⚠️ Low subscribers")
    
    # 2. View performance (25 points)
    if avg_views >= 50000:
        score += 25
        factors.append("✅ Excellent avg views")
    elif avg_views >= 20000:
        score += 20
        factors.append("✅ Great avg views")
    elif avg_views >= 10000:
        score += 15
        factors.append("📊 Good avg views")
    elif avg_views >= 5000:
        score += 10
        factors.append("📊 Moderate avg views")
    else:
        score += 5
        factors.append("⚠️ Low avg views")
    
    # 3. Consistency (25 points)
    if uploads_per_week >= 5:
        score += 25
        factors.append("✅ Very consistent uploads")
    elif uploads_per_week >= 3:
        score += 20
        factors.append("✅ Consistent uploads")
    elif uploads_per_week >= 1:
        score += 15
        factors.append("📊 Regular uploads")
    elif uploads_per_week >= 0.5:
        score += 10
        factors.append("⚠️ Infrequent uploads")
    else:
        score += 5
        factors.append("❌ Rare uploads")
    
    # 4. Engagement ratio (25 points)
    if view_sub_ratio >= 100:
        score += 25
        factors.append("✅ Excellent reach")
    elif view_sub_ratio >= 50:
        score += 20
        factors.append("✅ Good reach")
    elif view_sub_ratio >= 20:
        score += 15
        factors.append("📊 Decent reach")
    else:
        score += 10
        factors.append("⚠️ Limited reach")
    
    # Health label
    if score >= 85:
        health_label = "🟢 Excellent"
    elif score >= 70:
        health_label = "🟢 Good"
    elif score >= 55:
        health_label = "🟡 Average"
    elif score >= 40:
        health_label = "🟠 Below Average"
    else:
        health_label = "🔴 Poor"
    
    return score, health_label, factors


def calculate_viral_probability(views, virality, engagement, title_analysis, channel_health):
    """Calculate probability of video going viral"""
    score = 0
    
    # Virality component (30%)
    if virality >= 10000:
        score += 30
    elif virality >= 5000:
        score += 25
    elif virality >= 2000:
        score += 20
    elif virality >= 1000:
        score += 15
    elif virality >= 500:
        score += 10
    else:
        score += 5
    
    # Engagement component (25%)
    if engagement >= 10:
        score += 25
    elif engagement >= 5:
        score += 20
    elif engagement >= 3:
        score += 15
    elif engagement >= 1:
        score += 10
    else:
        score += 5
    
    # Title CTR score (20%)
    ctr_score = title_analysis.get("ctr_score", 50)
    score += (ctr_score / 100) * 20
    
    # Channel health (15%)
    score += (channel_health / 100) * 15
    
    # Already viral bonus (10%)
    if views >= 1000000:
        score += 10
    elif views >= 500000:
        score += 8
    elif views >= 100000:
        score += 5
    
    return min(round(score, 1), 100)


def detect_upload_pattern(created_date, total_videos, uploads_per_week):
    """Detect channel upload pattern"""
    if uploads_per_week >= 7:
        return "Daily+", "🔥 Posts daily or multiple times per day"
    elif uploads_per_week >= 5:
        return "Very Active", "📈 Posts almost daily"
    elif uploads_per_week >= 3:
        return "Active", "✅ Posts multiple times per week"
    elif uploads_per_week >= 1:
        return "Regular", "📅 Posts weekly"
    elif uploads_per_week >= 0.5:
        return "Bi-weekly", "📆 Posts every 2 weeks"
    elif uploads_per_week >= 0.25:
        return "Monthly", "🗓️ Posts monthly"
    else:
        return "Inactive", "⏸️ Rarely posts"


def calculate_niche_saturation(niche, search_results_count):
    """Estimate niche saturation level"""
    # Based on how many results we found for the niche
    if search_results_count >= 100:
        return 90, "🔴 Very Saturated"
    elif search_results_count >= 50:
        return 70, "🟠 Saturated"
    elif search_results_count >= 25:
        return 50, "🟡 Moderate"
    elif search_results_count >= 10:
        return 30, "🟢 Low Competition"
    else:
        return 10, "🟢 Untapped"


def get_related_keywords(keyword):
    """Get related keyword suggestions"""
    keyword_lower = keyword.lower()
    suggestions = []
    
    for base_kw, related in RELATED_KEYWORDS.items():
        if base_kw in keyword_lower:
            suggestions.extend(related)
    
    # Remove duplicates and the original keyword
    suggestions = list(set(suggestions))
    if keyword in suggestions:
        suggestions.remove(keyword)
    
    return suggestions[:10]  # Return top 10


def estimate_sponsorship_potential(subs, avg_views, engagement, niche):
    """Estimate sponsorship earning potential"""
    # Base rate per 1000 views
    base_rate = 20  # $20 per 1000 views for sponsorships
    
    # Niche multiplier
    niche_multipliers = {
        "Finance": 3.0,
        "Tech": 2.5,
        "Business": 2.5,
        "Health": 2.0,
        "Education": 1.5,
        "True Crime": 1.2,
        "Other": 1.0
    }
    
    multiplier = niche_multipliers.get(niche, 1.0)
    
    # Engagement bonus
    if engagement >= 5:
        multiplier *= 1.3
    elif engagement >= 3:
        multiplier *= 1.1
    
    # Subscriber tier bonus
    if subs >= 100000:
        multiplier *= 1.5
    elif subs >= 50000:
        multiplier *= 1.3
    elif subs >= 10000:
        multiplier *= 1.1
    
    # Calculate potential per video
    per_video = (avg_views / 1000) * base_rate * multiplier
    
    # Monthly potential (assuming 4 videos/month with sponsors)
    monthly = per_video * 4
    
    return round(per_video, 2), round(monthly, 2)


def analyze_competition(all_results, current_channel_id):
    """Analyze competition in the same niche"""
    similar_channels = [r for r in all_results if r.get("ChannelID") != current_channel_id]
    
    if not similar_channels:
        return 0, "No competition data"
    
    avg_subs = sum(r.get("Subs", 0) for r in similar_channels) / len(similar_channels)
    avg_views = sum(r.get("Views", 0) for r in similar_channels) / len(similar_channels)
    
    return len(similar_channels), f"Avg: {avg_subs:,.0f} subs, {avg_views:,.0f} views"


# ------------------------------------------------------------
# HELPER FUNCTIONS (Original + Enhanced)
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


def calculate_quality_score(views, virality, engagement, monetization_score, faceless_score, subs, avg_views, growth_score=0, health_score=0):
    """Enhanced quality score calculation"""
    score = 0
    
    # Virality (20 points)
    if virality >= 10000:
        score += 20
    elif virality >= 5000:
        score += 16
    elif virality >= 2000:
        score += 12
    elif virality >= 1000:
        score += 8
    elif virality >= 500:
        score += 4
    
    # Engagement (15 points)
    if engagement >= 10:
        score += 15
    elif engagement >= 5:
        score += 12
    elif engagement >= 2:
        score += 8
    elif engagement >= 1:
        score += 4
    
    # Monetization (15 points)
    score += monetization_score * 0.15
    
    # Faceless confidence (10 points)
    score += faceless_score * 0.10
    
    # Channel size sweet spot (10 points)
    if 10000 <= subs <= 500000:
        score += 10
    elif 5000 <= subs < 10000:
        score += 7
    elif 1000 <= subs < 5000:
        score += 5
    
    # Avg views (10 points)
    if avg_views >= 50000:
        score += 10
    elif avg_views >= 20000:
        score += 8
    elif avg_views >= 10000:
        score += 5
    elif avg_views >= 5000:
        score += 3
    
    # Growth score (10 points)
    score += growth_score * 0.10
    
    # Health score (10 points)
    score += health_score * 0.10
    
    return min(round(score, 1), 100)


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
        
        pattern, desc = detect_upload_pattern(created_date, total_videos, uploads_per_week)
        
        return uploads_per_week, uploads_per_month, f"{pattern} ({uploads_per_week:.1f}/week)"
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


def estimate_revenue(views, country, video_count, niche="Other"):
    base_cpm = CPM_RATES.get(country, 1.0)
    niche_multiplier = NICHE_CPM_MULTIPLIERS.get(niche, 1.0)
    cpm = base_cpm * niche_multiplier
    
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
        "Finance": ["money", "invest", "stock", "crypto", "finance", "wealth"],
        "Tech": ["tech", "technology", "gadget", "software", "programming"],
        "Health": ["health", "fitness", "diet", "workout", "medical"]
    }
    for niche, keywords in niches.items():
        if any(kw in text for kw in keywords):
            return niche
    return "Other"


def estimate_quota_usage(num_keywords, num_orders, num_regions, use_pagination, results_per_keyword):
    pages_per_search = 2 if use_pagination else 1
    searches = num_keywords * num_orders * num_regions * pages_per_search
    search_quota = searches * 100
    
    estimated_videos = min(searches * 50, results_per_keyword * num_keywords)
    video_requests = (estimated_videos // 50) + 1
    channel_requests = (estimated_videos // 50) + 1
    
    total = search_quota + video_requests + channel_requests
    
    return {
        "searches": searches,
        "search_quota": search_quota,
        "video_requests": video_requests,
        "channel_requests": channel_requests,
        "total": total
    }


def batch_fetch_channels(channel_ids, api_key, cache):
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
# HTML REPORT GENERATOR (Enhanced)
# ------------------------------------------------------------
def generate_html_report(df, stats, quota_exceeded=False):
    """Generate beautiful HTML report with all new metrics"""
    
    total_views = df['Views'].sum() if len(df) > 0 else 0
    avg_virality = df['Virality'].mean() if len(df) > 0 else 0
    avg_quality = df['QualityScore'].mean() if 'QualityScore' in df.columns and len(df) > 0 else 0
    avg_health = df['HealthScore'].mean() if 'HealthScore' in df.columns and len(df) > 0 else 0
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
    <title>Faceless Viral Hunter PRO MAX Report - {datetime.now().strftime("%Y-%m-%d")}</title>
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
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .stat-card .number {{
            font-size: 1.8rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .stat-card .label {{ font-size: 0.8rem; color: #888; margin-top: 5px; }}
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
        .channel-name {{ display: inline-block; color: #667eea; text-decoration: none; font-weight: 500; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
            gap: 10px;
            margin: 15px 0;
        }}
        .stat-item {{ background: rgba(255,255,255,0.05); border-radius: 10px; padding: 12px; text-align: center; }}
        .stat-value {{ font-size: 1.1rem; font-weight: 600; color: #fff; }}
        .stat-label {{ font-size: 0.65rem; color: #888; margin-top: 3px; }}
        .badge {{
            display: inline-block;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.75rem;
            font-weight: 500;
            margin-right: 6px;
            margin-bottom: 6px;
        }}
        .badge-green {{ background: rgba(40, 167, 69, 0.2); color: #28a745; }}
        .badge-yellow {{ background: rgba(255, 193, 7, 0.2); color: #ffc107; }}
        .badge-red {{ background: rgba(220, 53, 69, 0.2); color: #dc3545; }}
        .badge-blue {{ background: rgba(102, 126, 234, 0.2); color: #667eea; }}
        .badge-purple {{ background: rgba(156, 39, 176, 0.2); color: #9c27b0; }}
        .action-links {{ margin-top: 15px; }}
        .action-link {{
            display: inline-block;
            padding: 10px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            margin-right: 10px;
            font-size: 0.9rem;
        }}
        .footer {{ text-align: center; padding: 30px; margin-top: 40px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Faceless Viral Hunter PRO MAX</h1>
            <p>Report Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
        </div>
        
        {quota_warning}
        
        <div class="summary-grid">
            <div class="stat-card"><div class="number">{len(df)}</div><div class="label">📊 Channels</div></div>
            <div class="stat-card"><div class="number">{total_views:,.0f}</div><div class="label">👁️ Total Views</div></div>
            <div class="stat-card"><div class="number">{avg_virality:,.0f}/day</div><div class="label">🔥 Avg Virality</div></div>
            <div class="stat-card"><div class="number">{avg_quality:.1f}</div><div class="label">⭐ Avg Quality</div></div>
            <div class="stat-card"><div class="number">{avg_health:.1f}</div><div class="label">💪 Avg Health</div></div>
            <div class="stat-card"><div class="number">{monetized_count}</div><div class="label">💰 Monetized</div></div>
            <div class="stat-card"><div class="number">${total_revenue:,.0f}</div><div class="label">💵 Est. Revenue</div></div>
        </div>
        
        <h2 style="font-size: 1.5rem; margin-bottom: 20px;">🎬 Results ({len(df)} channels)</h2>
"""
    
    for idx, row in df.iterrows():
        mon_class = "badge-green" if row['MonetizationScore'] >= 70 else ("badge-yellow" if row['MonetizationScore'] >= 50 else "badge-red")
        faceless_text = "✅ Faceless" if row['Faceless'] == "YES" else "🤔 Maybe"
        
        html += f"""
        <div class="video-card">
            <div class="video-header">
                <img src="{row['Thumb']}" alt="Thumbnail" class="thumbnail" loading="lazy">
                <div class="video-info">
                    <h3 class="video-title"><a href="{row['Link']}" target="_blank">{row['Title']}</a></h3>
                    <a href="{row['ChannelLink']}" target="_blank" class="channel-name">📺 {row['Channel']}</a>
                    <div style="font-size: 0.85rem; color: #888; margin-top: 8px;">
                        🌍 {row['Country']} • 📅 {row['ChCreated']} • 🎬 {row['TotalVideos']:,} videos • 📂 {row.get('Niche', 'Other')}
                    </div>
                </div>
            </div>
            <div class="stats-grid">
                <div class="stat-item"><div class="stat-value">{row['Views']:,}</div><div class="stat-label">👁️ Views</div></div>
                <div class="stat-item"><div class="stat-value">{row['Subs']:,}</div><div class="stat-label">👥 Subs</div></div>
                <div class="stat-item"><div class="stat-value">{row['Virality']:,}/d</div><div class="stat-label">🔥 Virality</div></div>
                <div class="stat-item"><div class="stat-value">{row['Engagement%']}%</div><div class="stat-label">💬 Engage</div></div>
                <div class="stat-item"><div class="stat-value">{row['QualityScore']:.0f}</div><div class="stat-label">⭐ Quality</div></div>
                <div class="stat-item"><div class="stat-value">{row.get('HealthScore', 0):.0f}</div><div class="stat-label">💪 Health</div></div>
                <div class="stat-item"><div class="stat-value">{row.get('GrowthScore', 0):.0f}</div><div class="stat-label">📈 Growth</div></div>
                <div class="stat-item"><div class="stat-value">{row.get('ViralProb', 0):.0f}%</div><div class="stat-label">🎯 Viral</div></div>
            </div>
            <div>
                <span class="badge badge-purple">⭐ Quality: {row['QualityScore']:.0f}/100</span>
                <span class="badge {mon_class}">💰 {row['MonetizationScore']}%</span>
                <span class="badge badge-blue">{faceless_text}</span>
                <span class="badge badge-green">📈 {row.get('GrowthLabel', 'N/A')}</span>
            </div>
            <div class="action-links">
                <a href="{row['Link']}" target="_blank" class="action-link">▶️ Watch</a>
                <a href="{row['ChannelLink']}" target="_blank" class="action-link" style="background: rgba(255,255,255,0.1);">📺 Channel</a>
            </div>
        </div>
"""
    
    html += """
        <div class="footer">
            <p>🎯 Faceless Viral Hunter PRO MAX Report</p>
            <p>Made with ❤️ for Muhammed Rizwan Qamar</p>
        </div>
    </div>
</body>
</html>
"""
    return html


# ------------------------------------------------------------
# SIDEBAR SETTINGS
# ------------------------------------------------------------
st.sidebar.header("⚙️ Settings")

# Saved Searches Management
with st.sidebar.expander("💾 Saved Searches", expanded=False):
    if st.session_state.saved_searches:
        selected_preset = st.selectbox("Load Preset", ["-- Select --"] + list(st.session_state.saved_searches.keys()))
        if selected_preset != "-- Select --" and st.button("📂 Load"):
            preset = st.session_state.saved_searches[selected_preset]
            st.session_state.update(preset)
            st.rerun()
    
    preset_name = st.text_input("Save Current as", placeholder="My Preset")
    if st.button("💾 Save Current Settings") and preset_name:
        st.session_state.saved_searches[preset_name] = {
            "min_views": min_views if 'min_views' in dir() else 10000,
            "min_subs": min_subs if 'min_subs' in dir() else 1000,
        }
        st.success(f"Saved: {preset_name}")

with st.sidebar.expander("📅 Time Filters", expanded=True):
    days = st.slider("Videos from last X days", 1, 90, 14)
    channel_age = st.selectbox("Channel Created After", ["2025", "2024", "2023", "2022", "Any"], index=1)

with st.sidebar.expander("📊 View Filters", expanded=True):
    min_views = st.number_input("Min Views", min_value=1000, value=10000, step=1000)
    max_views = st.number_input("Max Views (0=No Limit)", min_value=0, value=0, step=10000)
    min_virality = st.slider("Min Virality (Views/Day)", 0, 10000, 500)
    min_engagement = st.slider("Min Engagement %", 0.0, 20.0, 0.5, step=0.1)

with st.sidebar.expander("👥 Subscriber Filters", expanded=True):
    min_subs = st.number_input("Min Subscribers", min_value=0, value=1000)
    max_subs = st.number_input("Max Subscribers", min_value=0, value=500000)

with st.sidebar.expander("🎬 Channel Video Filters", expanded=True):
    min_videos = st.slider("⭐ Minimum Videos (Channel)", 0, 1000, 10, step=5)
    max_videos_channel = st.number_input("Max Videos (0=No Limit)", min_value=0, value=0, step=100)
    min_avg_views = st.number_input("Min Avg Views/Video", min_value=0, value=0, step=1000)

with st.sidebar.expander("📈 Growth & Health Filters", expanded=False):
    min_growth_score = st.slider("Min Growth Score", 0, 100, 0)
    min_health_score = st.slider("Min Health Score", 0, 100, 0)
    min_quality_score = st.slider("Min Quality Score", 0, 100, 0)

with st.sidebar.expander("🎬 Video Type", expanded=True):
    video_type = st.selectbox("Video Duration", ["All", "Long (5min+)", "Medium (1-5min)", "Shorts (<1min)"])
    exclude_shorts = st.checkbox("❌ Exclude Shorts Completely", value=False)

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
    use_pagination = st.checkbox("Use Pagination", value=False)
    results_per_keyword = st.slider("Max Results Per Keyword", 10, 100, 30, step=10)

with st.sidebar.expander("🚫 Blacklist/Whitelist", expanded=False):
    blacklist_input = st.text_area("Blacklist Channel IDs (one per line)", height=80)
    if blacklist_input:
        st.session_state.blacklist = set(blacklist_input.strip().split('\n'))
    
    whitelist_input = st.text_area("Whitelist Channel IDs (one per line)", height=80)
    if whitelist_input:
        st.session_state.whitelist = set(whitelist_input.strip().split('\n'))
    
    st.caption(f"Blacklisted: {len(st.session_state.blacklist)} | Whitelisted: {len(st.session_state.whitelist)}")


# ------------------------------------------------------------
# KEYWORDS SECTION
# ------------------------------------------------------------
st.markdown("### 🔑 Keywords")
st.info(f"⚠️ **Quota Saving Mode**: Maximum **{MAX_KEYWORDS} keywords** allowed!")

# Keyword templates
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    if st.button("📖 Reddit", use_container_width=True):
        st.session_state['kw_template'] = "reddit stories\naita\npro revenge\nnuclear revenge\nmalicious compliance"
with col2:
    if st.button("👻 Horror", use_container_width=True):
        st.session_state['kw_template'] = "true horror stories\nscary stories\ncreepypasta\nmr nightmare type\nparanormal"
with col3:
    if st.button("💪 Motivation", use_container_width=True):
        st.session_state['kw_template'] = "stoicism\nmotivation\nself improvement\nmarcus aurelius\nsigma mindset"
with col4:
    if st.button("📺 Cash Cow", use_container_width=True):
        st.session_state['kw_template'] = "top 10 facts\nexplained documentary\ntrue crime\nmystery unsolved\nhistory facts"
with col5:
    if st.button("💰 Finance", use_container_width=True):
        st.session_state['kw_template'] = "money explained\ninvesting tips\nwealth building\nfinancial freedom\npassive income"

default_keywords = st.session_state.get('kw_template', """reddit stories
true horror stories
stoicism motivation
top 10 facts
true crime documentary""")

keyword_input = st.text_area("Enter Keywords (One per line, Max 5)", height=150, value=default_keywords)

# Parse and validate keywords
all_keywords = list(dict.fromkeys([kw.strip() for line in keyword_input.splitlines() for kw in line.split(",") if kw.strip()]))

if len(all_keywords) > MAX_KEYWORDS:
    st.warning(f"⚠️ **{len(all_keywords)} keywords** diye hain! Sirf pehle **{MAX_KEYWORDS}** use honge.")
    keywords_to_use = all_keywords[:MAX_KEYWORDS]
else:
    keywords_to_use = all_keywords

if keywords_to_use:
    st.success(f"✅ **{len(keywords_to_use)} keywords** selected: {', '.join(keywords_to_use)}")
    
    # Show related keywords suggestions
    with st.expander("💡 Related Keywords Suggestions"):
        for kw in keywords_to_use[:3]:
            related = get_related_keywords(kw)
            if related:
                st.markdown(f"**{kw}**: {', '.join(related[:5])}")


# Quota estimation
if keywords_to_use:
    quota_est = estimate_quota_usage(len(keywords_to_use), len(search_orders), len(search_regions), use_pagination, results_per_keyword)
    
    with st.expander("📊 Estimated Quota Usage"):
        cols = st.columns(4)
        cols[0].metric("Search Requests", quota_est["searches"])
        cols[1].metric("Search Quota", f"{quota_est['search_quota']:,}")
        cols[2].metric("Other Requests", f"~{quota_est['video_requests'] + quota_est['channel_requests']}")
        cols[3].metric("Total Estimated", f"~{quota_est['total']:,}")


# ------------------------------------------------------------
# MAIN SEARCH BUTTON
# ------------------------------------------------------------
if st.button("🚀 HUNT FACELESS VIRAL VIDEOS", type="primary", use_container_width=True):
    
    if not keywords_to_use:
        st.error("⚠️ Keywords daal do!")
        st.stop()
    
    all_results = []
    channel_cache = {}
    seen_videos = set()
    seen_channels = set()
    quota_exceeded = False
    niche_counts = defaultdict(int)
    
    published_after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    total_ops = len(keywords_to_use) * len(search_orders) * len(search_regions)
    current_op = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    quota_warning = st.empty()
    
    stats = {"total_searched": 0, "final": 0, "keywords_completed": 0, "filtered_out": defaultdict(int)}
    
    for kw in keywords_to_use:
        if quota_exceeded:
            break
        
        keyword_results = 0
            
        for order in search_orders:
            if quota_exceeded or keyword_results >= results_per_keyword:
                break
                
            for region in search_regions:
                if quota_exceeded or keyword_results >= results_per_keyword:
                    break
                    
                current_op += 1
                progress_bar.progress(current_op / total_ops)
                status_text.markdown(f"🔍 `{kw}` | {order} | {region} | Found: {keyword_results}/{results_per_keyword}")
                
                search_params = {
                    "part": "snippet", "q": kw, "type": "video", "order": order,
                    "publishedAfter": published_after, "maxResults": 50,
                    "regionCode": region, "relevanceLanguage": "en", "safeSearch": "none",
                    "videoDuration": "medium" if exclude_shorts else "any"
                }
                
                if video_type == "Long (5min+)":
                    search_params["videoDuration"] = "long"
                elif video_type == "Medium (1-5min)" or exclude_shorts:
                    search_params["videoDuration"] = "medium"
                elif video_type == "Shorts (<1min)":
                    search_params["videoDuration"] = "short"
                
                if use_pagination:
                    items, quota_hit = search_videos_with_pagination(kw, search_params, API_KEY, 2)
                    if quota_hit:
                        quota_exceeded = True
                        quota_warning.warning("⚠️ API Quota khatam!")
                else:
                    data = fetch_json(SEARCH_URL, {**search_params, "key": API_KEY})
                    if data == "QUOTA":
                        quota_exceeded = True
                        quota_warning.warning("⚠️ API Quota khatam!")
                        items = []
                    else:
                        items = data.get("items", []) if data else []
                
                if not items:
                    continue
                
                stats["total_searched"] += len(items)
                
                # Deduplicate
                new_items = []
                for item in items:
                    vid = item.get("id", {}).get("videoId")
                    cid = item.get("snippet", {}).get("channelId")
                    
                    # Skip blacklisted channels
                    if cid in st.session_state.blacklist:
                        stats["filtered_out"]["blacklisted"] += 1
                        continue
                    
                    if vid and vid not in seen_videos and cid not in seen_channels:
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
                    vid_data = fetch_json(VIDEOS_URL, {"part": "statistics,contentDetails", "id": ",".join(batch), "key": API_KEY})
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
                    if keyword_results >= results_per_keyword:
                        break
                        
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
                    avg_views_per_video = total_channel_views / max(total_videos, 1)
                    
                    # ============ FILTERS ============
                    
                    if exclude_shorts and duration < 60:
                        stats["filtered_out"]["shorts"] += 1
                        continue
                    
                    if views < min_views or (max_views > 0 and views > max_views):
                        stats["filtered_out"]["views"] += 1
                        continue
                    
                    if not (min_subs <= subs <= max_subs):
                        stats["filtered_out"]["subs"] += 1
                        continue
                    
                    if total_videos < min_videos:
                        stats["filtered_out"]["min_videos"] += 1
                        continue
                    
                    if max_videos_channel > 0 and total_videos > max_videos_channel:
                        stats["filtered_out"]["max_videos"] += 1
                        continue
                    
                    if min_avg_views > 0 and avg_views_per_video < min_avg_views:
                        stats["filtered_out"]["avg_views"] += 1
                        continue
                    
                    if channel_age != "Any":
                        created_year = int(ch.get("created", "2000")[:4]) if ch.get("created") else 2000
                        if created_year < int(channel_age):
                            stats["filtered_out"]["channel_age"] += 1
                            continue
                    
                    is_faceless, faceless_confidence, faceless_reasons = detect_faceless_advanced(ch, faceless_strictness)
                    if faceless_only and not is_faceless:
                        stats["filtered_out"]["not_faceless"] += 1
                        continue
                    
                    country = ch.get("country", "N/A")
                    if premium_only and country not in PREMIUM_COUNTRIES:
                        stats["filtered_out"]["country"] += 1
                        continue
                    
                    vtype = get_video_type_label(duration)
                    if video_type == "Long (5min+)" and duration < 300:
                        stats["filtered_out"]["duration"] += 1
                        continue
                    if video_type == "Medium (1-5min)" and (duration < 60 or duration >= 300):
                        stats["filtered_out"]["duration"] += 1
                        continue
                    if video_type == "Shorts (<1min)" and duration >= 60:
                        stats["filtered_out"]["duration"] += 1
                        continue
                    
                    virality = calculate_virality_score(views, sn["publishedAt"])
                    if virality < min_virality:
                        stats["filtered_out"]["virality"] += 1
                        continue
                    
                    engagement = calculate_engagement_rate(views, likes, comments)
                    if engagement < min_engagement:
                        stats["filtered_out"]["engagement"] += 1
                        continue
                    
                    uploads_per_week, uploads_per_month, schedule_desc = calculate_upload_frequency(ch.get("created", ""), total_videos)
                    if min_upload_frequency > 0 and uploads_per_week < min_upload_frequency:
                        stats["filtered_out"]["upload_freq"] += 1
                        continue
                    
                    monetization_status, _, monetization_score, monetization_reasons = check_monetization_status(ch)
                    if monetized_only and monetization_score < 50:
                        stats["filtered_out"]["not_monetized"] += 1
                        continue
                    
                    # ============ CALCULATE NEW METRICS ============
                    
                    # Growth rate
                    growth_score, growth_label, growth_details = calculate_growth_rate(ch)
                    if growth_score < min_growth_score:
                        stats["filtered_out"]["growth"] += 1
                        continue
                    
                    # Channel health
                    health_score, health_label, health_factors = calculate_channel_health(ch, {"uploads_per_week": uploads_per_week})
                    if health_score < min_health_score:
                        stats["filtered_out"]["health"] += 1
                        continue
                    
                    # Title analysis
                    title_analysis = analyze_title(sn["title"])
                    
                    # Niche detection
                    niche = detect_niche(sn["title"], sn["channelTitle"], kw)
                    niche_counts[niche] += 1
                    
                    # Quality score (enhanced)
                    quality_score = calculate_quality_score(
                        views, virality, engagement, monetization_score, 
                        faceless_confidence, subs, avg_views_per_video,
                        growth_score, health_score
                    )
                    if quality_score < min_quality_score:
                        stats["filtered_out"]["quality"] += 1
                        continue
                    
                    # Viral probability
                    viral_prob = calculate_viral_probability(views, virality, engagement, title_analysis, health_score)
                    
                    # Revenue estimation (enhanced with niche)
                    est_revenue, monthly_revenue = estimate_revenue(total_channel_views, country, total_videos, niche)
                    
                    # Sponsorship potential
                    sponsor_per_video, sponsor_monthly = estimate_sponsorship_potential(subs, avg_views_per_video, engagement, niche)
                    
                    # ============ PASSED ALL FILTERS ============
                    
                    seen_channels.add(cid)
                    stats["final"] += 1
                    keyword_results += 1
                    
                    all_results.append({
                        "Title": sn["title"],
                        "Channel": sn["channelTitle"],
                        "ChannelID": cid,
                        "Subs": subs,
                        "TotalVideos": total_videos,
                        "TotalChannelViews": total_channel_views,
                        "AvgViewsPerVideo": round(avg_views_per_video, 0),
                        "UploadsPerWeek": uploads_per_week,
                        "UploadSchedule": schedule_desc,
                        
                        # New metrics
                        "QualityScore": quality_score,
                        "GrowthScore": growth_score,
                        "GrowthLabel": growth_label,
                        "GrowthDetails": growth_details,
                        "HealthScore": health_score,
                        "HealthLabel": health_label,
                        "ViralProb": viral_prob,
                        "CTRScore": title_analysis["ctr_score"],
                        
                        # Monetization
                        "MonetizationStatus": monetization_status,
                        "MonetizationScore": monetization_score,
                        "EstRevenue": est_revenue,
                        "MonthlyRevenue": monthly_revenue,
                        "SponsorPerVideo": sponsor_per_video,
                        "SponsorMonthly": sponsor_monthly,
                        
                        # Video stats
                        "Views": views,
                        "Likes": likes,
                        "Comments": comments,
                        "Virality": virality,
                        "Engagement%": engagement,
                        "SubViewRatio": round(views / max(subs, 1), 2),
                        
                        # Meta
                        "Niche": niche,
                        "Uploaded": sn["publishedAt"][:10],
                        "ChCreated": ch.get("created", "")[:10] if ch.get("created") else "N/A",
                        "Country": country,
                        "Type": vtype,
                        "Duration": duration,
                        "DurationStr": f"{duration//60}:{duration%60:02d}",
                        "Faceless": "YES" if is_faceless else "MAYBE",
                        "FacelessScore": faceless_confidence,
                        "Keyword": kw,
                        "Thumb": sn["thumbnails"]["high"]["url"],
                        "Link": f"https://www.youtube.com/watch?v={vid}",
                        "ChannelLink": f"https://www.youtube.com/channel/{cid}"
                    })
        
        stats["keywords_completed"] += 1
    
    progress_bar.empty()
    status_text.empty()
    
    # Show quota warning
    if quota_exceeded:
        st.warning(f"""
        ⚠️ **API Quota Khatam!**
        - Keywords: **{stats['keywords_completed']}/{len(keywords_to_use)}**
        - Searched: **{stats['total_searched']}**
        - Found: **{stats['final']}**
        """)
    
    # Stats display
    st.markdown("### 📊 Statistics")
    cols = st.columns(5)
    cols[0].metric("Total Searched", stats["total_searched"])
    cols[1].metric("Keywords Done", f"{stats['keywords_completed']}/{len(keywords_to_use)}")
    cols[2].metric("Results Found", stats["final"])
    cols[3].metric("Filtered Out", sum(stats["filtered_out"].values()))
    cols[4].metric("Unique Niches", len(niche_counts))
    
    # Niche breakdown
    if niche_counts:
        with st.expander("📂 Niche Breakdown"):
            niche_df = pd.DataFrame([{"Niche": k, "Count": v} for k, v in sorted(niche_counts.items(), key=lambda x: -x[1])])
            st.dataframe(niche_df, use_container_width=True, hide_index=True)
    
    # Filter breakdown
    if stats["filtered_out"]:
        with st.expander("🔍 Filter Breakdown"):
            filter_df = pd.DataFrame([{"Filter": k.replace("_", " ").title(), "Removed": v} for k, v in sorted(stats["filtered_out"].items(), key=lambda x: -x[1]) if v > 0])
            if not filter_df.empty:
                st.dataframe(filter_df, use_container_width=True, hide_index=True)
    
    if not all_results:
        st.warning("😔 Koi result nahi mila! Filters adjust karo.")
        st.stop()
    
    df = pd.DataFrame(all_results)
    df = df.sort_values("QualityScore", ascending=False).reset_index(drop=True)
    
    st.success(f"🎉 **{len(df)} FACELESS VIRAL VIDEOS** found!")
    if not quota_exceeded:
        st.balloons()
    
    # Sorting options
    st.markdown("### 🔄 Sort Results")
    col1, col2 = st.columns(2)
    with col1:
        sort_by = st.selectbox("Sort By", [
            "QualityScore", "ViralProb", "GrowthScore", "HealthScore", 
            "Views", "Virality", "Engagement%", "Subs", "AvgViewsPerVideo",
            "MonetizationScore", "CTRScore", "EstRevenue", "SponsorMonthly"
        ])
    with col2:
        sort_order = st.selectbox("Order", ["Descending", "Ascending"])
    
    df = df.sort_values(by=sort_by, ascending=(sort_order == "Ascending"))
    
    # Display results
    for idx, r in df.iterrows():
        with st.container():
            st.markdown("---")
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Quality badge
                if r['QualityScore'] >= 70:
                    q_color = "🟢"
                elif r['QualityScore'] >= 50:
                    q_color = "🟡"
                else:
                    q_color = "🟠"
                
                st.markdown(f"### {q_color} {r['Title']}")
                st.markdown(f"**📺 [{r['Channel']}]({r['ChannelLink']})** • 👥 {r['Subs']:,} • 🎬 {r['TotalVideos']} videos • 📊 {r['AvgViewsPerVideo']:,.0f}/vid • 🌍 {r['Country']} • 📂 {r['Niche']}")
                st.markdown(f"📅 Created: {r['ChCreated']} • ⏰ {r['UploadSchedule']} • {r['GrowthLabel']}")
                
                # Score badges
                st.markdown(f"""
                **⭐ Quality: {r['QualityScore']:.0f}** | 
                **🎯 Viral Prob: {r['ViralProb']:.0f}%** | 
                **📈 Growth: {r['GrowthScore']:.0f}** | 
                **💪 Health: {r['HealthScore']:.0f}** |
                **📝 CTR: {r['CTRScore']:.0f}**
                """)
                
                # Monetization
                if "LIKELY" in r['MonetizationStatus']:
                    st.success(f"💰 {r['MonetizationStatus']} | Est: ${r['EstRevenue']:,.0f} | Sponsor: ${r['SponsorPerVideo']:,.0f}/vid")
                elif "POSSIBLY" in r['MonetizationStatus']:
                    st.info(f"💰 {r['MonetizationStatus']} ({r['MonetizationScore']}%)")
                else:
                    st.warning(f"💰 {r['MonetizationStatus']} ({r['MonetizationScore']}%)")
                
                # Stats grid
                cols = st.columns(6)
                cols[0].metric("👁️ Views", f"{r['Views']:,}")
                cols[1].metric("🔥 Virality", f"{r['Virality']:,.0f}/d")
                cols[2].metric("💬 Engage", f"{r['Engagement%']}%")
                cols[3].metric("📈 Sub:View", f"{r['SubViewRatio']}x")
                cols[4].metric("📊 Avg/Vid", f"{r['AvgViewsPerVideo']:,.0f}")
                cols[5].metric("🎯 Viral%", f"{r['ViralProb']:.0f}%")
                
                st.markdown(f"⏱️ {r['DurationStr']} ({r['Type']}) • 👍 {r['Likes']:,} • 💬 {r['Comments']:,} • 📤 {r['Uploaded']}")
                
                if r['Faceless'] == "YES":
                    st.success(f"✅ Faceless ({r['FacelessScore']}%)")
                else:
                    st.info(f"🤔 Maybe Faceless ({r['FacelessScore']}%)")
                
                st.markdown(f"🔑 `{r['Keyword']}` | [▶️ Watch]({r['Link']})")
            
            with col2:
                st.image(r["Thumb"], use_container_width=True)
    
    # Download section
    st.markdown("---")
    st.markdown("### 📥 Download Results")
    
    download_cols = st.columns(3)
    
    with download_cols[0]:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 CSV", data=csv, file_name=f"viral_hunter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv", use_container_width=True)
    
    with download_cols[1]:
        html_report = generate_html_report(df, stats, quota_exceeded)
        st.download_button("📥 HTML Report", data=html_report, file_name=f"viral_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html", mime="text/html", use_container_width=True)
    
    with download_cols[2]:
        json_data = df.to_json(orient='records', indent=2)
        st.download_button("📥 JSON", data=json_data, file_name=f"viral_hunter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", mime="application/json", use_container_width=True)
    
    # Table view
    with st.expander("📋 View Table"):
        st.dataframe(df[[
            "Title", "Channel", "QualityScore", "ViralProb", "GrowthScore", 
            "HealthScore", "Views", "Virality", "Subs", "AvgViewsPerVideo",
            "MonetizationScore", "Niche", "Country", "Faceless"
        ]], use_container_width=True, height=400)

# Footer
st.markdown("---")
st.caption("Made with ❤️ for Muhammed Rizwan Qamar | Faceless Viral Hunter PRO MAX 2025")
