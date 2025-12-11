import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import re
from collections import defaultdict, Counter

# ------------------------------------------------------------
# APP CONFIG
# ------------------------------------------------------------
st.set_page_config(page_title="🎯 Faceless Viral Hunter PRO", layout="wide")
st.title("🎯 Faceless Viral Hunter PRO")
st.markdown("**Complete Analysis: Videos Count, Upload Schedule, Monetization Status**")

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

# Countries eligible for YouTube Partner Program
YPP_ELIGIBLE_COUNTRIES = {
    'US', 'CA', 'GB', 'AU', 'NZ', 'DE', 'FR', 'IT', 'ES', 'NL', 'BE', 'AT', 'CH',
    'SE', 'NO', 'DK', 'FI', 'IE', 'LU', 'JP', 'KR', 'SG', 'HK', 'IN', 'PK', 'BD',
    'PH', 'ID', 'MY', 'TH', 'VN', 'BR', 'MX', 'AR', 'CL', 'CO', 'PE'
}

# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------
st.sidebar.header("⚙️ Advanced Settings")

with st.sidebar.expander("📅 Time Filters", expanded=True):
    days = st.slider("Videos from last X days", 1, 90, 30)
    channel_age = st.selectbox(
        "Channel Created After",
        ["2025", "2024", "2023", "2022", "Any"],
        index=1
    )

with st.sidebar.expander("📊 View Filters", expanded=True):
    min_views = st.number_input("Min Views", min_value=1000, value=5000, step=1000)
    max_views = st.number_input("Max Views (0=No Limit)", min_value=0, value=0, step=10000)
    min_virality = st.slider("Min Virality Score (Views/Day)", 0, 10000, 500)

with st.sidebar.expander("👥 Subscriber Filters", expanded=True):
    min_subs = st.number_input("Min Subscribers", min_value=0, value=100)
    max_subs = st.number_input("Max Subscribers", min_value=0, value=500000)

with st.sidebar.expander("🎬 Video Type", expanded=True):
    video_type = st.selectbox("Video Duration", ["All", "Long (5min+)", "Medium (1-5min)", "Shorts (<1min)"])
    
with st.sidebar.expander("🎯 Faceless Detection", expanded=True):
    faceless_only = st.checkbox("Only Faceless Channels", value=True)
    faceless_strictness = st.select_slider(
        "Detection Strictness",
        options=["Relaxed", "Normal", "Strict"],
        value="Normal"
    )

with st.sidebar.expander("💰 Monetization Filters", expanded=False):
    monetized_only = st.checkbox("Only Likely Monetized Channels", value=False)
    min_total_videos = st.number_input("Min Total Videos", min_value=0, value=0)
    show_upload_schedule = st.checkbox("Analyze Upload Schedule", value=True)

with st.sidebar.expander("🌍 Region Filters", expanded=False):
    premium_only = st.checkbox("Only Premium CPM Countries", value=False)
    search_regions = st.multiselect(
        "Search in Regions",
        ["US", "GB", "CA", "AU", "IN", "PH"],
        default=["US"]
    )

with st.sidebar.expander("🔍 Search Settings", expanded=False):
    search_orders = st.multiselect(
        "Search Order",
        ["viewCount", "relevance", "date"],
        default=["viewCount", "relevance"]
    )
    results_per_keyword = st.slider("Results per keyword", 50, 150, 100)
    use_pagination = st.checkbox("Use Pagination", value=True)

# ------------------------------------------------------------
# KEYWORDS INPUT
# ------------------------------------------------------------
st.markdown("### 🔑 Keywords")

default_keywords = """reddit stories
aita
am i the asshole
reddit relationship advice
reddit cheating stories
true horror stories
scary stories
mr nightmare
creepypasta
pro revenge reddit
nuclear revenge
malicious compliance
entitled parents
tifu reddit
motivation
stoicism
sigma mindset
cash cow
top 10 facts
true crime"""

keyword_input = st.text_area(
    "Enter Keywords (One per line)",
    height=250,
    value=default_keywords
)

