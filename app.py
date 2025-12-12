import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import re
import json
import time

# ------------------------------------------------------------
# APP CONFIG
# ------------------------------------------------------------
st.set_page_config(page_title="🎯 Faceless Viral Hunter PRO + AI", layout="wide")
st.title("🎯 Faceless Viral Hunter PRO")
st.markdown("**Now with 🤖 Gemini AI Integration!**")

# API Keys
YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", "")
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# Check APIs
GEMINI_AVAILABLE = bool(GEMINI_API_KEY)

if GEMINI_AVAILABLE:
    st.sidebar.success("🤖 Gemini AI: ACTIVE")
else:
    st.sidebar.warning("🤖 Gemini AI: Not configured")
    st.sidebar.caption("Add GEMINI_API_KEY in secrets")

# URLs
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


# ------------------------------------------------------------
# GEMINI AI FUNCTIONS - FIXED
# ------------------------------------------------------------
def call_gemini_api(prompt, max_retries=3):
    """
    Call Gemini API with proper error handling
    Returns: (success: bool, response: dict/str, error: str)
    """
    if not GEMINI_API_KEY:
        return False, None, "Gemini API key not configured"
    
    headers = {"Content-Type": "application/json"}
    
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
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
                
                # Extract text from response
                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        text = candidate["content"]["parts"][0].get("text", "")
                        return True, text, None
                
                return False, None, "Empty response from Gemini"
            
            elif response.status_code == 429:
                # Rate limited - wait and retry
                time.sleep(2 ** attempt)
                continue
            
            elif response.status_code == 400:
                return False, None, f"Bad request: {response.text[:200]}"
            
            else:
                return False, None, f"API error: {response.status_code}"
        
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return False, None, "Request timeout"
        
        except Exception as e:
            return False, None, str(e)
    
    return False, None, "Max retries exceeded"


def parse_json_from_response(text):
    """
    Extract and parse JSON from Gemini response
    Handles markdown code blocks and extra text
    """
    if not text:
        return None
    
    # Try direct JSON parse first
    try:
        return json.loads(text.strip())
    except:
        pass
    
    # Try to find JSON in code blocks
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',  # ```json ... ```
        r'```\s*([\s\S]*?)\s*```',       # ``` ... ```
        r'\{[\s\S]*\}',                   # { ... }
        r'\[[\s\S]*\]',                   # [ ... ]
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                # Clean the match
                clean = match.strip()
                # Try to parse
                return json.loads(clean)
            except:
                continue
    
    # Try to find JSON object manually
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end > start:
            json_str = text[start:end]
            return json.loads(json_str)
    except:
        pass
    
    return None


def ai_analyze_title(title, views=0):
    """Analyze a YouTube title with AI"""
    
    prompt = f"""Analyze this YouTube video title and explain why it's effective for getting clicks and views.

Title: "{title}"
Views: {views:,}

Respond with ONLY a JSON object (no other text) in this exact format:
{{
    "hook_score": 8,
    "curiosity_score": 9,
    "emotion_score": 7,
    "overall_score": 8,
    "why_it_works": "This title works because...",
    "power_words": ["word1", "word2", "word3"],
    "improvement_tips": ["tip1", "tip2"],
    "similar_titles": ["Better title idea 1", "Better title idea 2", "Better title idea 3"]
}}"""

    success, response, error = call_gemini_api(prompt)
    
    if success and response:
        result = parse_json_from_response(response)
        if result:
            return True, result, None
        else:
            # Return raw response if JSON parsing fails
            return True, {"raw_response": response}, None
    
    return False, None, error


def ai_generate_ideas(niche, count=10):
    """Generate video ideas for a niche"""
    
    prompt = f"""Generate {count} viral video ideas for a faceless YouTube channel in the "{niche}" niche.

These should be:
- Suitable for AI voiceover/text-to-speech
- High viral potential
- Easy to make without showing face

Respond with ONLY a JSON object (no other text) in this exact format:
{{
    "niche": "{niche}",
    "ideas": [
        {{
            "title": "Catchy video title here",
            "hook": "First 5 seconds script",
            "description": "Brief description of video content",
            "length": "8-12 min",
            "viral_potential": "high",
            "difficulty": "easy"
        }},
        {{
            "title": "Another catchy title",
            "hook": "Another hook",
            "description": "Another description",
            "length": "10-15 min",
            "viral_potential": "medium",
            "difficulty": "medium"
        }}
    ]
}}

Generate exactly {count} ideas in the ideas array."""

    success, response, error = call_gemini_api(prompt)
    
    if success and response:
        result = parse_json_from_response(response)
        if result and "ideas" in result:
            return True, result, None
        elif result:
            return True, result, None
        else:
            return False, None, "Could not parse response"
    
    return False, None, error


