import streamlit as st
import requests
from datetime import datetime, timedelta, timezone

# -------------------
# CONFIGURATION
# -------------------
# YouTube API Key from Streamlit Secrets
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]

# Gemini API Key (AIzaSyAuxEnMZXoYmZZtKEqAVJ7GdQ-VVHSgryg)
GEMINI_API_KEY = st.secrets.get("GEMINimport streamlit as st
import requests
from datetime import datetime, timedelta, timezone

# -------------------
# CONFIGURATION
# -------------------
# YouTube API Key from Streamlit Secrets
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]

# Gemini API Key from Streamlit Secrets
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    st.error("Gemini API key not found in secrets!")
    st.stop()

# YouTube API URLs
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"

# -------------------
# FUNCTIONS
# -------------------

def generate_seo_script(topic):
    """Generate SEO-friendly video script using Gemini API"""
    url = "https://gemini.googleapis.com/v1/generateText"  # Example endpoint
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = (
        f"Write a long SEO-friendly YouTube video script about '{topic}'. "
        "Include headings, subheadings, keywords, and an engaging intro and outro."
    )
    payload = {"prompt": prompt, "max_output_tokens": 1000}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        # Gemini API may use different key depending on version
        return data.get("output_text") or data.get("text") or "No content generated."
    except Exception as e:
        return f"Error generating script: {e}"

# -------------------
# STREAMLIT UI
# -------------------

st.title("YouTube Viral Topics + SEO Script Tool")

days = st.number_input("Enter Days to Search (1-30):", min_value=1, max_value=30, value=5)

keyword_input = st.text_area(
    "Enter up to 50 keywords (one per line or comma-separated):",
    placeholder="Example:\nrelationship stories\naida update, reddit cheating\nopen marriage"
)

raw_keywords = keyword_input.replace(",", "\n")
keywords = [k.strip() for k in raw_keywords.split("\n") if k.strip()]

if st.button("Fetch Data"):
    if not keywords:
        st.error("Please enter at least one keyword.")
        st.stop()

    start_date = (datetime.now(timezone.utc) - timedelta(days=int(days))).isoformat()
    all_results = []

    for keyword in keywords:
        st.info(f"Searching for keyword: {keyword}")
        try:
            search_params = {
                "part": "snippet",
                "q": keyword,
                "type": "video",
                "order": "viewCount",
                "publishedAfter": start_date,
                "maxResults": 5,
                "key": YOUTUBE_API_KEY,
            }

            response = requests.get(YOUTUBE_SEARCH_URL, params=search_params)
            data = response.json()
            videos = data.get("items", [])

            if not videos:
                st.warning(f"No videos found for keyword: {keyword}")
                continue

            video_ids = [v["id"].get("videoId") for v in videos if "videoId" in v["id"]]
            channel_ids = [v["snippet"].get("channelId") for v in videos]

            if not video_ids or not channel_ids:
                continue

            stats_response = requests.get(
                YOUTUBE_VIDEO_URL,
                params={"part": "statistics", "id": ",".join(video_ids), "key": YOUTUBE_API_KEY}
            )
            stats_data = stats_response.json().get("items", [])

            channel_response = requests.get(
                YOUTUBE_CHANNEL_URL,
                params={"part": "statistics", "id": ",".join(channel_ids), "key": YOUTUBE_API_KEY}
            )
            channel_data = channel_response.json().get("items", [])

            for video, stat, channel in zip(videos, stats_data, channel_data):
                title = video["snippet"].get("title", "N/A")
                description = video["snippet"].get("description", "")[:200]
                video_url = f"https://www.youtube.com/watch?v={video['id'].get('videoId')}"
                views = int(stat["statistics"].get("viewCount", 0))
                subs = int(channel["statistics"].get("subscriberCount", 0))

                if subs < 3000:
                    seo_script = generate_seo_script(title)
                    all_results.append({
                        "Title": title,
                        "Description": description,
                        "URL": video_url,
                        "Views": views,
                        "Subscribers": subs,
                        "SEO_Script": seo_script
                    })

        except Exception as e:
            st.error(f"Error fetching data for '{keyword}': {e}")

    if all_results:
        st.success(f"Found {len(all_results)} results!")
        for result in all_results:
            st.markdown(
                f"**Title:** {result['Title']}  \n"
                f"**Description:** {result['Description']}  \n"
                f"**URL:** [Watch Video]({result['URL']})  \n"
                f"**Views:** {result['Views']}  \n"
                f"**Subscribers:** {result['Subscribers']}"
            )
            st.text_area("Generated SEO Script", value=result['SEO_Script'], height=300)
            st.write("---")
    else:
        st.warning("No results found for channels under 3,000 subscribers.")