# ------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------
def fetch_json(url, params, retries=2):
    """Safe wrapper for requests.get with retries"""
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            if "quotaExceeded" in resp.text or resp.status_code == 403:
                return "QUOTA"
        except Exception as e:
            if attempt < retries - 1:
                continue
            return None
    return None


def parse_duration(duration):
    """Convert ISO 8601 duration to seconds"""
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
    """Calculate views per day since upload"""
    try:
        pub_date = datetime.strptime(published_at[:19], "%Y-%m-%dT%H:%M:%S")
        days_since = max((datetime.utcnow() - pub_date).days, 1)
        return round(views / days_since, 2)
    except:
        return 0


def calculate_engagement_rate(views, likes, comments):
    """Calculate engagement percentage"""
    if views == 0:
        return 0
    engagement = ((likes + comments * 2) / views) * 100
    return round(engagement, 2)


def get_video_type_label(duration):
    """Categorize video by duration"""
    if duration < 60:
        return "Shorts"
    elif duration < 300:
        return "Medium"
    else:
        return "Long"


def detect_faceless_advanced(channel_data, strictness="Normal"):
    """Advanced faceless detection"""
    reasons = []
    score = 0
    
    profile_url = channel_data.get("profile", "")
    banner_url = channel_data.get("banner", "")
    channel_name = channel_data.get("name", "").lower()
    description = channel_data.get("description", "").lower()
    
    # Signal 1: Default Profile Picture
    if "default.jpg" in profile_url or "s88-c-k-c0x00ffffff-no-rj" in profile_url:
        score += 30
        reasons.append("Default profile")
    
    # Signal 2: No Banner
    if not banner_url:
        score += 20
        reasons.append("No banner")
    
    # Signal 3: Channel name
    name_matches = sum(1 for kw in FACELESS_INDICATORS if kw in channel_name)
    if name_matches >= 1:
        score += min(name_matches * 15, 30)
        reasons.append(f"Name match ({name_matches})")
    
    # Signal 4: Description
    desc_matches = sum(1 for kw in FACELESS_DESCRIPTION_KEYWORDS if kw in description)
    if desc_matches >= 1:
        score += min(desc_matches * 10, 25)
        reasons.append(f"Desc match ({desc_matches})")
    
    # Signal 5: AI patterns
    ai_patterns = ["ai", "voice", "narrator", "stories", "compilation", "facts"]
    ai_matches = sum(1 for p in ai_patterns if p in channel_name)
    if ai_matches >= 2:
        score += 15
        reasons.append("AI pattern")
    
    # Signal 6: No custom URL
    if channel_data.get("custom_url") is None:
        score += 5
        reasons.append("No custom URL")
    
    thresholds = {"Relaxed": 20, "Normal": 35, "Strict": 55}
    threshold = thresholds.get(strictness, 35)
    
    is_faceless = score >= threshold
    confidence = min(score, 100)
    
    return is_faceless, confidence, reasons


