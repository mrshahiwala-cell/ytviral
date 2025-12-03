import streamlit as st
import requests
from datetime import datetime, timedelta

# API Key from Streamlit secrets
API_KEY = st.secrets["YOUTUBE_API_KEY"]

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"

st.title("YouTube Viral Topics Tool")

days = st.number_input("Enter Days to Search (1-30):", min_value=1, max_value=30, value=5)

keyword_input = st.text_area(
    "Enter keywords (line by line or separated by commas):",
    placeholder="Example:\nrelationship stories, aita update, reddit cheating, open marriage"
)

keywords = []
for part in keyword_input.split("\n"):
    for kw in part.split(","):
        if kw.strip():
            keywords.append(kw.strip())

if st.button("Fetch Data"):
    if not keywords:
        st.error("Please enter at least one keyword.")
        st.stop()

    try:
        start_date = (datetime.utcnow() - timedelta(days=int(days))).isoformat("T") + "Z"
        all_results = []

        for keyword in keywords:
            st.write(f"Searching for keyword: {keyword}")

            search_params = {
                "part": "snippet",
                "q": keyword,
                "type": "video",
                "order": "viewCount",
                "publishedAfter": start_date,
                "maxResults": 5,
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

            stats_response = requests.get(
                YOUTUBE_VIDEO_URL,
                params={"part": "statistics", "id": ",".join(video_ids), "key": API_KEY}
            )
            stats_data = stats_response.json()

            channel_response = requests.get(
                YOUTUBE_CHANNEL_URL,
                params={"part": "statistics", "id": ",".join(channel_ids), "key": API_KEY}
            )
            channel_data = channel_response.json()

            if "items" not in stats_data or "items" not in channel_data:
                continue

            stats = stats_data["items"]
            channels = channel_data["items"]

            for video, stat, channel in zip(videos, stats, channels):
                title = video["snippet"].get("title", "N/A")
                description = video["snippet"].get("description", "")[:200]
                video_url = f"https://www.youtube.com/watch?v={video['id']['videoId']}"
                views = int(stat["statistics"].get("viewCount", 0))
                subs = int(channel["statistics"].get("subscriberCount", 0))

                if subs < 3000:
                    all_results.append({
                        "Title": title,
                        "Description": description,
                        "URL": video_url,
                        "Views": views,
                        "Subscribers": subs
                    })

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
                st.write("---")
        else:
            st.warning("No results found for channels with fewer than 3,000 subscribers.")

    except Exception as e:
        st.error(f"An error occurred: {e}")
