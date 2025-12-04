import streamlit as st
import requests
from datetime import datetime, timedelta, timezone

# Load API Key from Streamlit Secrets
API_KEY = st.secrets["YOUTUBE_API_KEY"]

# YouTube API URLs
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"

# App Title
st.title("YouTube Viral Topics Tool")

# Days Input
days = st.number_input("Enter Days to Search (1-30):", min_value=1, max_value=30, value=5)

# Keyword Input (comma + newline both supported)
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
        # Date range fix
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
                "maxResults": 20,  # increased from 5
                "key": API_KEY,
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
                params={"part": "statistics,contentDetails", "id": ",".join(video_ids), "key": API_KEY}
            )
            stats_data = stats_response.json()

            # Channel Stats
            channel_response = requests.get(
                YOUTUBE_CHANNEL_URL,
                params={"part": "statistics", "id": ",".join(channel_ids), "key": API_KEY}
            )
            channel_data = channel_response.json()

            if "items" not in stats_data or "items" not in channel_data:
                continue

            stats = stats_data["items"]
            channels = channel_data["items"]

            # Collect Data
            for video, stat, channel in zip(videos, stats, channels):
                title = video["snippet"].get("title", "N/A")
                description = video["snippet"].get("description", "")[:200]
                video_url = f"https://www.youtube.com/watch?v={video['id']['videoId']}"
                views = int(stat["statistics"].get("viewCount", 0))
                likes = int(stat["statistics"].get("likeCount", 0))
                comments = int(stat["statistics"].get("commentCount", 0))
                subs = int(channel["statistics"].get("subscriberCount", 0))

                # Calculate views per day
                published_date = datetime.fromisoformat(video["snippet"]["publishedAt"].replace("Z", "+00:00"))
                days_since_published = max((datetime.now(timezone.utc) - published_date).days, 1)
                views_per_day = round(views / days_since_published, 2)

                # Filter: Channels under 3000 subs
                if subs < 3000:
                    all_results.append({
                        "Title": title,
                        "Description": description,
                        "URL": video_url,
                        "Views": views,
                        "Likes": likes,
                        "Comments": comments,
                        "Subscribers": subs,
                        "Views/Day": views_per_day
                    })

        # Show Results
        if all_results:
            st.success(f"Found {len(all_results)} results across all keywords!")
            # Sort by views/day descending
            all_results = sorted(all_results, key=lambda x: x["Views/Day"], reverse=True)
            for result in all_results:
                st.markdown(
                    f"**Title:** {result['Title']}  \n"
                    f"**Description:** {result['Description']}  \n"
                    f"**URL:** [Watch Video]({result['URL']})  \n"
                    f"**Views:** {result['Views']}  \n"
                    f"**Likes:** {result['Likes']}  \n"
                    f"**Comments:** {result['Comments']}  \n"
                    f"**Subscribers:** {result['Subscribers']}  \n"
                    f"**Views/Day:** {result['Views/Day']}"
                )
                st.write("---")
        else:
            st.warning("No results found for channels with fewer than 3,000 subscribers.")

    except Exception as e:
        st.error(f"An error occurred: {e}")