def analyze_upload_schedule(channel_id, api_key):
    """
    Analyze channel's upload schedule by fetching recent uploads
    Returns: (upload_frequency, best_upload_time, consistency_score)
    """
    try:
        # Get channel's uploads playlist
        params = {
            "part": "contentDetails",
            "id": channel_id,
            "key": api_key
        }
        
        data = fetch_json(CHANNELS_URL, params)
        if not data or data == "QUOTA":
            return "Unknown", "Unknown", 0
        
        uploads_playlist = data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        
        # Get recent uploads (last 50)
        params = {
            "part": "snippet",
            "playlistId": uploads_playlist,
            "maxResults": 50,
            "key": api_key
        }
        
        playlist_url = "https://www.googleapis.com/youtube/v3/playlistItems"
        data = fetch_json(playlist_url, params)
        
        if not data or data == "QUOTA":
            return "Unknown", "Unknown", 0
        
        items = data.get("items", [])
        if len(items) < 5:
            return "Irregular", "Unknown", 0
        
        # Analyze upload dates
        upload_dates = []
        upload_hours = []
        
        for item in items:
            pub_date_str = item["snippet"]["publishedAt"]
            try:
                pub_date = datetime.strptime(pub_date_str[:19], "%Y-%m-%dT%H:%M:%S")
                upload_dates.append(pub_date)
                upload_hours.append(pub_date.hour)
            except:
                continue
        
        if len(upload_dates) < 5:
            return "Irregular", "Unknown", 0
        
        # Calculate gaps between uploads
        upload_dates.sort()
        gaps = []
        for i in range(1, len(upload_dates)):
            gap_days = (upload_dates[i-1] - upload_dates[i]).days
            if gap_days > 0:
                gaps.append(gap_days)
        
        if not gaps:
            return "Irregular", "Unknown", 0
        
        avg_gap = sum(gaps) / len(gaps)
        
        # Determine frequency
        if avg_gap <= 1:
            frequency = "Daily"
        elif avg_gap <= 2:
            frequency = "Every 2 days"
        elif avg_gap <= 4:
            frequency = "2-3x/week"
        elif avg_gap <= 7:
            frequency = "Weekly"
        elif avg_gap <= 14:
            frequency = "Bi-weekly"
        elif avg_gap <= 30:
            frequency = "Monthly"
        else:
            frequency = "Irregular"
        
        # Find most common upload hour
        if upload_hours:
            hour_counter = Counter(upload_hours)
            most_common_hour = hour_counter.most_common(1)[0][0]
            upload_time = f"{most_common_hour:02d}:00 UTC"
        else:
            upload_time = "Unknown"
        
        # Calculate consistency score (0-100)
        if len(gaps) > 1:
            gap_variance = sum((g - avg_gap) ** 2 for g in gaps) / len(gaps)
            consistency = max(0, 100 - (gap_variance / avg_gap * 10))
        else:
            consistency = 50
        
        return frequency, upload_time, round(consistency, 1)
        
    except Exception as e:
        return "Unknown", "Unknown", 0


def check_monetization_eligibility(channel_data, upload_analysis):
    """
    Check if channel is likely monetized based on YouTube Partner Program requirements
    Requirements:
    - 1000+ subscribers
    - 4000+ watch hours in last 12 months (we estimate from views)
    - Follow policies (we can't check)
    - In eligible country
    
    Returns: (status, confidence, reasons)
    """
    reasons = []
    score = 0
    max_score = 100
    
    subs = channel_data.get("subs", 0)
    total_views = channel_data.get("total_views", 0)
    video_count = channel_data.get("video_count", 0)
    country = channel_data.get("country", "N/A")
    created = channel_data.get("created", "")
    
    # Check 1: Subscriber count (1000+)
    if subs >= 1000:
        score += 30
        reasons.append(f"{subs:,} subs (✓)")
    elif subs >= 500:
        score += 15
        reasons.append(f"{subs:,} subs (close)")
    else:
        reasons.append(f"{subs:,} subs (need 1000)")
    
    # Check 2: Estimated watch hours
    # Rough estimate: assume avg 40% watch time, 8 min avg video
    estimated_watch_hours = (total_views * 0.4 * 8) / 60
    
    if estimated_watch_hours >= 4000:
        score += 30
        reasons.append(f"~{int(estimated_watch_hours):,}h watch (✓)")
    elif estimated_watch_hours >= 2000:
        score += 15
        reasons.append(f"~{int(estimated_watch_hours):,}h watch (close)")
    else:
        reasons.append(f"~{int(estimated_watch_hours):,}h watch (need 4000)")
    
    # Check 3: Country eligibility
    if country in YPP_ELIGIBLE_COUNTRIES:
        score += 20
        reasons.append(f"{country} (✓)")
    else:
        reasons.append(f"{country} (unknown)")
    
    # Check 4: Channel age (needs time to accumulate watch hours)
    try:
        created_date = datetime.strptime(created[:10], "%Y-%m-%d")
        age_days = (datetime.utcnow() - created_date).days
        
        if age_days >= 60:
            score += 10
            reasons.append(f"{age_days}d old (✓)")
        else:
            reasons.append(f"{age_days}d old (too new)")
    except:
        pass
    
    # Check 5: Active uploads
    frequency, _, consistency = upload_analysis
    if frequency not in ["Irregular", "Unknown"] and consistency > 30:
        score += 10
        reasons.append(f"Active ({frequency})")
    
    # Determine status
    confidence = min(score, 100)
    
    if confidence >= 70:
        status = "✅ Likely Monetized"
    elif confidence >= 40:
        status = "🟡 Possibly Monetized"
    else:
        status = "❌ Likely Not Monetized"
    
    return status, confidence, reasons


