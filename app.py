import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import re
from collections import defaultdict

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
# FACELESS DETECTION KEYWORDS (Enhanced)
# ------------------------------------------------------------
FACELESS_INDICATORS = [
    # Channel name patterns
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

# ------------------------------------------------------------
# SIDEBAR - Enhanced Settings
# ------------------------------------------------------------
st.sidebar.header("⚙️ Advanced Settings")

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

with st.sidebar.expander("🌍 Region Filters", expanded=False):
    premium_only = st.checkbox("Only Premium CPM Countries", value=False)
    search_regions = st.multiselect(
        "Search in Regions",
        ["US", "GB", "CA", "AU", "IN", "PH"],
        default=["US"]
    )

with st.sidebar.expander("🔍 Search Settings", expanded=False):
    search_orders = st.multiselect(
        "Search Order (Multiple = More Results)",
        ["viewCount", "relevance", "date", "rating"],
        default=["viewCount", "relevance"]
    )
    results_per_keyword = st.slider("Results per keyword", 50, 150, 100)
    use_pagination = st.checkbox("Use Pagination (More Results)", value=True)

# ------------------------------------------------------------
# KEYWORDS INPUT - Enhanced
# ------------------------------------------------------------
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
    "Enter Keywords (One per line - More keywords = More results)",
    height=300,
    value=default_keywords
)

# Quick keyword templates
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("📖 Reddit Niche"):
        st.session_state.keywords = "reddit stories\naita\nam i the asshole\npro revenge\nnuclear revenge\nmalicious compliance\nentitled parents\nreddit updates\nreddit drama"
with col2:
    if st.button("👻 Horror Niche"):
        st.session_state.keywords = "true horror stories\nscary stories\ncreepypasta\nmr nightmare\nhorror narration\ncreepy stories\nparanormal stories\ntrue scary"
with col3:
    if st.button("💪 Motivation Niche"):
        st.session_state.keywords = "stoicism\nmotivation\nself improvement\nmarcus aurelius\nsigma mindset\ndark psychology\nmindset\ndiscipline"
with col4:
    if st.button("📺 Cash Cow"):
        st.session_state.keywords = "top 10\nfacts about\nexplained\ndocumentary\ntrue crime\nmysteries\nconspiracy\nhistory facts"

# ------------------------------------------------------------
# HELPER FUNCTIONS - Enhanced
# ------------------------------------------------------------
def fetch_json(url, params, retries=2):
    """Safe wrapper for requests.get with retries"""
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            if "quotaExceeded" in resp.text:
                return "QUOTA"
            if resp.status_code == 403:
                return "QUOTA"
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                continue
            return None
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


def detect_faceless_advanced(channel_data, strictness="Normal"):
    """
    Advanced faceless detection using multiple signals
    Returns: (is_faceless: bool, confidence: int, reasons: list)
    """
    reasons = []
    score = 0
    
    profile_url = channel_data.get("profile", "")
    banner_url = channel_data.get("banner", "")
    channel_name = channel_data.get("name", "").lower()
    description = channel_data.get("description", "").lower()
    
    # Signal 1: Default/Generic Profile Picture
    if "default.jpg" in profile_url or "s88-c-k-c0x00ffffff-no-rj" in profile_url:
        score += 30
        reasons.append("Default profile pic")
    
    # Signal 2: No Banner
    if not banner_url:
        score += 20
        reasons.append("No banner")
    
    # Signal 3: Channel name contains faceless keywords
    name_matches = sum(1 for kw in FACELESS_INDICATORS if kw in channel_name)
    if name_matches >= 1:
        score += min(name_matches * 15, 30)
        reasons.append(f"Name matches ({name_matches} keywords)")
    
    # Signal 4: Description contains faceless keywords
    desc_matches = sum(1 for kw in FACELESS_DESCRIPTION_KEYWORDS if kw in description)
    if desc_matches >= 1:
        score += min(desc_matches * 10, 25)
        reasons.append(f"Description matches ({desc_matches} keywords)")
    
    # Signal 5: Generic/AI channel patterns
    ai_patterns = ["ai", "voice", "narrator", "stories", "compilation", "facts", "top"]
    ai_matches = sum(1 for p in ai_patterns if p in channel_name)
    if ai_matches >= 2:
        score += 15
        reasons.append("AI/Compilation pattern")
    
    # Signal 6: No custom URL (newer channels)
    if channel_data.get("custom_url") is None:
        score += 5
        reasons.append("No custom URL")
    
    # Determine threshold based on strictness
    thresholds = {"Relaxed": 20, "Normal": 35, "Strict": 55}
    threshold = thresholds.get(strictness, 35)
    
    is_faceless = score >= threshold
    confidence = min(score, 100)
    
    return is_faceless, confidence, reasons


