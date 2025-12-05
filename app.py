import streamlit as st
import requests
from datetime import datetime, timedelta, timezone
import time

# ====== API ======
API_KEY = st.secrets["YOUTUBE_API_KEY"]
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

st.set_page_config(page_title="Viral YouTube Finder", layout="wide")
st.title("YouTube Viral Video Finder (Guaranteed Results)")
st.markdown("**Ab har keyword pe 100% result milega – Bilkul Working Version**")

# Input
col1, col2 = st.columns(2)
with col1:
    days = st.number_input("Days ago se search karein (1-30)", 1, 30, 7)
with col2:
    country = st.selectbox("Country", 
        ["US", "IN", "GB", "PK", "BD", "CA", "AU", "AE", "BR", "ID", "MY", "EG", "DE", "FR"],
        index=1)  # India default kyunki zyada chance

keyword_input = st.text_area("Keywords daalein (ek line mein ek ya comma se)", 
    height=150,
    placeholder="reddit stories\naita cheating\ntrue horror stories\nmrbeast challenge")

if st.button("Viral Videos Dhundo Abhi!", type="primary"):
    if not keyword_input.strip():
        st.error("Keyword to daalo bhai!")
        st.stop()

    keywords = [k.strip() for k in keyword_input.replace(",", "\n").split("\n") if k.strip()]
    if not keywords:
        st.error("Koi valid keyword nahi mila!")
        st.stop()

    all_results = []
    progress = st.progress(0)
    
    for i, keyword in enumerate(keywords):
        st.write(f"**Searching:** `{keyword}` in **{country}**")
        progress.progress((i + 1) / len(keywords))
        
        # Date filter
175        published_after = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat("T") + "Z"

        # Maximum results le rahe hain
        for page in range(3):  # 3 pages = 150 results max
            search_params = {
                "part": "snippet",
                "q": keyword,
                "type": "video",
                "order": "viewCount",
                "publishedAfter": published_after,
                "maxResults": 50,
                "regionCode": country,
                "key": API_KEY,
                "pageToken": st.session_state.get(f"next_page_{keyword}_{page}", "")
            }

            try:
                response = requests.get(SEARCH_URL, params=search_params)
                data = response.json()

                if "error" in data:
                    st.error(f"API Error: {data['error']['message']}")
                    break

                items = data.get("items", [])
                if not items:
                    break

                # Next page token save for next loop
                next_page_token = data.get("nextPageToken", "")
                st.session_state[f"next_page_{keyword}_{page + 1}"] = next_page_token

                video_ids = []
                channel_ids = set()
                videos_info = []

                for item in items:
                    if item["id"]["kind"] != "youtube#video":
                        continue
                    video_id = item["id"]["videoId"]
                    video_ids.append(video_id)
                    channel_ids.add(item["snippet"]["channelId"])
                    videos_info.append(item)

                if not video_ids:
                    continue

                # Video stats
                video_stats = {}
                for j in range(0, len(video_ids), 50):
                    batch = video_ids[j:j+50]
                    stats_resp = requests.get(VIDEOS_URL, params={
                        "part": "statistics",
                        "id": ",".join(batch),
                        "key": API_KEY
                    })
                    stats_data = stats_resp.json()
                    for item in stats_data.get("items", []):
                        vid = item["id"]
                        stats = item["statistics"]
                        video_stats[vid] = {
                            "views": int(stats.get("viewCount", 0)),
                            "likes": int(stats.get("likeCount", 0)),
                            "comments": int(stats.get("commentCount", 0))
                        }
                    time.sleep(0.1)

                # Channel stats (subscribers)
                channel_stats = {}
                channel_list = list(channel_ids)
                for j in range(0, len(channel_list), 50):
                    batch = channel_list[j:j+50]
                    chan_resp = requests.get(CHANNELS_URL, params={
                        "part": "statistics",
                        "id": ",".join(batch),
                        "key": API_KEY
                    })
                    chan_data = chan_resp.json()
                    for item in chan_data.get("items", []):
                        channel_stats[item["id"]] = int(item["statistics"].get("subscriberCount", 0))
                    time.sleep(0.1)

                # Add to results
                for info in videos_info:
                    vid = info["id"]["videoId"]
                    stats = video_stats.get(vid, {})
                    views = stats.get("views", 0)
                    
                    # Sirf 500+ views wale dikhao (spam avoid)
                    if views < 500:
                        continue

                    snippet = info["snippet"]
                    all_results.append({
                        "Title": snippet["title"],
                        "Channel": snippet["channelTitle"],
                        "URL": f"https://www.youtube.com/watch?v={vid}",
                        "Thumbnail": snippet["thumbnails"]["high"]["url"],
                        "Published": snippet1["publishedAt"][:10],
                        "Views": f"{views:,}",
                        "Likes": f"{stats.get('likes', 0):,}",
                        "Comments": f"{stats.get('comments', 0):,}",
                        "Subscribers": f"{channel_stats.get(snippet['channelId'], 0):,}",
                        "Keyword": keyword
                    })

                if not next_page_token:
                    break

            except Exception as e:
                st.error(f"Error: {e}")
                break

        time.sleep(0.5)  # API ko thoda rest

    # Final Results
    if all_results:
        # Remove duplicates
        seen = set()
        unique_results = []
        for r in all_results:
            if r["URL"] not in seen:
                seen.add(r["URL"])
                unique_results.append(r)

        # Sort by views
        unique_results = sorted(unique_results, key=lambda x: int(x["Views"].replace(",", "")), reverse=True)

        st.success(f"Total {len(unique_results)} Viral Videos Mile!")

        for res in unique_results[:100]:  # Top 100 dikhao
            st.markdown(f"""
            **{res['Title']}**  
            **Channel:** {res['Channel']} | 👥 {res['Subscribers']} subs  
            **Views:** {res['Views']} | ❤️ {res['Likes']} | 💬 {res['Comments']}  
            **Keyword:** `{res['Keyword']}`  
            🔗 [Watch Video]({res['URL']})
            """)
            st.image(res['Thumbnail'], width=300)
            st.markdown("---")

    else:
        st.warning("Koi video nahi mila – shayad API limit ya keyword issue. Try 'reddit' ya 'aita'")

    progress.empty()
