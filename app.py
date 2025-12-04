import streamlit as st
import requests
from datetime import datetime, timedelta, timezone

# Load API Key
API_KEY = st.secrets["YOUTUBE_API_KEY"]

# YouTube API URLs
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"

st.title("YouTube Channel & Trending Video Insights")

# Days input
days = st.number_input("Enter Days to Search (1-30):", min_value=1, max_value=30, value=5)

# Keyword input
keyword_input = st.text_area(
    "Enter up to 50 keywords (one per line or comma-separated):",
    placeholder="Example:\nrelationship stories\naida update, reddit cheating\nopen marriage"
)
raw_keywords = keyword_input.replace(",", "\n")
keywords = [k.strip() for k in raw_keywords.split("\n") if k.strip()]

if st.button("Fetch Channel Videos"):
    if not keywords:
        st.error("Please enter at least one keyword.")
        st.stop()

    try:
        start_date = (datetime.now(timezone.utc) - timedelta(days=int(days))).isoformat()
        all_results = []

        for keyword in keywords:
            st.write(f"Searching for keyword: {keyword}")

            # Search for videos
            search_params = {
                "part": "snippet",
                "q": keyword,
                "type": "video",
                "order": "viewCount",
                "publishedAfter": start_date,
                "maxResults": 20,
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

            # Video stats
            stats_response = requests.get(
                YOUTUBE_VIDEO_URL,
                params={"part": "statistics", "id": ",".join(video_ids), "key": API_KEY}
            )
            stats_data = stats_response.json()

            # Channel stats
            channel_response = requests.get(
                YOUTUBE_CHANNEL_URL,
                params={"part": "snippet,statistics", "id": ",".join(channel_ids), "key": API_KEY}
            )
            channel_data = channel_response.json()

            stats = stats_data.get("items", [])
            channels = channel_data.get("items", [])

            for video, stat, channel in zip(videos, stats, channels):
                snippet = video["snippet"]
                title = snippet.get("title", "N/A")
                description = snippet.get("description", "")[:200]
                video_url = f"https://www.youtube.com/watch?v={video['id']['videoId']}"
                thumbnail_url = snippet["thumbnails"]["default"]["url"]
                published_at = snippet["publishedAt"]

                views = int(stat["statistics"].get("viewCount", 0))
                if views < 1000:  # filter by minimum 1000 views
                    continue

                likes = int(stat["statistics"].get("likeCount", 0))
                comments = int(stat["statistics"].get("commentCount", 0))
                subs = int(channel["statistics"].get("subscriberCount", 0))
                channel_created = channel["snippet"]["publishedAt"]

                # Trending keywords from channel's recent videos (titles)
                trending_keywords = ", ".join([v["snippet"]["title"] for v in videos[:5]])

                all_results.append({
                    "Title": title,
                    "Description": description,
                    "URL": video_url,
                    "Thumbnail": thumbnail_url,
                    "Published Date": published_at,
                    "Views": views,
                    "Likes": likes,
                    "Comments": comments,
                    "Subscribers": subs,
                    "Channel Created": channel_created,
                    "Trending Keywords": trending_keywords
                })

        if all_results:
            st.success(f"Found {len(all_results)} results!")
            # Sort by views descending
            all_results = sorted(all_results, key=lambda x: x["Views"], reverse=True)

            for result in all_results:
                st.markdown(
                    f"**Title:** {result['Title']}  \n"
                    f"**Description:** {result['Description']}  \n"
                    f"**URL:** [Watch Video]({result['URL']})  \n"
                    f"**Published Date:** {result['Published Date']}  \n"
                    f"**Views:** {result['Views']}  \n"
                    f"**Likes:** {result['Likes']}  \n"
                    f"**Comments:** {result['Comments']}  \n"
                    f"**Subscribers:** {result['Subscribers']}  \n"
                    f"**Channel Created:** {result['Channel Created']}  \n"
                    f"**Trending Keywords:** {result['Trending Keywords']}"
                )
                st.image(result["Thumbnail"], width=160)
                st.write("---")
        else:
            st.warning("No videos found with at least 1,000 views.")

    except Exception as e:
        st.error(f"An error occurred: {e}")