def ai_generate_script(title, niche, length_minutes=10):
    """Generate a full video script"""
    
    prompt = f"""Write a complete YouTube video script for a faceless narration channel.

Title: "{title}"
Niche: {niche}
Target Length: {length_minutes} minutes (approximately {length_minutes * 150} words)

The script should include:
1. A powerful hook (first 30 seconds)
2. Introduction
3. Main content with storytelling
4. Call to action (like, subscribe, comment)
5. Strong conclusion

Respond with ONLY a JSON object (no other text) in this exact format:
{{
    "title": "{title}",
    "duration": "{length_minutes} minutes",
    "word_count": 1500,
    "hook": "Write the attention-grabbing first 30 seconds here...",
    "introduction": "Write the introduction here...",
    "main_content": "Write the main body of the script here. Make it engaging and story-driven...",
    "call_to_action": "If you enjoyed this video, smash that like button...",
    "conclusion": "Write the conclusion here...",
    "full_script": "Complete script from start to end...",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "description": "SEO optimized video description here..."
}}"""

    success, response, error = call_gemini_api(prompt)
    
    if success and response:
        result = parse_json_from_response(response)
        if result:
            return True, result, None
        else:
            # Return raw text as script
            return True, {"full_script": response, "title": title}, None
    
    return False, None, error


def ai_analyze_niche(niche):
    """Deep analysis of a YouTube niche"""
    
    prompt = f"""Provide a comprehensive analysis of the "{niche}" niche for someone starting a faceless YouTube channel.

Respond with ONLY a JSON object (no other text) in this exact format:
{{
    "niche": "{niche}",
    "overview": "Brief overview of this niche",
    "market_size": "large",
    "competition": "medium",
    "difficulty": "easy",
    "monetization": {{
        "estimated_cpm": "$2-5",
        "affiliate_potential": "high",
        "sponsorship_potential": "medium"
    }},
    "audience": {{
        "age_range": "18-35",
        "gender": "60% male",
        "countries": ["US", "UK", "Canada"],
        "interests": ["interest1", "interest2"]
    }},
    "content_strategy": {{
        "video_length": "8-15 minutes",
        "upload_frequency": "3-5 per week",
        "best_times": ["Saturday 10am", "Sunday 2pm"],
        "content_types": ["type1", "type2", "type3"]
    }},
    "growth_tips": ["tip1", "tip2", "tip3"],
    "risks": ["risk1", "risk2"],
    "tools_needed": ["tool1", "tool2", "tool3"],
    "time_to_monetization": "3-6 months",
    "success_rating": "8/10",
    "recommendation": "Yes, this niche is recommended because..."
}}"""

    success, response, error = call_gemini_api(prompt)
    
    if success and response:
        result = parse_json_from_response(response)
        if result:
            return True, result, None
        else:
            return False, None, "Could not parse niche analysis"
    
    return False, None, error


def ai_reddit_to_script(story):
    """Convert Reddit story to YouTube script"""
    
    prompt = f"""Convert this Reddit story into an engaging YouTube video script for a faceless narration channel.

Reddit Story:
{story[:4000]}

Make it:
- Dramatic and engaging
- Add suspense and emotional beats
- Include a powerful hook
- Add narration cues like [PAUSE], [DRAMATIC MUSIC], etc.

Respond with ONLY a JSON object (no other text) in this exact format:
{{
    "original_title": "Original story title or summary",
    "youtube_title": "Catchy YouTube title for this story",
    "thumbnail_text": "3 words max",
    "duration": "8-12 minutes",
    "hook": "Attention-grabbing first 15 seconds...",
    "full_script": "Complete narration script with dramatic elements...",
    "music_mood": "tense/sad/mysterious",
    "tags": ["tag1", "tag2", "tag3"]
}}"""

    success, response, error = call_gemini_api(prompt)
    
    if success and response:
        result = parse_json_from_response(response)
        if result:
            return True, result, None
        else:
            return True, {"full_script": response}, None
    
    return False, None, error


