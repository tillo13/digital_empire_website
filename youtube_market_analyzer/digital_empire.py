#!/usr/bin/env python3
"""
YouTube Digital Empire Network Validator
---------------------------------------
Validates and collects data for all Digital Empire channels,
then generates a beautiful HTML report showcasing their collective strength.
"""

import os
import json
import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import time

# Digital Empire Network Channels - EXACT handles as they appear on YouTube
DIGITAL_EMPIRE_CHANNELS = {
    'Dexter Playz': 'dexterplayz',
    'Red Ninja': 'RealRedNinja', 
    'Fast Friends': 'FastFriendsYT',
    'Red Playz': 'realredplayz',
    'Durple and Simon': 'DurpleandSimonYT',
    'Red': 'redninja-gaming',
    'Dexter Also': 'dexteralso4621'
}

def format_number(num):
    """Format large numbers with K/M suffix"""
    try:
        num = int(num)
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        else:
            return str(num)
    except:
        return "0"

def get_channel_data(youtube, channel_handle):
    """Get channel data by handle"""
    try:
        # Remove @ if present
        handle_clean = channel_handle.replace('@', '')
        
        # Use the forHandle parameter (available since Jan 2024)
        channel_response = youtube.channels().list(
            part="snippet,statistics,contentDetails,brandingSettings",
            forHandle=handle_clean
        ).execute()
        
        if not channel_response.get('items'):
            print(f"  ❌ Channel not found: {channel_handle}")
            return None
            
        channel = channel_response['items'][0]
        channel_id = channel['id']
        stats = channel.get('statistics', {})
        snippet = channel.get('snippet', {})
        
        # Get top videos (if channel has videos)
        top_videos = []
        video_count = int(stats.get('videoCount', 0))
        
        if video_count > 0:
            try:
                uploads_playlist_id = channel['contentDetails']['relatedPlaylists']['uploads']
                
                # Get latest videos
                playlist_response = youtube.playlistItems().list(
                    part="snippet,contentDetails",
                    playlistId=uploads_playlist_id,
                    maxResults=10
                ).execute()
                
                video_ids = [item['contentDetails']['videoId'] for item in playlist_response.get('items', [])]
                
                if video_ids:
                    videos_response = youtube.videos().list(
                        part="snippet,statistics",
                        id=','.join(video_ids)
                    ).execute()
                    
                    videos = videos_response.get('items', [])
                    # Sort by views
                    videos.sort(key=lambda x: int(x.get('statistics', {}).get('viewCount', 0)), reverse=True)
                    
                    for video in videos[:3]:  # Top 3 videos
                        top_videos.append({
                            'title': video['snippet']['title'],
                            'views': int(video['statistics'].get('viewCount', 0)),
                            'url': f"https://www.youtube.com/watch?v={video['id']}"
                        })
            except HttpError as e:
                # Channel might have no public videos or playlist is empty
                print(f"  ⚠️  Could not fetch videos for {channel_handle}: {str(e)[:100]}")
        
        return {
            'channel_id': channel_id,
            'title': snippet.get('title', ''),
            'description': snippet.get('description', '')[:200] + '...' if len(snippet.get('description', '')) > 200 else snippet.get('description', ''),
            'custom_url': snippet.get('customUrl', ''),
            'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
            'country': snippet.get('country', ''),
            'published_at': snippet.get('publishedAt', ''),
            'view_count': int(stats.get('viewCount', 0)),
            'subscriber_count': int(stats.get('subscriberCount', 0)),
            'video_count': video_count,
            'url': f"https://www.youtube.com/channel/{channel_id}",
            'handle': '@' + handle_clean,
            'top_videos': top_videos
        }
        
    except HttpError as e:
        print(f"  ❌ Error fetching {channel_handle}: {str(e)[:100]}")
        return None
    except Exception as e:
        print(f"  ❌ Unexpected error for {channel_handle}: {str(e)[:100]}")
        return None