def batch_fetch_channels_extended(channel_ids, api_key, cache, analyze_schedule=False):
    """Fetch detailed channel data including upload analysis"""
    new_ids = [cid for cid in channel_ids if cid not in cache]
    
    if not new_ids:
        return cache
    
    for i in range(0, len(new_ids), 50):
        batch = new_ids[i:i+50]
        params = {
            "part": "snippet,statistics,brandingSettings,contentDetails",
            "id": ",".join(batch),
            "key": api_key
        }
        
        data = fetch_json(CHANNELS_URL, params)
        if data == "QUOTA":
            return "QUOTA"
        if not data:
            continue
            
        for c in data.get("items", []):
            sn = c["snippet"]
            stats = c["statistics"]
            brand = c.get("brandingSettings", {})
            brand_img = brand.get("image", {})
            brand_ch = brand.get("channel", {})
            
            profile = sn.get("thumbnails", {}).get("default", {}).get("url", "")
            banner = brand_img.get("bannerExternalUrl", "")
            
            channel_data = {
                "name": sn.get("title", ""),
                "subs": int(stats.get("subscriberCount", 0)),
                "total_views": int(stats.get("viewCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
                "created": sn.get("publishedAt", ""),
                "country": sn.get("country", "N/A"),
                "description": sn.get("description", ""),
                "profile": profile,
                "banner": banner,
                "custom_url": sn.get("customUrl"),
                "keywords": brand_ch.get("keywords", "")
            }
            
            # Analyze upload schedule if requested
            if analyze_schedule:
                frequency, upload_time, consistency = analyze_upload_schedule(c["id"], api_key)
                channel_data["upload_frequency"] = frequency
                channel_data["upload_time"] = upload_time
                channel_data["upload_consistency"] = consistency
            else:
                channel_data["upload_frequency"] = "Not Analyzed"
                channel_data["upload_time"] = "Not Analyzed"
                channel_data["upload_consistency"] = 0
            
            # Check monetization eligibility
            monetization_status, mon_confidence, mon_reasons = check_monetization_eligibility(
                channel_data,
                (channel_data["upload_frequency"], channel_data["upload_time"], channel_data["upload_consistency"])
            )
            
            channel_data["monetization_status"] = monetization_status
            channel_data["monetization_confidence"] = mon_confidence
            channel_data["monetization_reasons"] = mon_reasons
            
            cache[c["id"]] = channel_data
    
    return cache


def search_videos_with_pagination(keyword, params, api_key, max_pages=2):
    """Search videos with pagination"""
    all_items = []
    next_token = None
    
    for page in range(max_pages):
        search_params = params.copy()
        search_params["key"] = api_key
        
        if next_token:
            search_params["pageToken"] = next_token
        
        data = fetch_json(SEARCH_URL, search_params)
        
        if data == "QUOTA":
            return "QUOTA"
        if not data:
            break
            
        items = data.get("items", [])
        all_items.extend(items)
        
        next_token = data.get("nextPageToken")
        if not next_token:
            break
    
    return all_items


# ------------------------------------------------------------
# MAIN SEARCH ACTION
# ------------------------------------------------------------
if st.button("🚀 HUNT VIRAL VIDEOS", type="primary", use_container_width=True):
    
    if not keyword_input.strip():
        st.error("⚠️ Keywords daal do!")
        st.stop()
    
    keywords = [kw.strip() for line in keyword_input.splitlines() 
                for kw in line.split(",") if kw.strip()]
    keywords = list(dict.fromkeys(keywords))
    
    all_results = []
    channel_cache = {}
    seen_videos = set()
    
    published_after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    total_ops = len(keywords) * len(search_orders) * len(search_regions)
    current_op = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    stats = {
        "total_searched": 0,
        "passed_filters": 0,
        "final": 0
    }
    
    # MAIN SEARCH LOOP
    for kw in keywords:
        for order in search_orders:
            for region in search_regions:
                current_op += 1
                progress_bar.progress(current_op / total_ops)
                status_text.markdown(f"🔍 **Searching:** `{kw}` | `{order}` | `{region}`")
                
                search_params = {
                    "part": "snippet",
                    "q": kw,
                    "type": "video",
                    "order": order,
                    "publishedAfter": published_after,
                    "maxResults": 50,
                    "regionCode": region,
                    "relevanceLanguage": "en",
                    "safeSearch": "none"
                }
                
                if use_pagination:
                    items = search_videos_with_pagination(kw, search_params, API_KEY, max_pages=2)
                else:
                    data = fetch_json(SEARCH_URL, {**search_params, "key": API_KEY})
                    items = data.get("items", []) if data and data != "QUOTA" else []
                
                if items == "QUOTA":
                    st.error("❌ API Quota khatam!")
                    st.stop()
                
                if not items:
                    continue
                
                stats["total_searched"] += len(items)
                
                # Filter seen videos
                new_items = []
                for item in items:
                    vid = item.get("id", {}).get("videoId")
                    if vid and vid not in seen_videos:
                        seen_videos.add(vid)
                        new_items.append(item)
                
                if not new_items:
                    continue
                
                # Get video and channel IDs
                video_ids = [i["id"]["videoId"] for i in new_items if "videoId" in i.get("id", {})]
                channel_ids = {i["snippet"]["channelId"] for i in new_items}
                
                # Fetch video stats
                video_stats = {}
                for i in range(0, len(video_ids), 50):
                    batch = video_ids[i:i+50]
                    params = {
                        "part": "statistics,contentDetails",
                        "id": ",".join(batch),
                        "key": API_KEY
                    }
                    vid_data = fetch_json(VIDEOS_URL, params)
                    
                    if vid_data == "QUOTA":
                        st.error("❌ API Quota khatam!")
                        st.stop()
                    
                    if vid_data:
                        for v in vid_data.get("items", []):
                            dur_sec = parse_duration(v["contentDetails"].get("duration", ""))
                            s = v.get("statistics", {})
                            video_stats[v["id"]] = {
                                "views": int(s.get("viewCount", 0)),
                                "likes": int(s.get("likeCount", 0)),
                                "comments": int(s.get("commentCount", 0)),
                                "duration": dur_sec
                            }
                
                # Fetch channel details with extended analysis
                result = batch_fetch_channels_extended(
                    channel_ids, 
                    API_KEY, 
                    channel_cache,
                    analyze_schedule=show_upload_schedule
                )
                
                if result == "QUOTA":
                    st.error("❌ API Quota khatam!")
                    st.stop()
                
                channel_cache = result
                
                # Process videos
                for item in new_items:
                    sn = item["snippet"]
                    vid = item["id"].get("videoId")
                    if not vid:
                        continue
                    
                    cid = sn["channelId"]
                    v_stats = video_stats.get(vid, {})
                    ch = channel_cache.get(cid, {})
                    
                    views = v_stats.get("views", 0)
                    likes = v_stats.get("likes", 0)
                    comments = v_stats.get("comments", 0)
                    duration = v_stats.get("duration", 0)
                    subs = ch.get("subs", 0)
                    total_videos = ch.get("video_count", 0)
                    
                    # FILTERS
                    # 1. Views
                    if views < min_views:
                        continue
                    if max_views > 0 and views > max_views:
                        continue
                    
                    # 2. Subs
                    if not (min_subs <= subs <= max_subs):
                        continue
                    
                    # 3. Channel age
                    if channel_age != "Any":
                        created_year = int(ch.get("created", "2000")[:4]) if ch.get("created") else 2000
                        if created_year < int(channel_age):
                            continue
                    
                    # 4. Total videos
                    if total_videos < min_total_videos:
                        continue
                    
                    # 5. Faceless
                    if faceless_only:
                        is_faceless, confidence, reasons = detect_faceless_advanced(ch, faceless_strictness)
                        if not is_faceless:
                            continue
                    else:
                        is_faceless, confidence, reasons = detect_faceless_advanced(ch, faceless_strictness)
                    
                    # 6. Monetization
                    if monetized_only:
                        mon_status = ch.get("monetization_status", "")
                        if "❌" in mon_status:
                            continue
                    
                    # 7. Country
                    country = ch.get("country", "N/A")
                    if premium_only and country not in PREMIUM_COUNTRIES:
                        continue
                    
                    # 8. Duration
                    vtype = get_video_type_label(duration)
                    if video_type == "Long (5min+)" and duration < 300:
                        continue
                    if video_type == "Medium (1-5min)" and (duration < 60 or duration >= 300):
                        continue
                    if video_type == "Shorts (<1min)" and duration >= 60:
                        continue
                    
                    # 9. Virality
                    virality = calculate_virality_score(views, sn["publishedAt"])
                    if virality < min_virality:
                        continue
                    
                    stats["passed_filters"] += 1
                    
                    engagement = calculate_engagement_rate(views, likes, comments)
                    sub_view_ratio = round(views / max(subs, 1), 2)
                    
                    stats["final"] += 1
                    
                    # Add result
                    all_results.append({
                        "Title": sn["title"],
                        "Channel": sn["channelTitle"],
                        "ChannelID": cid,
                        "Subs": subs,
                        "TotalVideos": total_videos,
                        "TotalViews": ch.get("total_views", 0),
                        "Views": views,
                        "Likes": likes,
                        "Comments": comments,
                        "Virality": virality,
                        "Engagement%": engagement,
                        "SubViewRatio": sub_view_ratio,
                        "Uploaded": sn["publishedAt"][:10],
                        "ChCreated": ch.get("created", "")[:10] if ch.get("created") else "N/A",
                        "ChAge(Days)": (datetime.utcnow() - datetime.strptime(ch.get("created", "")[:10], "%Y-%m-%d")).days if ch.get("created") else 0,
                        "Country": country,
                        "Type": vtype,
                        "Duration": duration,
                        "DurationStr": f"{duration//60}:{duration%60:02d}",
                        "UploadFrequency": ch.get("upload_frequency", "Unknown"),
                        "UploadTime": ch.get("upload_time", "Unknown"),
                        "UploadConsistency": ch.get("upload_consistency", 0),
                        "MonetizationStatus": ch.get("monetization_status", "Unknown"),
                        "MonetizationConfidence": ch.get("monetization_confidence", 0),
                        "MonetizationReasons": ", ".join(ch.get("monetization_reasons", [])),
                        "Faceless": "YES" if is_faceless else "MAYBE",
                        "FacelessScore": confidence,
                        "FacelessReasons": ", ".join(reasons) if reasons else "N/A",
                        "Keyword": kw,
                        "Thumb": sn["thumbnails"]["high"]["url"],
                        "Link": f"https://www.youtube.com/watch?v={vid}",
                        "ChannelLink": f"https://www.youtube.com/channel/{cid}"
                    })
    
    progress_bar.empty()
    status_text.empty()
    
    # ------------------------------------------------------------
    # SHOW STATS
    # ------------------------------------------------------------
    st.markdown("### 📊 Search Statistics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Searched", stats["total_searched"])
    col2.metric("Passed Filters", stats["passed_filters"])
    col3.metric("Final Results", stats["final"])
    
    # ------------------------------------------------------------
    # RESULTS
    # ------------------------------------------------------------
    if not all_results:
        st.warning("😔 Kuch nahi mila! Filters relax karo.")
        st.stop()
    
    df = pd.DataFrame(all_results)
    df = df.sort_values("Views", ascending=False)
    df = df.drop_duplicates(subset="ChannelID", keep="first")
    df = df.reset_index(drop=True)
    
    st.success(f"🎉 **{len(df)} CHANNELS** found!")
    st.balloons()
    
    # Sorting
    st.markdown("### 🎯 Results")
    col1, col2 = st.columns(2)
    with col1:
        sort_by = st.selectbox("Sort By", ["Views", "Virality", "Subs", "TotalVideos", "MonetizationConfidence"])
    with col2:
        sort_order = st.selectbox("Order", ["Descending", "Ascending"])
    
    df = df.sort_values(by=sort_by, ascending=(sort_order == "Ascending"))
    
    # Display
    for idx, r in df.iterrows():
        with st.container():
            st.markdown("---")
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### {r['Title']}")
                
                # Channel info
                st.markdown(
                    f"**📺 [{r['Channel']}]({r['ChannelLink']})** • "
                    f"👥 {r['Subs']:,} subs • "
                    f"🎬 {r['TotalVideos']:,} videos • "
                    f"👁️ {r['TotalViews']:,} total views"
                )
                
                st.markdown(
                    f"🌍 {r['Country']} • "
                    f"📅 Created: {r['ChCreated']} ({r['ChAge(Days)']} days old)"
                )
                
                # Video stats
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("👁️ Views", f"{r['Views']:,}")
                col_b.metric("🔥 Virality", f"{r['Virality']:,}/day")
                col_c.metric("💬 Engagement", f"{r['Engagement%']}%")
                col_d.metric("📈 View:Sub", f"{r['SubViewRatio']}x")
                
                # Upload schedule
                if r['UploadFrequency'] != "Not Analyzed":
                    st.markdown(
                        f"📤 **Upload Schedule:** {r['UploadFrequency']} • "
                        f"⏰ Time: {r['UploadTime']} • "
                        f"📊 Consistency: {r['UploadConsistency']}%"
                    )
                
                # Monetization
                mon_icon = "✅" if "✅" in r['MonetizationStatus'] else "🟡" if "🟡" in r['MonetizationStatus'] else "❌"
                st.markdown(
                    f"💰 **Monetization:** {r['MonetizationStatus']} ({r['MonetizationConfidence']}%)"
                )
                st.caption(f"Reasons: {r['MonetizationReasons']}")
                
                # Faceless
                if r['Faceless'] == "YES":
                    st.success(f"✅ Faceless: {r['FacelessScore']}% | {r['FacelessReasons']}")
                else:
                    st.info(f"🤔 Faceless: {r['FacelessScore']}% | {r['FacelessReasons']}")
                
                st.markdown(
                    f"⏱️ {r['DurationStr']} ({r['Type']}) • "
                    f"👍 {r['Likes']:,} • "
                    f"💬 {r['Comments']:,} • "
                    f"📤 {r['Uploaded']} • "
                    f"🔑 `{r['Keyword']}`"
                )
                
                st.markdown(f"[▶️ Watch Video]({r['Link']})")
            
            with col2:
                st.image(r["Thumb"], use_container_width=True)
    
    # CSV Download
    st.markdown("---")
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Download Results (CSV)",
        data=csv,
        file_name=f"faceless_viral_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    # Table view
    with st.expander("📋 Table View"):
        display_cols = [
            "Title", "Channel", "TotalVideos", "Subs", "Views", "Virality",
            "UploadFrequency", "UploadTime", "MonetizationStatus", 
            "Faceless", "Country"
        ]
        st.dataframe(df[display_cols], use_container_width=True, height=400)

st.markdown("---")
st.caption("🚀 Made with ❤️ for Muhammed Rizwan Qamar | Complete PRO Edition 2025")