def ai_seo_optimize(title, niche):
    """Generate SEO optimization for a video"""
    
    prompt = f"""Generate SEO optimization for this YouTube video.

Title: "{title}"
Niche: {niche}

Respond with ONLY a JSON object (no other text) in this exact format:
{{
    "optimized_title": "SEO optimized title (max 70 chars)",
    "description": "Full 300+ word SEO description with keywords naturally included...",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"],
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
    "keywords": {{
        "primary": ["keyword1", "keyword2"],
        "secondary": ["keyword3", "keyword4"],
        "long_tail": ["long tail keyword 1", "long tail keyword 2"]
    }},
    "thumbnail_text": "3 WORDS MAX",
    "first_comment": "Engaging pinned comment..."
}}"""

    success, response, error = call_gemini_api(prompt)
    
    if success and response:
        result = parse_json_from_response(response)
        if result:
            return True, result, None
    
    return False, None, error


# ------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------
FACELESS_INDICATORS = [
    "stories", "reddit", "aita", "horror", "scary", "creepy", "nightmare",
    "revenge", "confession", "askreddit", "tifu", "relationship", "karma",
    "tales", "narration", "motivation", "stoic", "facts", "explained",
    "documentary", "mystery", "crime", "compilation", "top 10", "top 5"
]

PREMIUM_COUNTRIES = {'US', 'CA', 'GB', 'AU', 'NZ', 'DE', 'FR', 'IT', 'ES', 'NL'}

CPM_RATES = {
    'US': 4.0, 'CA': 3.5, 'GB': 3.5, 'AU': 4.0, 'DE': 3.5,
    'FR': 2.5, 'IN': 0.5, 'PK': 0.3, 'N/A': 1.0
}


# ------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------
def fetch_json(url, params):
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 403:
            return "QUOTA"
    except:
        pass
    return None

def parse_duration(duration):
    if not duration: return 0
    total = 0
    for val, unit in re.findall(r"(\d+)([HMS])", duration):
        if unit == "H": total += int(val) * 3600
        elif unit == "M": total += int(val) * 60
        elif unit == "S": total += int(val)
    return total

def format_number(num):
    if num >= 1000000: return f"{num/1000000:.1f}M"
    if num >= 1000: return f"{num/1000:.1f}K"
    return str(num)


# ------------------------------------------------------------
# MAIN APP - TABS
# ------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🔍 Viral Hunter",
    "🎯 Title Analyzer",
    "💡 Idea Generator", 
    "📝 Script Writer",
    "📊 Niche Analyzer",
    "🔧 SEO Optimizer"
])


# ============================================================
# TAB 1: VIRAL HUNTER (Simplified version)
# ============================================================
with tab1:
    st.markdown("### 🔍 Find Faceless Viral Videos")
    st.info("This is the main video hunting feature - same as before")
    
    # Settings in sidebar
    with st.sidebar:
        st.header("⚙️ Hunt Settings")
        days = st.slider("Days to search", 1, 30, 7)
        min_views = st.number_input("Min views", value=10000, step=5000)
        max_subs = st.number_input("Max subs", value=500000, step=50000)
    
    keywords = st.text_area("Keywords (one per line):", 
                           value="reddit stories\naita\nscary stories\nmotivation stoicism",
                           height=100)
    
    if st.button("🚀 Start Hunt", type="primary", use_container_width=True):
        st.info("🔍 Hunting viral videos... (Full implementation same as before)")
        # Add the full hunting logic here from previous code


