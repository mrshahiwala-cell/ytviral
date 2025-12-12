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

# Initialize session state
if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'quota_used' not in st.session_state:
    st.session_state.quota_used = 0
if 'last_search' not in st.session_state:
    st.session_state.last_search = ""

API_KEY = st.secrets["YOUTUBE_API_KEY"]

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

# Settings
MAX_KEYWORDS = 5  # Maximum 5 keywords/niches/titles for search (quota save)
# No limit on results - show all channels found

# ------------------------------------------------------------
# COUNTRIES & CPM RATES
# ------------------------------------------------------------
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


# ------------------------------------------------------------
# QUOTA TRACKING
# ------------------------------------------------------------
def add_quota(units):
    st.session_state.quota_used += units


# ------------------------------------------------------------
# COMPLETE HTML REPORT GENERATOR
# ------------------------------------------------------------
def generate_html_report(df, search_query):
    """Generate complete beautiful HTML report with all details"""
    
    total_views = df['Views'].sum() if len(df) > 0 else 0
    total_subs = df['Subs'].sum() if len(df) > 0 else 0
    avg_virality = df['Virality'].mean() if len(df) > 0 else 0
    avg_quality = df['QualityScore'].mean() if 'QualityScore' in df.columns and len(df) > 0 else 0
    monetized_count = len(df[df['MonetizationScore'] >= 70]) if len(df) > 0 else 0
    total_revenue = df['EstRevenue'].sum() if 'EstRevenue' in df.columns and len(df) > 0 else 0
    total_videos_all = df['TotalVideos'].sum() if len(df) > 0 else 0
    total_shorts = df['ShortsCount'].sum() if 'ShortsCount' in df.columns and len(df) > 0 else 0
    total_medium = df['MediumCount'].sum() if 'MediumCount' in df.columns and len(df) > 0 else 0
    total_long = df['LongCount'].sum() if 'LongCount' in df.columns and len(df) > 0 else 0
    
    # Niche breakdown
    niche_counts = df['Niche'].value_counts().to_dict() if 'Niche' in df.columns else {}
    
    # Country breakdown
    country_counts = df['Country'].value_counts().to_dict() if 'Country' in df.columns else {}
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Faceless Viral Hunter PRO Report - {search_query}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
            min-height: 100vh;
            color: #e4e4e4;
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        
        /* Header */
        .header {{
            text-align: center;
            padding: 50px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            border-radius: 24px;
            margin-bottom: 40px;
            box-shadow: 0 20px 60px rgba(102, 126, 234, 0.4);
            position: relative;
            overflow: hidden;
        }}
        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
        }}
        .header h1 {{ font-size: 3rem; font-weight: 800; margin-bottom: 15px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); position: relative; }}
        .header p {{ opacity: 0.95; font-size: 1.2rem; position: relative; }}
        .search-badge {{ 
            background: rgba(0,0,0,0.3); 
            padding: 15px 35px; 
            border-radius: 30px; 
            display: inline-block; 
            margin-top: 20px; 
            font-size: 1.2rem;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            position: relative;
        }}
        
        /* Summary Stats */
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.03);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 28px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.08);
            transition: all 0.3s ease;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(102, 126, 234, 0.2);
            border-color: rgba(102, 126, 234, 0.3);
        }}
        .stat-card .number {{
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #667eea, #764ba2, #f093fb);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .stat-card .label {{ font-size: 0.9rem; color: #888; margin-top: 8px; font-weight: 500; }}
        
        /* Breakdown Section */
        .breakdown-section {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
            margin-bottom: 40px;
        }}
        .breakdown-card {{
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.08);
        }}
        .breakdown-card h3 {{
            font-size: 1.2rem;
            margin-bottom: 20px;
            color: #667eea;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .breakdown-item {{
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        .breakdown-item:last-child {{ border-bottom: none; }}
        .breakdown-item .name {{ color: #ccc; }}
        .breakdown-item .value {{ font-weight: 600; color: #fff; }}
        
        /* Section Title */
        .section-title {{
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 3px solid rgba(102, 126, 234, 0.3);
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        /* Video Cards */
        .video-card {{
            background: rgba(255,255,255,0.02);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 25px;
            border: 1px solid rgba(255,255,255,0.06);
            transition: all 0.3s ease;
        }}
        .video-card:hover {{
            background: rgba(255,255,255,0.05);
            border-color: rgba(102, 126, 234, 0.3);
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}
        .video-header {{ display: flex; gap: 25px; margin-bottom: 25px; align-items: flex-start; }}
        .rank {{ 
            font-size: 2.5rem; 
            font-weight: 800; 
            min-width: 80px; 
            text-align: center;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .thumbnail {{ 
            width: 220px; 
            height: 124px; 
            border-radius: 14px; 
            object-fit: cover; 
            flex-shrink: 0;
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }}
        .video-info {{ flex: 1; }}
        .video-title {{ 
            font-size: 1.3rem; 
            font-weight: 700; 
            margin-bottom: 12px; 
            color: #fff;
            line-height: 1.4;
        }}
        .video-title a {{ color: #fff; text-decoration: none; }}
        .video-title a:hover {{ color: #667eea; }}
        .channel-name {{ 
            display: inline-block; 
            color: #667eea; 
            text-decoration: none; 
            font-weight: 600; 
            margin-bottom: 10px;
            font-size: 1.1rem;
        }}
        .channel-name:hover {{ text-decoration: underline; }}
        .video-meta {{ font-size: 0.95rem; color: #999; line-height: 1.8; }}
        
        /* Video Breakdown Box */
        .video-breakdown {{
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
            border: 1px solid rgba(102, 126, 234, 0.2);
            border-radius: 14px;
            padding: 20px 25px;
            margin: 20px 0;
        }}
        .video-breakdown-title {{ 
            font-weight: 700; 
            margin-bottom: 12px; 
            color: #667eea;
            font-size: 1rem;
        }}
        .video-breakdown-stats {{ 
            display: flex; 
            gap: 30px; 
            flex-wrap: wrap;
        }}
        .breakdown-stat {{ 
            font-size: 0.95rem;
            color: #ccc;
        }}
        .breakdown-stat strong {{ color: #fff; }}
        
        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-item {{ 
            background: rgba(255,255,255,0.04); 
            border-radius: 12px; 
            padding: 18px 12px; 
            text-align: center;
            border: 1px solid rgba(255,255,255,0.05);
        }}
        .stat-value {{ font-size: 1.4rem; font-weight: 700; color: #fff; }}
        .stat-label {{ font-size: 0.75rem; color: #888; margin-top: 6px; font-weight: 500; }}
        
        /* Badges */
        .badges {{ margin: 15px 0; }}
        .badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 25px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-right: 10px;
            margin-bottom: 10px;
        }}
        .badge-green {{ background: rgba(40, 167, 69, 0.2); color: #28a745; border: 1px solid rgba(40, 167, 69, 0.3); }}
        .badge-yellow {{ background: rgba(255, 193, 7, 0.2); color: #ffc107; border: 1px solid rgba(255, 193, 7, 0.3); }}
        .badge-blue {{ background: rgba(102, 126, 234, 0.2); color: #667eea; border: 1px solid rgba(102, 126, 234, 0.3); }}
        .badge-purple {{ background: rgba(156, 39, 176, 0.2); color: #ab47bc; border: 1px solid rgba(156, 39, 176, 0.3); }}
        .badge-orange {{ background: rgba(255, 152, 0, 0.2); color: #ff9800; border: 1px solid rgba(255, 152, 0, 0.3); }}
        
        /* Action Buttons */
        .action-links {{ margin-top: 20px; display: flex; gap: 12px; flex-wrap: wrap; }}
        .action-link {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 10px;
            font-size: 0.95rem;
            font-weight: 600;
            transition: all 0.3s ease;
        }}
        .action-link:hover {{ 
            transform: translateY(-3px); 
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4); 
        }}
        .action-link.secondary {{ 
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .action-link.secondary:hover {{
            background: rgba(255,255,255,0.15);
        }}
        
        /* Footer */
        .footer {{ 
            text-align: center; 
            padding: 40px; 
            margin-top: 50px; 
            color: #666; 
            font-size: 0.95rem;
            border-top: 1px solid rgba(255,255,255,0.05);
        }}
        .footer p {{ margin: 8px 0; }}
        .footer .made-with {{ color: #888; font-size: 1rem; }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 2rem; }}
            .video-header {{ flex-direction: column; }}
            .thumbnail {{ width: 100%; height: auto; aspect-ratio: 16/9; }}
            .rank {{ font-size: 1.8rem; }}
        }}
        
        /* Print Styles */
        @media print {{
            body {{ background: white; color: black; }}
            .video-card {{ break-inside: avoid; border: 1px solid #ddd; }}
            .action-links {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🎯 Faceless Viral Hunter PRO</h1>
            <p>Complete Analysis Report</p>
            <p style="font-size: 0.95rem; opacity: 0.8;">Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
            <div class="search-badge">🔍 Search: <strong>{search_query}</strong></div>
        </div>
        
        <!-- Summary Stats -->
        <div class="summary-grid">
            <div class="stat-card">
                <div class="number">{len(df)}</div>
                <div class="label">📊 Channels Found</div>
            </div>
            <div class="stat-card">
                <div class="number">{total_views:,.0f}</div>
                <div class="label">👁️ Total Views</div>
            </div>
            <div class="stat-card">
                <div class="number">{total_subs:,.0f}</div>
                <div class="label">👥 Total Subscribers</div>
            </div>
            <div class="stat-card">
                <div class="number">{avg_virality:,.0f}/day</div>
                <div class="label">🔥 Avg Virality</div>
            </div>
            <div class="stat-card">
                <div class="number">{avg_quality:.1f}</div>
                <div class="label">⭐ Avg Quality Score</div>
            </div>
            <div class="stat-card">
                <div class="number">{monetized_count}</div>
                <div class="label">💰 Monetized Channels</div>
            </div>
            <div class="stat-card">
                <div class="number">${total_revenue:,.0f}</div>
                <div class="label">💵 Est. Total Revenue</div>
            </div>
        </div>
        
        <!-- Video Breakdown Summary -->
        <div class="breakdown-section">
            <div class="breakdown-card">
                <h3>📊 Total Video Breakdown</h3>
                <div class="breakdown-item">
                    <span class="name">🎬 Total Videos</span>
                    <span class="value">{total_videos_all:,}</span>
                </div>
                <div class="breakdown-item">
                    <span class="name">📱 Shorts (<1 min)</span>
                    <span class="value">{total_shorts:,}</span>
                </div>
                <div class="breakdown-item">
                    <span class="name">⏱️ Medium (1-5 min)</span>
                    <span class="value">{total_medium:,}</span>
                </div>
                <div class="breakdown-item">
                    <span class="name">🎥 Long (5+ min)</span>
                    <span class="value">{total_long:,}</span>
                </div>
            </div>
            
            <div class="breakdown-card">
                <h3>📂 Niche Distribution</h3>
"""
    
    for niche, count in list(niche_counts.items())[:6]:
        html += f"""
                <div class="breakdown-item">
                    <span class="name">{niche}</span>
                    <span class="value">{count}</span>
                </div>
"""
    
    html += """
            </div>
            
            <div class="breakdown-card">
                <h3>🌍 Country Distribution</h3>
"""
    
    for country, count in list(country_counts.items())[:6]:
        html += f"""
                <div class="breakdown-item">
                    <span class="name">{country}</span>
                    <span class="value">{count}</span>
                </div>
"""
    
    html += f"""
            </div>
        </div>
        
        <!-- Channel Results -->
        <h2 class="section-title">🎬 All {len(df)} Channels</h2>
"""
    
    for idx, row in df.iterrows():
        # Rank emoji
        if idx == 0:
            rank_emoji = "🏆"
        elif idx == 1:
            rank_emoji = "🥈"
        elif idx == 2:
            rank_emoji = "🥉"
        else:
            rank_emoji = "⭐"
        
        # Monetization badge
        if row['MonetizationScore'] >= 70:
            mon_class = "badge-green"
            mon_text = "🟢 Monetized"
        elif row['MonetizationScore'] >= 50:
            mon_class = "badge-yellow"
            mon_text = "🟡 Likely Monetized"
        else:
            mon_class = "badge-orange"
            mon_text = "🟠 Possibly"
        
        html += f"""
        <div class="video-card">
            <div class="video-header">
                <div class="rank">{rank_emoji}#{idx+1}</div>
                <img src="{row['Thumb']}" alt="Thumbnail" class="thumbnail" loading="lazy">
                <div class="video-info">
                    <h3 class="video-title">
                        <a href="{row['Link']}" target="_blank">{row['Title']}</a>
                    </h3>
                    <a href="{row['ChannelLink']}" target="_blank" class="channel-name">📺 {row['Channel']}</a>
                    <div class="video-meta">
                        🌍 {row['Country']} &nbsp;•&nbsp; 
                        📅 Channel Created: {row['ChCreated']} &nbsp;•&nbsp;
                        ⏰ Age: {row.get('ChannelAge', 'N/A')} &nbsp;•&nbsp;
                        📂 {row['Niche']}
                    </div>
                    <div class="video-meta">
                        📤 Video Uploaded: {row['Uploaded']} &nbsp;•&nbsp;
                        ⏱️ Duration: {row['DurationStr']} ({row['Type']}) &nbsp;•&nbsp;
                        🔑 Keyword: {row['Keyword']}
                    </div>
                </div>
            </div>
            
            <div class="video-breakdown">
                <div class="video-breakdown-title">📊 Channel Video Breakdown</div>
                <div class="video-breakdown-stats">
                    <div class="breakdown-stat">🎬 <strong>Total:</strong> {row['TotalVideos']}</div>
                    <div class="breakdown-stat">📱 <strong>Shorts:</strong> {row.get('ShortsCount', 0)}</div>
                    <div class="breakdown-stat">⏱️ <strong>Medium:</strong> {row.get('MediumCount', 0)}</div>
                    <div class="breakdown-stat">🎥 <strong>Long:</strong> {row.get('LongCount', 0)}</div>
                    <div class="breakdown-stat">📊 <strong>Avg Views:</strong> {row.get('AvgViews', 0):,.0f}</div>
                </div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-item"><div class="stat-value">{row['Views']:,}</div><div class="stat-label">👁️ Views</div></div>
                <div class="stat-item"><div class="stat-value">{row['Subs']:,}</div><div class="stat-label">👥 Subscribers</div></div>
                <div class="stat-item"><div class="stat-value">{row['Virality']:,.0f}/d</div><div class="stat-label">🔥 Virality</div></div>
                <div class="stat-item"><div class="stat-value">{row['Engagement%']}%</div><div class="stat-label">💬 Engagement</div></div>
                <div class="stat-item"><div class="stat-value">{row.get('QualityScore', 0):.0f}</div><div class="stat-label">⭐ Quality</div></div>
                <div class="stat-item"><div class="stat-value">{row['FacelessScore']}%</div><div class="stat-label">🎭 Faceless</div></div>
                <div class="stat-item"><div class="stat-value">${row['EstRevenue']:,.0f}</div><div class="stat-label">💵 Revenue</div></div>
                <div class="stat-item"><div class="stat-value">{row.get('UploadsPerWeek', 0):.1f}/wk</div><div class="stat-label">📤 Uploads</div></div>
            </div>
            
            <div class="badges">
                <span class="badge {mon_class}">{mon_text} ({row['MonetizationScore']}%)</span>
                <span class="badge badge-blue">✅ Faceless ({row['FacelessScore']}%)</span>
                <span class="badge badge-purple">📂 {row['Niche']}</span>
                <span class="badge badge-orange">🌍 {row['Country']}</span>
            </div>
            
            <div class="action-links">
                <a href="{row['Link']}" target="_blank" class="action-link">▶️ Watch Video</a>
                <a href="{row['ChannelLink']}" target="_blank" class="action-link secondary">📺 View Channel</a>
            </div>
        </div>
"""
    
    html += f"""
        <!-- Footer -->
        <div class="footer">
            <p class="made-with">🎯 Faceless Viral Hunter PRO Report</p>
            <p>Made with ❤️ for <strong>Muhammed Rizwan Qamar</strong></p>
            <p style="margin-top: 15px; font-size: 0.85rem; color: #555;">
                📊 Quota Used: {st.session_state.quota_used:,} units | 
                🔍 Search: {search_query} | 
                📅 Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
            </p>
        </div>
    </div>
</body>
</html>
"""
    return html


# ------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------
def fetch_json(url, params, quota_cost=0):
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            if quota_cost > 0:
                add_quota(quota_cost)
            return resp.json()
        if "quotaExceeded" in resp.text or resp.status_code == 403:
            return "QUOTA"
    except:
        pass
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
    score = 0
    subs = channel_data.get("subs", 0)
    total_videos = channel_data.get("video_count", 0)
    created = channel_data.get("created", "")
    country = channel_data.get("country", "N/A")
    total_views = channel_data.get("total_views", 0)
    
    if subs >= 1000:
        score += 35
    elif subs >= 500:
        score += 15
    
    if created:
        try:
            created_date = datetime.strptime(created[:19], "%Y-%m-%dT%H:%M:%S")
            days_old = (datetime.utcnow() - created_date).days
            if days_old >= 30:
                score += 15
        except:
            pass
    
    estimated_watch_hours = (total_views * 3.2) / 60
    if estimated_watch_hours >= 4000:
        score += 30
    elif estimated_watch_hours >= 2000:
        score += 15
    
    if country in MONETIZATION_COUNTRIES:
        score += 15
    
    if total_videos >= 30:
        score += 5
    
    if score >= 70:
        status = "🟢 LIKELY MONETIZED"
    elif score >= 50:
        status = "🟡 POSSIBLY MONETIZED"
    elif score >= 30:
        status = "🟠 CLOSE TO MONETIZATION"
    else:
        status = "🔴 NOT MONETIZED"
    
    return status, min(score, 100)


def detect_faceless_advanced(channel_data, strictness="Normal"):
    score = 0
    profile_url = channel_data.get("profile", "")
    banner_url = channel_data.get("banner", "")
    channel_name = channel_data.get("name", "").lower()
    description = channel_data.get("description", "").lower()
    
    if "default.jpg" in profile_url or "s88-c-k-c0x00ffffff-no-rj" in profile_url:
        score += 30
    
    if not banner_url:
        score += 20
    
    name_matches = sum(1 for kw in FACELESS_INDICATORS if kw in channel_name)
    if name_matches >= 1:
        score += min(name_matches * 15, 30)
    
    desc_matches = sum(1 for kw in FACELESS_DESCRIPTION_KEYWORDS if kw in description)
    if desc_matches >= 1:
        score += min(desc_matches * 10, 25)
    
    thresholds = {"Relaxed": 20, "Normal": 35, "Strict": 55}
    threshold = thresholds.get(strictness, 35)
    
    return score >= threshold, min(score, 100)


def get_video_type_label(duration):
    if duration < 60:
        return "Shorts"
    elif duration < 300:
        return "Medium"
    return "Long"


def estimate_revenue(views, country, video_count):
    cpm = CPM_RATES.get(country, 1.0)
    monetized_views = views * 0.55
    revenue = (monetized_views / 1000) * cpm
    return round(revenue, 2)


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
        "Mystery": ["mystery", "mysteries", "unsolved", "conspiracy"]
    }
    for niche, keywords in niches.items():
        if any(kw in text for kw in keywords):
            return niche
    return "Other"


def calculate_quality_score(views, virality, engagement, mon_score, faceless_score, subs, avg_views):
    score = 0
    
    if virality >= 10000: score += 25
    elif virality >= 5000: score += 20
    elif virality >= 2000: score += 15
    elif virality >= 1000: score += 10
    elif virality >= 500: score += 5
    
    if engagement >= 10: score += 20
    elif engagement >= 5: score += 15
    elif engagement >= 2: score += 10
    elif engagement >= 1: score += 5
    
    score += mon_score * 0.2
    score += faceless_score * 0.15
    
    if 5000 <= subs <= 50000: score += 10
    elif 1000 <= subs < 5000: score += 7
    else: score += 5
    
    if avg_views >= 20000: score += 10
    elif avg_views >= 10000: score += 8
    elif avg_views >= 5000: score += 5
    
    return min(round(score, 1), 100)


def batch_fetch_channels(channel_ids, api_key, cache):
    new_ids = [cid for cid in channel_ids if cid not in cache]
    if not new_ids:
        return cache, False
    
    for i in range(0, len(new_ids), 50):
        batch = new_ids[i:i+50]
        params = {
            "part": "snippet,statistics,brandingSettings",
            "id": ",".join(batch),
            "key": api_key
        }
        data = fetch_json(CHANNELS_URL, params, quota_cost=1)
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
                "banner": brand_img.get("bannerExternalUrl", "")
            }
    return cache, False


# ------------------------------------------------------------
# HEADER - Title LEFT, HTML Button RIGHT
# ------------------------------------------------------------
col_title, col_html = st.columns([5, 1])

with col_title:
    st.title("🎯 Faceless Viral Hunter PRO")

with col_html:
    if st.session_state.results_df is not None and len(st.session_state.results_df) > 0:
        html_data = generate_html_report(st.session_state.results_df, st.session_state.last_search)
        st.download_button(
            "📥 HTML",
            data=html_data,
            file_name=f"faceless_report_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
            mime="text/html",
            use_container_width=True,
            type="primary"
        )
    else:
        st.button("📥 HTML", disabled=True, use_container_width=True, help="Search first")

st.markdown("**Find monetized faceless channels | Last 6 months | Premium CPM countries**")


# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------
st.sidebar.header("📊 Quota Tracker")
quota_pct = min(st.session_state.quota_used / 10000, 1.0)
st.sidebar.metric("Quota Used", f"{st.session_state.quota_used:,} / 10,000")
st.sidebar.progress(quota_pct)

if st.sidebar.button("🔄 Reset Quota Counter"):
    st.session_state.quota_used = 0
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Filters")

with st.sidebar.expander("📅 Time & Channel Age", expanded=True):
    days = st.slider("Videos from last X days", 1, 90, 30)
    max_channel_age = st.slider("Max Channel Age (months)", 1, 12, 6, help="Only channels created within this time")

with st.sidebar.expander("📊 View Filters", expanded=True):
    min_views = st.number_input("Min Views", min_value=1000, value=5000, step=1000)
    max_views = st.number_input("Max Views (0=No Limit)", min_value=0, value=0, step=10000)
    min_virality = st.slider("Min Virality (Views/Day)", 0, 10000, 100)

with st.sidebar.expander("👥 Subscriber Filters", expanded=True):
    min_subs = st.number_input("Min Subscribers", min_value=0, value=1000)
    max_subs = st.number_input("Max Subscribers", min_value=0, value=100000)

with st.sidebar.expander("🎬 Channel Video Filters", expanded=True):
    min_videos = st.slider("Min Videos", 0, 500, 5)
    max_videos = st.slider("Max Videos", 0, 1000, 500)

with st.sidebar.expander("🎬 Video Type", expanded=False):
    video_type = st.selectbox("Video Duration", ["All", "Long (5min+)", "Medium (1-5min)", "Shorts (<1min)"])
    exclude_shorts = st.checkbox("Exclude Shorts", value=True)

with st.sidebar.expander("🎯 Faceless Detection", expanded=False):
    faceless_only = st.checkbox("Only Faceless Channels", value=True)
    faceless_strictness = st.select_slider("Detection Strictness", options=["Relaxed", "Normal", "Strict"], value="Normal")

with st.sidebar.expander("💰 Monetization", expanded=True):
    monetized_only = st.checkbox("Only Monetized Channels", value=True, help="Channels with 1000+ subs")
    min_monetization_score = st.slider("Min Monetization Score", 0, 100, 50)

with st.sidebar.expander("🌍 Region (Premium CPM)", expanded=False):
    st.info("Default: Premium CPM countries only")
    premium_only = st.checkbox("Only Premium CPM Countries", value=True)
    selected_regions = st.multiselect(
        "Search Regions", 
        list(PREMIUM_COUNTRIES), 
        default=["US", "GB", "CA"]
    )


# ------------------------------------------------------------
# MAIN SEARCH SECTION
# ------------------------------------------------------------
st.markdown("---")
st.markdown("### 🔍 Search")
st.markdown(f"Enter **niche**, **keywords**, or **titles** (Max **{MAX_KEYWORDS}** items, one per line)")

search_input = st.text_area(
    "🔎 Type your search (one per line):",
    placeholder="reddit stories\nhorror\nmotivation\ntop 10 facts\ntrue crime",
    height=120,
    help=f"Enter up to {MAX_KEYWORDS} keywords, niches, or titles - one per line"
)

# Parse keywords
keywords_list = [kw.strip() for kw in search_input.strip().split('\n') if kw.strip()]
keywords_list = list(dict.fromkeys(keywords_list))  # Remove duplicates

if len(keywords_list) > MAX_KEYWORDS:
    st.warning(f"⚠️ Maximum {MAX_KEYWORDS} keywords allowed! Using first {MAX_KEYWORDS}.")
    keywords_list = keywords_list[:MAX_KEYWORDS]

if keywords_list:
    st.success(f"✅ **{len(keywords_list)} keyword(s):** {', '.join(keywords_list)}")

st.markdown("---")

# Current Settings Display
st.info(f"""
📌 **Current Settings:**
- 🔍 Keywords: **{len(keywords_list)}/{MAX_KEYWORDS}**
- 🌍 Regions: **{', '.join(selected_regions)}** (Premium CPM)
- 📅 Videos: Last **{days}** days | Channels: Last **{max_channel_age}** months
- 👁️ Views: **{min_views:,}+** | 👥 Subs: **{min_subs:,} - {max_subs:,}**
- 🎬 Videos: **{min_videos} - {max_videos}** | 💰 Monetized: **{'Yes' if monetized_only else 'No'}**
- 📊 Results: **All channels** (No limit)
- 📈 Quota Used: **{st.session_state.quota_used:,}** units
""")


# ------------------------------------------------------------
# SEARCH FUNCTION
# ------------------------------------------------------------
def run_search(keywords):
    all_results = []
    channel_cache = {}
    seen_channels = set()
    quota_exceeded = False
    
    published_after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    total_ops = len(keywords) * len(selected_regions)
    current_op = 0
    
    progress = st.progress(0)
    status = st.empty()
    
    stats = {"searched": 0, "passed": 0, "filtered": defaultdict(int)}
    
    regions_to_search = selected_regions if selected_regions else ["US"]
    
    for keyword in keywords:
        if quota_exceeded:
            break
            
        for region in regions_to_search:
            if quota_exceeded:
                break
            
            current_op += 1
            progress.progress(current_op / total_ops * 0.5)
            status.markdown(f"🔍 Searching **{region}**: `{keyword}`...")
            
            search_params = {
                "part": "snippet",
                "q": keyword,
                "type": "video",
                "order": "viewCount",
                "publishedAfter": published_after,
                "maxResults": 50,
                "regionCode": region,
                "relevanceLanguage": "en",
                "safeSearch": "none",
                "key": API_KEY
            }
            
            if exclude_shorts or video_type == "Long (5min+)":
                search_params["videoDuration"] = "long" if video_type == "Long (5min+)" else "medium"
            elif video_type == "Medium (1-5min)":
                search_params["videoDuration"] = "medium"
            elif video_type == "Shorts (<1min)":
                search_params["videoDuration"] = "short"
            
            data = fetch_json(SEARCH_URL, search_params, quota_cost=100)
            
            if data == "QUOTA":
                quota_exceeded = True
                st.error("⚠️ API Quota exhausted!")
                break
            
            if not data:
                continue
            
            items = data.get("items", [])
            stats["searched"] += len(items)
            
            new_items = []
            for item in items:
                cid = item.get("snippet", {}).get("channelId")
                vid = item.get("id", {}).get("videoId")
                if vid and cid and cid not in seen_channels:
                    new_items.append(item)
            
            if not new_items:
                continue
            
            video_ids = [i["id"]["videoId"] for i in new_items]
            channel_ids = list({i["snippet"]["channelId"] for i in new_items})
            
            # Fetch video stats
            progress.progress(current_op / total_ops * 0.5 + 0.25)
            status.markdown(f"📊 Getting stats for `{keyword}`...")
            
            video_stats = {}
            for i in range(0, len(video_ids), 50):
                if quota_exceeded:
                    break
                batch = video_ids[i:i+50]
                vid_data = fetch_json(VIDEOS_URL, {
                    "part": "statistics,contentDetails",
                    "id": ",".join(batch),
                    "key": API_KEY
                }, quota_cost=1)
                
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
            channel_cache, quota_hit = batch_fetch_channels(channel_ids, API_KEY, channel_cache)
            if quota_hit:
                quota_exceeded = True
            
            # Process results
            for item in new_items:
                sn = item["snippet"]
                vid = item["id"]["videoId"]
                cid = sn["channelId"]
                v_stats = video_stats.get(vid, {})
                ch = channel_cache.get(cid, {})
                
                if not v_stats or not ch:
                    continue
                
                views = v_stats.get("views", 0)
                likes = v_stats.get("likes", 0)
                comments = v_stats.get("comments", 0)
                duration = v_stats.get("duration", 0)
                subs = ch.get("subs", 0)
                total_videos = ch.get("video_count", 0)
                total_channel_views = ch.get("total_views", 0)
                avg_views = total_channel_views / max(total_videos, 1)
                country = ch.get("country", "N/A")
                created = ch.get("created", "")
                
                # ========== FILTERS ==========
                
                if exclude_shorts and duration < 60:
                    stats["filtered"]["shorts"] += 1
                    continue
                
                if views < min_views or (max_views > 0 and views > max_views):
                    stats["filtered"]["views"] += 1
                    continue
                
                if not (min_subs <= subs <= max_subs):
                    stats["filtered"]["subs"] += 1
                    continue
                
                if total_videos < min_videos or total_videos > max_videos:
                    stats["filtered"]["video_count"] += 1
                    continue
                
                if premium_only and country not in PREMIUM_COUNTRIES:
                    stats["filtered"]["country"] += 1
                    continue
                
                # Channel age filter
                channel_age_days = 0
                if created:
                    try:
                        created_date = datetime.strptime(created[:19], "%Y-%m-%dT%H:%M:%S")
                        channel_age_days = (datetime.utcnow() - created_date).days
                        if channel_age_days > (max_channel_age * 30):
                            stats["filtered"]["channel_age"] += 1
                            continue
                    except:
                        stats["filtered"]["channel_age"] += 1
                        continue
                
                # Faceless detection
                is_faceless, faceless_score = detect_faceless_advanced(ch, faceless_strictness)
                if faceless_only and not is_faceless:
                    stats["filtered"]["not_faceless"] += 1
                    continue
                
                # Monetization
                mon_status, mon_score = check_monetization_status(ch)
                if monetized_only and mon_score < min_monetization_score:
                    stats["filtered"]["not_monetized"] += 1
                    continue
                
                # Virality
                virality = calculate_virality_score(views, sn["publishedAt"])
                if virality < min_virality:
                    stats["filtered"]["virality"] += 1
                    continue
                
                # Video type
                vtype = get_video_type_label(duration)
                if video_type == "Long (5min+)" and duration < 300:
                    stats["filtered"]["duration"] += 1
                    continue
                if video_type == "Medium (1-5min)" and (duration < 60 or duration >= 300):
                    stats["filtered"]["duration"] += 1
                    continue
                if video_type == "Shorts (<1min)" and duration >= 60:
                    stats["filtered"]["duration"] += 1
                    continue
                
                # ========== PASSED ALL FILTERS ==========
                
                seen_channels.add(cid)
                stats["passed"] += 1
                
                engagement = calculate_engagement_rate(views, likes, comments)
                niche = detect_niche(sn["title"], sn["channelTitle"], keyword)
                est_revenue = estimate_revenue(total_channel_views, country, total_videos)
                uploads_per_week, uploads_per_month, schedule = calculate_upload_frequency(created, total_videos)
                
                quality_score = calculate_quality_score(
                    views, virality, engagement, mon_score,
                    faceless_score, subs, avg_views
                )
                
                # Video breakdown estimation
                shorts_count = int(total_videos * 0.15)
                long_count = int(total_videos * 0.35)
                medium_count = total_videos - shorts_count - long_count
                
                channel_age_str = f"{channel_age_days} days" if channel_age_days > 0 else "N/A"
                
                all_results.append({
                    "Title": sn["title"],
                    "Channel": sn["channelTitle"],
                    "ChannelID": cid,
                    "Subs": subs,
                    "TotalVideos": total_videos,
                    "ShortsCount": shorts_count,
                    "MediumCount": medium_count,
                    "LongCount": long_count,
                    "TotalChannelViews": total_channel_views,
                    "AvgViews": round(avg_views, 0),
                    "UploadsPerWeek": uploads_per_week,
                    "UploadSchedule": schedule,
                    "MonetizationStatus": mon_status,
                    "MonetizationScore": mon_score,
                    "EstRevenue": est_revenue,
                    "Niche": niche,
                    "Views": views,
                    "Likes": likes,
                    "Comments": comments,
                    "Virality": virality,
                    "Engagement%": engagement,
                    "QualityScore": quality_score,
                    "FacelessScore": faceless_score,
                    "Uploaded": sn["publishedAt"][:10],
                    "ChCreated": created[:10] if created else "N/A",
                    "ChannelAge": channel_age_str,
                    "Country": country,
                    "Type": vtype,
                    "Duration": duration,
                    "DurationStr": f"{duration//60}:{duration%60:02d}",
                    "Thumb": sn["thumbnails"]["high"]["url"],
                    "Link": f"https://www.youtube.com/watch?v={vid}",
                    "ChannelLink": f"https://www.youtube.com/channel/{cid}",
                    "Keyword": keyword
                })
    
    progress.progress(1.0)
    status.empty()
    progress.empty()
    
    # Stats display
    st.markdown("### 📊 Search Statistics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Videos Searched", stats["searched"])
    col2.metric("Passed Filters", stats["passed"])
    col3.metric("Channels Found", len(all_results))
    col4.metric("Quota Used", f"{st.session_state.quota_used:,}")
    
    # Filter breakdown
    if stats["filtered"]:
        with st.expander("🔍 Filter Breakdown"):
            filter_data = [{"Filter": k.replace("_", " ").title(), "Removed": v} 
                          for k, v in sorted(stats["filtered"].items(), key=lambda x: -x[1]) if v > 0]
            if filter_data:
                st.dataframe(pd.DataFrame(filter_data), use_container_width=True, hide_index=True)
    
    if not all_results:
        return None
    
    # Sort by quality - NO LIMIT on results
    df = pd.DataFrame(all_results)
    df = df.sort_values("QualityScore", ascending=False).reset_index(drop=True)
    
    return df


# ------------------------------------------------------------
# SEARCH BUTTON & EXECUTION
# ------------------------------------------------------------
if st.button("🚀 FIND MONETIZED FACELESS CHANNELS", type="primary", use_container_width=True):
    
    if not keywords_list:
        st.error("⚠️ Please enter at least one keyword!")
        st.stop()
    
    st.session_state.last_search = ", ".join(keywords_list)
    
    df = run_search(keywords_list)
    
    if df is None or len(df) == 0:
        st.warning("😔 No results found! Try different keywords or adjust filters.")
        st.stop()
    
    st.session_state.results_df = df
    
    st.success(f"🎉 **{len(df)} MONETIZED FACELESS CHANNELS** found!")
    st.balloons()
    
    # Sorting
    col1, col2 = st.columns(2)
    with col1:
        sort_by = st.selectbox("Sort By", ["QualityScore", "Views", "Virality", "Engagement%", "Subs", "MonetizationScore", "EstRevenue", "TotalVideos"])
    with col2:
        sort_order = st.selectbox("Order", ["Descending", "Ascending"])
    
    df = df.sort_values(by=sort_by, ascending=(sort_order == "Ascending")).reset_index(drop=True)
    
    # Display ALL results
    for idx, r in df.iterrows():
        with st.container():
            st.markdown("---")
            
            if idx == 0:
                rank = "🏆 #1"
            elif idx == 1:
                rank = "🥈 #2"
            elif idx == 2:
                rank = "🥉 #3"
            else:
                rank = f"⭐ #{idx+1}"
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### {rank} - {r['Title']}")
                st.markdown(f"**📺 [{r['Channel']}]({r['ChannelLink']})** • 👥 {r['Subs']:,} subs • 🌍 {r['Country']} • 📂 {r['Niche']}")
                st.markdown(f"📅 Channel Age: **{r['ChannelAge']}** | Created: {r['ChCreated']} | ⏰ {r['UploadSchedule']}")
                
                # Video Breakdown
                st.info(f"""
                📊 **Video Breakdown:**
                🎬 Total: **{r['TotalVideos']}** | 📱 Shorts: **{r['ShortsCount']}** | ⏱️ Medium: **{r['MediumCount']}** | 🎥 Long: **{r['LongCount']}** | 📊 Avg: **{r['AvgViews']:,.0f}** views/vid
                """)
                
                # Quality Score
                st.markdown(f"### ⭐ Quality Score: **{r['QualityScore']:.0f}/100**")
                
                # Monetization status
                if r['MonetizationScore'] >= 70:
                    st.success(f"💰 {r['MonetizationStatus']} ({r['MonetizationScore']}%) | Est Revenue: ${r['EstRevenue']:,.0f}")
                elif r['MonetizationScore'] >= 50:
                    st.info(f"💰 {r['MonetizationStatus']} ({r['MonetizationScore']}%)")
                else:
                    st.warning(f"💰 {r['MonetizationStatus']} ({r['MonetizationScore']}%)")
                
                # Stats grid
                cols = st.columns(6)
                cols[0].metric("👁️ Views", f"{r['Views']:,}")
                cols[1].metric("🔥 Virality", f"{r['Virality']:,.0f}/day")
                cols[2].metric("💬 Engage", f"{r['Engagement%']}%")
                cols[3].metric("👍 Likes", f"{r['Likes']:,}")
                cols[4].metric("📊 Avg/Vid", f"{r['AvgViews']:,.0f}")
                cols[5].metric("✅ Faceless", f"{r['FacelessScore']}%")
                
                st.markdown(f"⏱️ Video: {r['DurationStr']} ({r['Type']}) • 📤 Uploaded: {r['Uploaded']} • 🔑 `{r['Keyword']}`")
                
                st.markdown(f"[▶️ **Watch Video**]({r['Link']}) | [📺 **Visit Channel**]({r['ChannelLink']})")
            
            with col2:
                st.image(r["Thumb"], use_container_width=True)
    
    # Download Section
    st.markdown("---")
    st.markdown("### 📥 Download Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        csv = 