def generate_html_report(channels_data, output_file='digital_empire_report.html'):
    """Generate a beautiful HTML report"""
    
    # Calculate totals
    total_subs = sum(ch['subscriber_count'] for ch in channels_data if ch)
    total_views = sum(ch['view_count'] for ch in channels_data if ch)
    total_videos = sum(ch['video_count'] for ch in channels_data if ch)
    active_channels = len([ch for ch in channels_data if ch and ch['video_count'] > 0])
    
    # Sort channels by subscribers
    channels_data.sort(key=lambda x: x['subscriber_count'] if x else 0, reverse=True)
    
    # Find oldest channel
    years_active = 0
    if channels_data:
        valid_dates = [ch['published_at'] for ch in channels_data if ch and ch.get('published_at')]
        if valid_dates:
            oldest_date = min(valid_dates)
            # Parse the date properly
            if oldest_date.endswith('Z'):
                oldest_dt = datetime.datetime.strptime(oldest_date, '%Y-%m-%dT%H:%M:%SZ')
            else:
                oldest_dt = datetime.datetime.fromisoformat(oldest_date.replace('+00:00', ''))
            years_active = (datetime.datetime.now() - oldest_dt).days // 365
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Digital Empire Network - Media Kit</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #ffffff;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            padding: 60px 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            margin-bottom: 40px;
        }}
        
        .header h1 {{
            font-size: 3.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .header p {{
            font-size: 1.3em;
            opacity: 0.9;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 40px 0;
        }}
        
        .stat-card {{
            background: #1a1a1a;
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            border: 1px solid #333;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        }}
        
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            font-size: 1.1em;
            color: #888;
        }}
        
        .channels-section {{
            margin: 60px 0;
        }}
        
        .section-title {{
            font-size: 2.5em;
            margin-bottom: 30px;
            text-align: center;
            color: #667eea;
        }}
        
        .channel-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 30px;
        }}
        
        .channel-card {{
            background: #1a1a1a;
            border-radius: 15px;
            overflow: hidden;
            border: 1px solid #333;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .channel-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        }}
        
        .channel-header {{
            display: flex;
            align-items: center;
            padding: 20px;
            background: #222;
        }}
        
        .channel-thumbnail {{
            width: 60px;
            height: 60px;
            border-radius: 50%;
            margin-right: 15px;
            object-fit: cover;
        }}
        
        .channel-info h3 {{
            font-size: 1.3em;
            margin-bottom: 5px;
        }}
        
        .channel-handle {{
            color: #888;
            font-size: 0.9em;
        }}
        
        .channel-stats {{
            display: flex;
            justify-content: space-around;
            padding: 20px;
            background: #181818;
        }}
        
        .channel-stat {{
            text-align: center;
        }}
        
        .channel-stat-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
        }}
        
        .channel-stat-label {{
            font-size: 0.8em;
            color: #888;
            text-transform: uppercase;
        }}
        
        .top-videos {{
            padding: 20px;
        }}
        
        .top-videos h4 {{
            font-size: 1.1em;
            margin-bottom: 10px;
            color: #667eea;
        }}
        
        .video-item {{
            margin-bottom: 10px;
            padding: 10px;
            background: #222;
            border-radius: 8px;
            font-size: 0.9em;
        }}
        
        .video-views {{
            color: #888;
            font-size: 0.8em;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 60px;
            padding: 30px;
            background: #1a1a1a;
            border-radius: 15px;
        }}
        
        .cta {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 40px;
            border-radius: 30px;
            text-decoration: none;
            display: inline-block;
            font-weight: bold;
            margin-top: 20px;
            transition: transform 0.3s;
        }}
        
        .cta:hover {{
            transform: scale(1.05);
        }}
        
        .timestamp {{
            text-align: center;
            color: #666;
            margin-top: 20px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Digital Empire Network</h1>
            <p>A Powerful Multi-Channel YouTube Media Network</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{format_number(total_subs)}+</div>
                <div class="stat-label">Total Subscribers</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{format_number(total_views)}+</div>
                <div class="stat-label">Total Views</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{format_number(total_videos)}+</div>
                <div class="stat-label">Videos Created</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{years_active}+</div>
                <div class="stat-label">Years Active</div>
            </div>
        </div>
        
        <div class="channels-section">
            <h2 class="section-title">Network Channels</h2>
            <div class="channel-grid">
"""
    
    # Add each channel
    for channel in channels_data:
        if not channel:
            continue
            
        thumbnail_url = channel['thumbnail'] or 'https://via.placeholder.com/60'
        
        html_content += f"""
                <div class="channel-card">
                    <div class="channel-header">
                        <img src="{thumbnail_url}" alt="{channel['title']}" class="channel-thumbnail">
                        <div class="channel-info">
                            <h3>{channel['title']}</h3>
                            <div class="channel-handle">{channel['handle']}</div>
                        </div>
                    </div>
                    <div class="channel-stats">
                        <div class="channel-stat">
                            <div class="channel-stat-value">{format_number(channel['subscriber_count'])}</div>
                            <div class="channel-stat-label">Subscribers</div>
                        </div>
                        <div class="channel-stat">
                            <div class="channel-stat-value">{format_number(channel['view_count'])}</div>
                            <div class="channel-stat-label">Views</div>
                        </div>
                        <div class="channel-stat">
                            <div class="channel-stat-value">{format_number(channel['video_count'])}</div>
                            <div class="channel-stat-label">Videos</div>
                        </div>
                    </div>
"""
        
        if channel['top_videos']:
            html_content += """
                    <div class="top-videos">
                        <h4>Top Videos</h4>
"""
            for video in channel['top_videos'][:3]:
                html_content += f"""
                        <div class="video-item">
                            <div>{video['title'][:60]}...</div>
                            <div class="video-views">{format_number(video['views'])} views</div>
                        </div>
"""
            html_content += """
                    </div>
"""
        
        html_content += """
                </div>
"""
    
    html_content += f"""
            </div>
        </div>
        
        <div class="footer">
            <h2>Why Partner with Digital Empire?</h2>
            <p>✅ Proven track record with {format_number(total_views)}+ views</p>
            <p>✅ Engaged audience of {format_number(total_subs)}+ subscribers</p>
            <p>✅ {years_active}+ years of content creation expertise</p>
            <p>✅ Multiple channels for diverse content strategies</p>
            <p>✅ Ready for voice AI integration at scale</p>
            <a href="#" class="cta">Partner With Us</a>
        </div>
        
        <div class="timestamp">
            Report generated on {datetime.datetime.now().strftime('%B %d, %Y at %I:%M %p')}
        </div>
    </div>
</body>
</html>
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_file

def main():
    """Main function to validate all channels and generate report"""
    
    print("="*60)
    print("DIGITAL EMPIRE NETWORK VALIDATOR")
    print("="*60)
    
    # Load environment variables
    load_dotenv()
    API_KEY = os.getenv('YT_API_KEY')
    
    if not API_KEY:
        print("❌ Error: YouTube API key not found!")
        print("Please create a .env file with: YT_API_KEY=your_key_here")
        return
    
    # Initialize YouTube API
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    
    print(f"\nValidating {len(DIGITAL_EMPIRE_CHANNELS)} channels...\n")
    
    # Collect data for all channels
    all_channel_data = []
    
    for name, handle in DIGITAL_EMPIRE_CHANNELS.items():
        print(f"📊 Fetching data for {name} (@{handle})...")
        channel_data = get_channel_data(youtube, handle)
        
        if channel_data:
            print(f"  ✅ Success! {format_number(channel_data['subscriber_count'])} subscribers")
            all_channel_data.append(channel_data)
        else:
            print(f"  ⚠️  Skipped (channel not found or error)")
        
        time.sleep(0.5)  # Be nice to the API
    
    # Generate HTML report
    print("\n" + "="*60)
    print("GENERATING REPORT...")
    print("="*60)
    
    if all_channel_data:
        output_file = generate_html_report(all_channel_data)
        
        # Print summary
        total_subs = sum(ch['subscriber_count'] for ch in all_channel_data)
        total_views = sum(ch['view_count'] for ch in all_channel_data)
        total_videos = sum(ch['video_count'] for ch in all_channel_data)
        
        print(f"\n✨ DIGITAL EMPIRE NETWORK SUMMARY:")
        print(f"  • Active Channels: {len(all_channel_data)}")
        print(f"  • Total Subscribers: {format_number(total_subs)}")
        print(f"  • Total Views: {format_number(total_views)}")
        print(f"  • Total Videos: {format_number(total_videos)}")
        print(f"\n📄 Report saved to: {output_file}")
        print(f"🌐 Open the file in your browser to view the beautiful report!")
        
        # Also save raw data as JSON
        with open('digital_empire_data.json', 'w') as f:
            json.dump(all_channel_data, f, indent=2)
        print(f"📊 Raw data saved to: digital_empire_data.json")
    else:
        print("\n❌ No channel data collected. Please check your API key and channel handles.")

if __name__ == "__main__":
    main()