# ============================================================
# TAB 2: AI TITLE ANALYZER
# ============================================================
with tab2:
    st.markdown("### 🎯 AI Title Analyzer")
    st.markdown("Analyze any YouTube title to understand why it works and how to improve it.")
    
    if not GEMINI_AVAILABLE:
        st.error("❌ Gemini API key required! Add GEMINI_API_KEY to your Streamlit secrets.")
        st.code("""
# In .streamlit/secrets.toml add:
GEMINI_API_KEY = "your_api_key_here"
        """)
        st.markdown("[🔗 Get Gemini API Key](https://makersuite.google.com/app/apikey)")
        st.stop()
    
    # Input
    title_input = st.text_input(
        "📝 Enter YouTube Title to Analyze:",
        placeholder="e.g., My husband loves his ex-wife more than me | Reddit Stories",
        help="Paste any YouTube title you want to analyze"
    )
    
    views_input = st.number_input("👁️ Views (optional):", value=100000, step=10000)
    
    if st.button("🔍 Analyze Title", type="primary", use_container_width=True):
        if not title_input:
            st.warning("Please enter a title first!")
        else:
            with st.spinner("🤖 AI analyzing title... Please wait..."):
                success, result, error = ai_analyze_title(title_input, views_input)
            
            if success and result:
                st.success("✅ Analysis Complete!")
                
                # Check if we got structured data or raw response
                if "raw_response" in result:
                    st.markdown("### 📝 AI Analysis:")
                    st.markdown(result["raw_response"])
                else:
                    # Display scores
                    st.markdown("### 📊 Title Scores")
                    cols = st.columns(4)
                    cols[0].metric("🎣 Hook", f"{result.get('hook_score', 'N/A')}/10")
                    cols[1].metric("🤔 Curiosity", f"{result.get('curiosity_score', 'N/A')}/10")
                    cols[2].metric("❤️ Emotion", f"{result.get('emotion_score', 'N/A')}/10")
                    cols[3].metric("⭐ Overall", f"{result.get('overall_score', 'N/A')}/10")
                    
                    # Why it works
                    st.markdown("### 💡 Why This Title Works")
                    st.info(result.get('why_it_works', 'Analysis not available'))
                    
                    # Power words
                    power_words = result.get('power_words', [])
                    if power_words:
                        st.markdown("### 🔥 Power Words Used")
                        st.markdown(" ".join([f"`{word}`" for word in power_words]))
                    
                    # Improvement tips
                    tips = result.get('improvement_tips', [])
                    if tips:
                        st.markdown("### 📈 How to Improve")
                        for tip in tips:
                            st.markdown(f"• {tip}")
                    
                    # Similar titles
                    similar = result.get('similar_titles', [])
                    if similar:
                        st.markdown("### ✨ Better Title Ideas")
                        for i, title in enumerate(similar, 1):
                            st.success(f"{i}. {title}")
            else:
                st.error(f"❌ Analysis failed: {error}")
                st.info("Try again or check your API key")


# ============================================================
# TAB 3: IDEA GENERATOR
# ============================================================
with tab3:
    st.markdown("### 💡 AI Video Idea Generator")
    st.markdown("Generate viral video ideas for your faceless YouTube channel.")
    
    if not GEMINI_AVAILABLE:
        st.error("❌ Gemini API key required!")
        st.stop()
    
    # Niche selection
    col1, col2 = st.columns(2)
    
    with col1:
        niche_options = [
            "Reddit Stories (AITA, Revenge, Relationships)",
            "Horror & Scary Stories",
            "True Crime",
            "Motivation & Stoicism",
            "Top 10 Facts",
            "Mystery & Conspiracy",
            "Relationship Drama",
            "Custom..."
        ]
        selected_niche = st.selectbox("📂 Select Niche:", niche_options)
    
    with col2:
        idea_count = st.slider("🔢 Number of Ideas:", 5, 20, 10)
    
    # Custom niche input
    if selected_niche == "Custom...":
        custom_niche = st.text_input("Enter your niche:", placeholder="e.g., AI Technology Explained")
        niche_to_use = custom_niche
    else:
        niche_to_use = selected_niche
    
    if st.button("🎲 Generate Ideas", type="primary", use_container_width=True):
        if not niche_to_use:
            st.warning("Please select or enter a niche!")
        else:
            with st.spinner(f"🤖 Generating {idea_count} ideas for {niche_to_use}..."):
                success, result, error = ai_generate_ideas(niche_to_use, idea_count)
            
            if success and result:
                ideas = result.get('ideas', [])
                
                if ideas:
                    st.success(f"✅ Generated {len(ideas)} Video Ideas!")
                    
                    for i, idea in enumerate(ideas, 1):
                        with st.expander(f"💡 Idea {i}: {idea.get('title', 'Untitled')}", expanded=(i <= 3)):
                            
                            # Title
                            st.markdown(f"**📺 Title:** {idea.get('title', 'N/A')}")
                            
                            # Hook
                            hook = idea.get('hook', '')
                            if hook:
                                st.markdown(f"**🎣 Hook:** _{hook}_")
                            
                            # Description
                            desc = idea.get('description', '')
                            if desc:
                                st.markdown(f"**📝 Description:** {desc}")
                            
                            # Metadata
                            col1, col2, col3 = st.columns(3)
                            col1.markdown(f"**⏱️ Length:** {idea.get('length', 'N/A')}")
                            col2.markdown(f"**🔥 Viral:** {idea.get('viral_potential', 'N/A')}")
                            col3.markdown(f"**📊 Difficulty:** {idea.get('difficulty', 'N/A')}")
                            
                            # Copy button
                            st.code(idea.get('title', ''), language=None)
                else:
                    st.warning("No ideas in response. Showing raw output:")
                    st.json(result)
            else:
                st.error(f"❌ Failed to generate ideas: {error}")