I_API_KEY", "AIzaSyAuxEnMZXoYmZZtKEqAVJ7GdQ-VVHSgryg")

# YouTube API URLs
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"

# -------------------
# FUNCTIONS
# -------------------

def generate_seo_script(topic):
    """Generate SEO-optimized long-form content using Gemini API"""
    url = "https://gemini.googleapis.com/v1/generateText"  # Example endpoint
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"Write a long SEO-friendly YouTube video script about '{topic}'. Include headings, subheadings, keywords, and an engaging intro and outro."
    payload = {"prompt": prompt, "max_output_tokens": 1000}

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json().get("output_text", "No content generated.")
    else:
        return f"Error generating script: {response.text}"

# -------------------
# STREAMLIT APP
# -------------------
st.title("YouTube Viral Topics + SEO Script Tool")

# Days Input
days = st.number_input("Enter Days to Search (1-30):", min_value=1, max_value=30, value=5)

# Keyword Input
keyword_input = st.text_area(
    "Enter up to 50 keywords (one per line or comma-separated):",
    placeholder="Example:\nrelationship stories\naida update, reddit cheating\nopen marriage"
)

# Convert raw input → supports comma + newline
raw_keywords = keyword_input.replace(",", "\n")
keywords = [k.strip() for k in raw_keywords.split("\n") if k.strip()]

# Fetch Data Button
if st.button("Fetch Data"):
    if not keywords:
        st.error("Please enter at least one keyword.")
        st.stop()

    try:
        start_date = (datetime.now(timezone.utc) - timedelta(days=int(days))).isoformat()
        all_results = []

        # Loop keywords
        for keyword in keywords:
            st.write(f"Searching for keyword: {keyword}")

            search_params = {
                "part": "snippet",
                "q": keyword,
                "type": "video",
                "order": "viewCount",
                "publishedAfter": start_date,
                "maxResults": 5,
                "key": YOUTUBE_API_KEY,
            }

            response = requests.get(YOUTUBE_SEARCH_URL, params=search_params)
            data = response.json()

            if "items" not in data or not data["items"]:
                st.warning(f"No videos found for keyword: {keyword}")
                continue

            videos = data["items"]
            video_ids = [v["id"]["videoId"] for v in videos if "videoId" in v["id"]]
            channel_ids = [v["snippet"]["channelId"] for v in videos]

            if not video_ids or not channel_ids:
                continue

            # Video Stats
            stats_response = requests.get(
                YOUTUBE_VIDEO_URL,
                params={"part": "statistics", "id": ",".join(video_ids), "key": YOUTUBE_API_KEY}
            )
            stats_data = stats_response.json()

            # Channel Stats
            channel_response = requests.get(
                YOUTUBE_CHANNEL_URL,
                params={"part": "statistics", "id": ",".join(channel_ids), "key": YOUTUBE_API_KEY}
            )
            channel_data = channel_response.json()

            if "items" not in stats_data or "items" not in channel_data:
                continue

            # Collect Data & Generate Script
            for video, stat, channel in zip(videos, stats_data["items"], channel_data["items"]):
                title = video["snippet"].get("title", "N/A")
                description = video["snippet"].get("description", "")[:200]
                video_url = f"https://www.youtube.com/watch?v={video['id']['videoId']}"
                views = int(stat["statistics"].get("viewCount", 0))
                subs = int(channel["statistics"].get("subscriberCount", 0))

                # Filter: Channels under 3000 subs
                if subs < 3000:
                    seo_script = generate_seo_script(title)
                    all_results.append({
                        "Title": title,
                        "Description": description,
                        "URL": video_url,
                        "Views": views,
                        "Subscribers": subs,
                        "SEO_Script": seo_script
                    })

        # Show Results
        if all_results:
            st.success(f"Found {len(all_results)} results across all keywords!")
            for result in all_results:
                st.markdown(
                    f"**Title:** {result['Title']}  \n"
                    f"**Description:** {result['Description']}  \n"
                    f"**URL:** [Watch Video]({result['URL']})  \n"
                    f"**Views:** {result['Views']}  \n"
                    f"**Subscribers:** {result['Subscribers']}"
                )
                st.text_area("Generated SEO Script", value=result['SEO_Script'], height=300)
                st.write("---")
        else:
            st.warning("No results found for channels with fewer than 3,000 subscribers.")

    except Exception as e:
        st.error(f"An error occurred: {e}")