def get_video_type_label(duration):
    """Categorize video by duration"""
    if duration < 60:
        return "Shorts"
    elif duration < 300:
        return "Medium"
    else:
        return "Long"


def batch_fetch_channels(channel_ids, api_key, cache):
    """Fetch channel details in batches of 50"""
    new_ids = [cid for cid in channel_ids if cid not in cache]
    
    if not new_ids:
        return cache
    
    for i in range(0, len(new_ids), 50):
        batch = new_ids[i:i+50]
        params = {
            "part": "snippet,statistics,brandingSettings",
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
            
            cache[c["id"]] = {
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
    
    return cache


def search_videos_with_pagination(keyword, params, api_key, max_pages=2):
    """Search videos with pagination support"""
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
# MAIN ACTION
# ------------------------------------------------------------
if st.button("🚀 HUNT FACELESS VIRAL VIDEOS", type="primary", use_container_width=True):
    
    if not keyword_input.strip():
        st.error("⚠️ Keywords daal do bhai!")
        st.stop()
    
    keywords = [kw.strip() for line in keyword_input.splitlines() 
                for kw in line.split(",") if kw.strip()]
    
    # Remove duplicates while preserving order
    keywords = list(dict.fromkeys(keywords))
    
    all_results = []
    channel_cache = {}
    seen_videos = set()
    
    published_after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Calculate total operations for progress
    total_ops = len(keywords) * len(search_orders) * len(search_regions)
    current_op = 0
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Stats tracking
    stats = {
        "total_searched": 0,
        "passed_views": 0,
        "passed_subs": 0,
        "passed_age": 0,
        "passed_faceless": 0,
        "final": 0
    }
    
    # MAIN SEARCH LOOP
    for kw in keywords:
        for order in search_orders:
            for region in search_regions:
                current_op += 1
                progress_bar.progress(current_op / total_ops)
                status_text.markdown(f"🔍 **Searching:** `{kw}` | Order: `{order}` | Region: `{region}`")
                
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
                    st.error("❌ API Quota khatam! Kal try karo ya API key change karo.")
                    st.stop()
                
                if not items:
                    continue
                
                stats["total_searched"] += len(items)
                
                # Filter already seen videos
                new_items = []
                for item in items:
                    vid = item.get("id", {}).get("videoId")
                    if vid and vid not in seen_videos:
                        seen_videos.add(vid)
                        new_items.append(item)
                
                if not new_items:
                    continue
                
                # Get video IDs and channel IDs
                video_ids = [i["id"]["videoId"] for i in new_items if "videoId" in i.get("id", {})]
                channel_ids = {i["snippet"]["channelId"] for i in new_items}
                
                # Fetch video details
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
                
                # Fetch channel details
                result = batch_fetch_channels(channel_ids, API_KEY, channel_cache)
                if result == "QUOTA":
                    st.error("❌ API Quota khatam!")
                    st.stop()
                channel_cache = result
                
                # Process and filter videos
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
                    
                    # Filter 1: Minimum views
                    if views < min_views:
                        continue
                    if max_views > 0 and views > max_views:
                        continue
                    stats["passed_views"] += 1
                    
                    # Filter 2: Subscriber range
                    if not (min_subs <= subs <= max_subs):
                        continue
                    stats["passed_subs"] += 1
                    
                    # Filter 3: Channel age
                    if channel_age != "Any":
                        created_year = int(ch.get("created", "2000")[:4]) if ch.get("created") else 2000
                        if created_year < int(channel_age):
                            continue
                    stats["passed_age"] += 1
                    
                    # Filter 4: Faceless detection
                    if faceless_only:
                        is_faceless, confidence, reasons = detect_faceless_advanced(ch, faceless_strictness)
                        if not is_faceless:
                            continue
                    else:
                        is_faceless, confidence, reasons = detect_faceless_advanced(ch, faceless_strictness)
                    stats["passed_faceless"] += 1
                    
                    # Filter 5: Country
                    country = ch.get("country", "N/A")
                    if premium_only and country not in PREMIUM_COUNTRIES:
                        continue
                    
                    # Filter 6: Video duration type
                    vtype = get_video_type_label(duration)
                    if video_type == "Long (5min+)" and duration < 300:
                        continue
                    if video_type == "Medium (1-5min)" and (duration < 60 or duration >= 300):
                        continue
                    if video_type == "Shorts (<1min)" and duration >= 60:
                        continue
                    
                    # Calculate metrics
                    virality = calculate_virality_score(views, sn["publishedAt"])
                    
                    # Filter 7: Minimum virality
                    if virality < min_virality:
                        continue
                    
                    engagement = calculate_engagement_rate(views, likes, comments)
                    sub_view_ratio = round(views / max(subs, 1), 2)
                    
                    stats["final"] += 1
                    
                    # Add result
                    all_results.append({
                        "Title": sn["title"],
                        "Channel": sn["channelTitle"],
                        "ChannelID": cid,
                        "Subs": subs,
                        "Views": views,
                        "Likes": likes,
                        "Comments": comments,
                        "Virality": virality,
                        "Engagement%": engagement,
                        "SubViewRatio": sub_view_ratio,
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
    
    progress_bar.empty()
    status_text.empty()
    
    # ------------------------------------------------------------
    # SHOW STATS
    # ------------------------------------------------------------
    st.markdown("### 📊 Search Statistics")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Searched", stats["total_searched"])
    col2.metric("Passed Views", stats["passed_views"])
    col3.metric("Passed Subs", stats["passed_subs"])
    col4.metric("Passed Age", stats["passed_age"])
    col5.metric("Final Results", stats["final"])
    
    # ------------------------------------------------------------
    # RESULTS
    # ------------------------------------------------------------
    if not all_results:
        st.warning("😔 Kuch nahi mila! Try karo:")
        st.markdown("""
        - **Days** badha do (14 ya 30 days)
        - **Min Views** kam karo (5000 ya 1000)
        - **Channel Age** "Any" ya "2023" select karo
        - **Faceless Strictness** "Relaxed" karo
        - **More keywords** add karo
        """)
        st.stop()
    
    # Create DataFrame
    df = pd.DataFrame(all_results)
    
    # Remove duplicates (keep highest views per channel)
    df = df.sort_values("Views", ascending=False)
    df = df.drop_duplicates(subset="ChannelID", keep="first")
    df = df.reset_index(drop=True)
    
    st.success(f"🎉 **{len(df)} FACELESS VIRAL VIDEOS** mil gaye!")
    st.balloons()
    
    # Sorting options
    st.markdown("### 🎯 Results")
    col1, col2 = st.columns(2)
    with col1:
        sort_by = st.selectbox("Sort By", ["Views", "Virality", "Engagement%", "Subs", "SubViewRatio"])
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
                
                # Channel info
                st.markdown(
                    f"**📺 [{r['Channel']}]({r['ChannelLink']})** • "
                    f"👥 {r['Subs']:,} subs • "
                    f"🌍 {r['Country']} • "
                    f"📅 Created: {r['ChCreated']}"
                )
                
                # Video stats
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("👁️ Views", f"{r['Views']:,}")
                col_b.metric("🔥 Virality", f"{r['Virality']:,}/day")
                col_c.metric("💬 Engagement", f"{r['Engagement%']}%")
                col_d.metric("📈 Sub:View", f"{r['SubViewRatio']}x")
                
                # Additional info
                st.markdown(
                    f"⏱️ **Duration:** {r['DurationStr']} ({r['Type']}) • "
                    f"👍 {r['Likes']:,} likes • "
                    f"💬 {r['Comments']:,} comments • "
                    f"📤 Uploaded: {r['Uploaded']}"
                )
                
                # Faceless indicator
                if r['Faceless'] == "YES":
                    st.success(f"✅ Faceless Score: {r['FacelessScore']}% | {r['FacelessReasons']}")
                else:
                    st.info(f"🤔 Faceless Score: {r['FacelessScore']}% | {r['FacelessReasons']}")
                
                st.markdown(f"🔑 Keyword: `{r['Keyword']}`")
                st.markdown(f"[▶️ Watch Video]({r['Link']})")
            
            with col2:
                st.image(r["Thumb"], use_container_width=True)
    
    # CSV Download
    st.markdown("---")
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Download Full Results (CSV)",
        data=csv,
        file_name=f"faceless_viral_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )
    
    # Excel-like view
    with st.expander("📋 View All Data (Table Format)"):
        st.dataframe(
            df[["Title", "Channel", "Views", "Virality", "Subs", "Engagement%", "Country", "Type", "Faceless", "FacelessScore"]],
            use_container_width=True,
            height=400
        )

# ------------------------------------------------------------
# FOOTER
# ------------------------------------------------------------
st.markdown("---")
st.caption("Made with ❤️ for Muhammed Rizwan Qamar | Faceless Viral Hunter PRO 2025")