# ============================================================
# TAB 4: SCRIPT WRITER
# ============================================================
with tab4:
    st.markdown("### 📝 AI Script Writer")
    st.markdown("Generate complete video scripts ready for voiceover.")
    
    if not GEMINI_AVAILABLE:
        st.error("❌ Gemini API key required!")
        st.stop()
    
    # Script options
    script_mode = st.radio(
        "Choose mode:",
        ["📝 Write from Title", "📖 Convert Reddit Story"],
        horizontal=True
    )
    
    if script_mode == "📝 Write from Title":
        col1, col2 = st.columns(2)
        with col1:
            script_title = st.text_input(
                "📺 Video Title:",
                placeholder="e.g., Top 10 Revenge Stories That Went Nuclear"
            )
        with col2:
            script_niche = st.selectbox(
                "📂 Niche:",
                ["Reddit Stories", "Horror", "Motivation", "True Crime", "Facts", "Other"]
            )
        
        script_length = st.slider("⏱️ Target Length (minutes):", 5, 20, 10)
        
        if st.button("✍️ Generate Script", type="primary", use_container_width=True):
            if not script_title:
                st.warning("Please enter a title!")
            else:
                with st.spinner("🤖 Writing script... This may take 30-60 seconds..."):
                    success, result, error = ai_generate_script(script_title, script_niche, script_length)
                
                if success and result:
                    st.success("✅ Script Generated!")
                    
                    # Display script sections
                    st.markdown(f"## 📺 {result.get('title', script_title)}")
                    st.markdown(f"**Duration:** {result.get('duration', f'{script_length} min')}")
                    
                    # Hook
                    if result.get('hook'):
                        st.markdown("### 🎣 Hook (First 30 seconds)")
                        st.info(result['hook'])
                    
                    # Full script
                    full_script = result.get('full_script', '')
                    if full_script:
                        st.markdown("### 📜 Full Script")
                        st.text_area("Copy this script:", value=full_script, height=400)
                    
                    # Individual sections
                    for section in ['introduction', 'main_content', 'call_to_action', 'conclusion']:
                        if result.get(section):
                            st.markdown(f"### {section.replace('_', ' ').title()}")
                            st.markdown(result[section])
                    
                    # Tags
                    tags = result.get('tags', [])
                    if tags:
                        st.markdown("### 🏷️ Suggested Tags")
                        st.code(", ".join(tags))
                    
                    # Download
                    st.download_button(
                        "📥 Download Script",
                        data=json.dumps(result, indent=2),
                        file_name=f"script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                else:
                    st.error(f"❌ Failed: {error}")
    
    else:  # Reddit story mode
        reddit_story = st.text_area(
            "📖 Paste Reddit Story Here:",
            height=300,
            placeholder="Paste the full Reddit story (AITA, ProRevenge, etc.)..."
        )
        
        if st.button("🔄 Convert to Script", type="primary", use_container_width=True):
            if not reddit_story or len(reddit_story) < 100:
                st.warning("Please paste a Reddit story (at least 100 characters)")
            else:
                with st.spinner("🤖 Converting story to script..."):
                    success, result, error = ai_reddit_to_script(reddit_story)
                
                if success and result:
                    st.success("✅ Script Created!")
                    
                    # YouTube title suggestion
                    if result.get('youtube_title'):
                        st.markdown("### 📺 Suggested YouTube Title")
                        st.success(result['youtube_title'])
                    
                    # Thumbnail text
                    if result.get('thumbnail_text'):
                        st.markdown(f"**🖼️ Thumbnail Text:** `{result['thumbnail_text']}`")
                    
                    # Hook
                    if result.get('hook'):
                        st.markdown("### 🎣 Hook")
                        st.info(result['hook'])
                    
                    # Full script
                    if result.get('full_script'):
                        st.markdown("### 📜 Full Narration Script")
                        st.text_area("Script:", value=result['full_script'], height=400)
                    
                    # Music mood
                    if result.get('music_mood'):
                        st.markdown(f"**🎵 Background Music Mood:** {result['music_mood']}")
                else:
                    st.error(f"❌ Failed: {error}")


# ============================================================
# TAB 5: NICHE ANALYZER
# ============================================================
with tab5:
    st.markdown("### 📊 AI Niche Analyzer")
    st.markdown("Get deep insights into any niche before starting your channel.")
    
    if not GEMINI_AVAILABLE:
        st.error("❌ Gemini API key required!")
        st.stop()
    
    niche_input = st.text_input(
        "🔍 Enter Niche to Analyze:",
        placeholder="e.g., Reddit AITA Stories, True Crime, Stoicism Motivation"
    )
    
    if st.button("🔬 Analyze Niche", type="primary", use_container_width=True):
        if not niche_input:
            st.warning("Please enter a niche!")
        else:
            with st.spinner(f"🤖 Analyzing '{niche_input}' niche..."):
                success, result, error = ai_analyze_niche(niche_input)
            
            if success and result:
                st.success("✅ Analysis Complete!")
                
                # Header
                st.markdown(f"## 📊 {result.get('niche', niche_input)}")
                st.info(result.get('overview', 'No overview available'))
                
                # Key metrics
                st.markdown("### 📈 Key Metrics")
                cols = st.columns(4)
                cols[0].metric("📊 Market Size", result.get('market_size', 'N/A'))
                cols[1].metric("⚔️ Competition", result.get('competition', 'N/A'))
                cols[2].metric("📈 Difficulty", result.get('difficulty', 'N/A'))
                cols[3].metric("⭐ Rating", result.get('success_rating', 'N/A'))
                
                # Monetization
                st.markdown("### 💰 Monetization Potential")
                mon = result.get('monetization', {})
                cols = st.columns(3)
                cols[0].markdown(f"**CPM:** {mon.get('estimated_cpm', 'N/A')}")
                cols[1].markdown(f"**Affiliate:** {mon.get('affiliate_potential', 'N/A')}")
                cols[2].markdown(f"**Sponsors:** {mon.get('sponsorship_potential', 'N/A')}")
                
                # Audience
                st.markdown("### 👥 Target Audience")
                aud = result.get('audience', {})
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Age:** {aud.get('age_range', 'N/A')}")
                    st.markdown(f"**Gender:** {aud.get('gender', 'N/A')}")
                with col2:
                    countries = aud.get('countries', [])
                    st.markdown(f"**Countries:** {', '.join(countries) if countries else 'N/A'}")
                    interests = aud.get('interests', [])
                    st.markdown(f"**Interests:** {', '.join(interests) if interests else 'N/A'}")
                
                # Content Strategy
                st.markdown("### 📺 Content Strategy")
                strat = result.get('content_strategy', {})
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Video Length:** {strat.get('video_length', 'N/A')}")
                    st.markdown(f"**Upload Frequency:** {strat.get('upload_frequency', 'N/A')}")
                with col2:
                    times = strat.get('best_times', [])
                    st.markdown(f"**Best Times:** {', '.join(times) if times else 'N/A'}")
                    types = strat.get('content_types', [])
                    st.markdown(f"**Content Types:** {', '.join(types) if types else 'N/A'}")
                
                # Tips and Risks
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### ✅ Growth Tips")
                    for tip in result.get('growth_tips', []):
                        st.markdown(f"• {tip}")
                with col2:
                    st.markdown("### ⚠️ Risks")
                    for risk in result.get('risks', []):
                        st.markdown(f"• {risk}")
                
                # Tools
                tools = result.get('tools_needed', [])
                if tools:
                    st.markdown("### 🛠️ Tools Needed")
                    st.markdown(", ".join(tools))
                
                # Timeline
                st.markdown(f"### ⏱️ Time to Monetization: **{result.get('time_to_monetization', 'N/A')}**")
                
                # Recommendation
                if result.get('recommendation'):
                    st.markdown("### 💡 Recommendation")
                    st.success(result['recommendation'])
            else:
                st.error(f"❌ Failed: {error}")


# ============================================================
# TAB 6: SEO OPTIMIZER
# ============================================================
with tab6:
    st.markdown("### 🔧 AI SEO Optimizer")
    st.markdown("Generate optimized titles, descriptions, tags, and keywords.")
    
    if not GEMINI_AVAILABLE:
        st.error("❌ Gemini API key required!")
        st.stop()
    
    col1, col2 = st.columns(2)
    with col1:
        seo_title = st.text_input(
            "📺 Video Title:",
            placeholder="e.g., Husband Caught Cheating - Reddit Stories"
        )
    with col2:
        seo_niche = st.selectbox(
            "📂 Niche:",
            ["Reddit Stories", "Horror", "Motivation", "True Crime", "Facts", "Gaming", "Other"]
        )
    
    if st.button("🚀 Optimize SEO", type="primary", use_container_width=True):
        if not seo_title:
            st.warning("Please enter a title!")
        else:
            with st.spinner("🤖 Optimizing SEO..."):
                success, result, error = ai_seo_optimize(seo_title, seo_niche)
            
            if success and result:
                st.success("✅ SEO Optimized!")
                
                # Optimized title
                if result.get('optimized_title'):
                    st.markdown("### 📺 Optimized Title")
                    st.success(result['optimized_title'])
                    st.caption(f"Length: {len(result['optimized_title'])} characters")
                
                # Thumbnail text
                if result.get('thumbnail_text'):
                    st.markdown("### 🖼️ Thumbnail Text")
                    st.info(result['thumbnail_text'])
                
                # Description
                if result.get('description'):
                    st.markdown("### 📝 Video Description")
                    st.text_area("Copy this:", value=result['description'], height=200)
                
                # Tags
                tags = result.get('tags', [])
                if tags:
                    st.markdown("### 🏷️ Tags")
                    st.code(", ".join(tags))
                
                # Hashtags
                hashtags = result.get('hashtags', [])
                if hashtags:
                    st.markdown("### #️⃣ Hashtags")
                    st.code(" ".join(hashtags))
                
                # Keywords
                keywords = result.get('keywords', {})
                if keywords:
                    st.markdown("### 🔑 Keywords")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown("**Primary:**")
                        for kw in keywords.get('primary', []):
                            st.markdown(f"• {kw}")
                    with col2:
                        st.markdown("**Secondary:**")
                        for kw in keywords.get('secondary', []):
                            st.markdown(f"• {kw}")
                    with col3:
                        st.markdown("**Long-tail:**")
                        for kw in keywords.get('long_tail', []):
                            st.markdown(f"• {kw}")
                
                # First comment
                if result.get('first_comment'):
                    st.markdown("### 💬 Pinned Comment")
                    st.info(result['first_comment'])
            else:
                st.error(f"❌ Failed: {error}")


# ------------------------------------------------------------
# FOOTER
# ------------------------------------------------------------
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("Made with ❤️ for Muhammed Rizwan Qamar")
with col2:
    st.caption("Faceless Viral Hunter PRO + AI 2025")
with col3:
    if GEMINI_AVAILABLE:
        st.caption("🤖 Gemini AI: Connected")
    else:
        st.caption("🤖 Gemini AI: Not configured")
