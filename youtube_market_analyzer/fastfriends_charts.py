#!/usr/bin/env python3
"""
Fast Friends Analytics - Enhanced Data Collector
------------------------------------------------
Enhanced data collection script with advanced public metrics analysis.
Creates JSON data files for the dashboard to consume.
Maximizes insights from publicly available YouTube data.
"""

import os
import datetime
import json
import webbrowser
import pandas as pd
from typing import Dict, List, Any, Optional
from collections import defaultdict
from dotenv import load_dotenv

# Auto-install dependencies
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    import subprocess
    subprocess.check_call(["pip", "install", "google-api-python-client", "pandas", "python-dotenv"])
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

# Configuration - All data in fastfriends_data folder
DATA_DIR = "fastfriends_data"
HISTORICAL_CSV = "historical_snapshots.csv"
GROWTH_CSV = "video_growth_tracking.csv"
SUBSCRIBER_CSV = "subscriber_tracking.csv"
ANALYTICS_JSON = "analytics_data.json"
DASHBOARD_HTML = "dashboard.html"

def format_number(num: int) -> str:
    """Format large numbers with K/M/B suffixes"""
    try:
        num = int(num)
        if num >= 1_000_000_000:
            return f"{num/1_000_000_000:.1f}B"
        elif num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num/1_000:.1f}K"
        else:
            return str(num)
    except (ValueError, TypeError):
        return "0"

def format_duration(duration: str) -> str:
    """Convert YouTube duration format to readable format"""
    duration = duration.replace('PT', '')
    
    hours = 0
    minutes = 0
    seconds = 0
    
    if 'H' in duration:
        hours_part = duration.split('H')[0]
        hours = int(hours_part)
        duration = duration.split('H')[1]
    
    if 'M' in duration:
        minutes_part = duration.split('M')[0]
        minutes = int(minutes_part)
        duration = duration.split('M')[1]
    
    if 'S' in duration:
        seconds_part = duration.split('S')[0]
        seconds = int(seconds_part)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

def get_channel_id_from_handle(youtube, handle: str) -> Optional[str]:
    """Find channel ID from handle"""
    try:
        handle_clean = handle.replace('@', '').lower()
        print(f"Searching for channel: @{handle_clean}")
        
        known_ids = {
            'fastfriendsyt': 'UCdZ8WmPJK-wN22wTSUIU-Ag'
        }
        
        if handle_clean in known_ids:
            print(f"✓ Using known channel ID: {known_ids[handle_clean]}")
            return known_ids[handle_clean]
        
        search_response = youtube.search().list(
            q=f"@{handle_clean}",
            type="channel", 
            part="snippet",
            maxResults=10
        ).execute()
        
        for item in search_response.get('items', []):
            channel_id = item['snippet']['channelId']
            
            channel_response = youtube.channels().list(
                part="snippet",
                id=channel_id
            ).execute()
            
            if channel_response.get('items'):
                custom_url = channel_response['items'][0]['snippet'].get('customUrl', '').replace('@', '')
                channel_title = channel_response['items'][0]['snippet']['title']
                
                if custom_url.lower() == handle_clean or 'fast friends' in channel_title.lower():
                    print(f"✓ Found channel: {channel_title} ({channel_id})")
                    return channel_id
        
        return None
        
    except HttpError as e:
        print(f"✗ Error searching for channel: {e}")
        return None

def get_channel_details(youtube, channel_id: str) -> Dict[str, Any]:
    """Get detailed channel information including subscriber count"""
    try:
        channel_response = youtube.channels().list(
            part="snippet,statistics,contentDetails",
            id=channel_id
        ).execute()
        
        if not channel_response.get('items'):
            return {}
        
        channel_info = channel_response['items'][0]
        snippet = channel_info.get('snippet', {})
        stats = channel_info.get('statistics', {})
        
        return {
            'channel_id': channel_id,
            'channel_title': snippet.get('title', ''),
            'channel_description': snippet.get('description', '')[:200] + '...' if snippet.get('description', '') else '',
            'channel_thumbnail': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
            'subscriber_count': int(stats.get('subscriberCount', 0)),
            'total_views': int(stats.get('viewCount', 0)),
            'video_count': int(stats.get('videoCount', 0)),
            'created_date': snippet.get('publishedAt', ''),
            'subscriber_count_formatted': format_number(int(stats.get('subscriberCount', 0))),
            'total_views_formatted': format_number(int(stats.get('viewCount', 0))),
            'video_count_formatted': format_number(int(stats.get('videoCount', 0)))
        }
        
    except HttpError as e:
        print(f"✗ Error getting channel details: {e}")
        return {}

def get_all_channel_videos(youtube, channel_id: str, max_videos: int = 100) -> List[Dict[str, Any]]:
    """Get all videos from a channel with enhanced analytics"""
    try:
        print(f"Getting videos from channel {channel_id}...")
        
        channel_response = youtube.channels().list(
            part="contentDetails,snippet",
            id=channel_id
        ).execute()
        
        if not channel_response.get('items'):
            return []
        
        channel_info = channel_response['items'][0]
        uploads_playlist_id = channel_info['contentDetails']['relatedPlaylists']['uploads']
        
        video_ids = []
        next_page_token = None
        
        while len(video_ids) < max_videos:
            playlist_response = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=min(50, max_videos - len(video_ids)),
                pageToken=next_page_token
            ).execute()
            
            batch_videos = playlist_response.get('items', [])
            if not batch_videos:
                break
            
            batch_video_ids = [video['contentDetails']['videoId'] for video in batch_videos]
            video_ids.extend(batch_video_ids)
            
            next_page_token = playlist_response.get('nextPageToken')
            if not next_page_token:
                break
        
        all_videos = []
        current_time = datetime.datetime.now(datetime.timezone.utc)
        
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]
            
            videos_response = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=','.join(batch_ids)
            ).execute()
            
            for video in videos_response.get('items', []):
                snippet = video.get('snippet', {})
                stats = video.get('statistics', {})
                content_details = video.get('contentDetails', {})
                
                published_at_str = snippet.get('publishedAt', '')
                if published_at_str:
                    published_at = datetime.datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
                    hours_since_published = (current_time - published_at).total_seconds() / 3600
                else:
                    published_at = None
                    hours_since_published = 0
                
                views = int(stats.get('viewCount', 0))
                likes = int(stats.get('likeCount', 0))
                comments = int(stats.get('commentCount', 0))
                views_per_hour = views / hours_since_published if hours_since_published > 0 else 0
                
                duration = content_details.get('duration', 'PT0S')
                duration_formatted = format_duration(duration)
                
                # Enhanced analytics calculations (publicly available data only)
                engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0
                like_rate = (likes / views * 100) if views > 0 else 0
                comment_rate = (comments / views * 100) if views > 0 else 0
                
                # Video momentum scoring (performance weighted by recency)
                days_old = hours_since_published / 24
                momentum_score = views_per_hour * (1 / (days_old + 1)) if days_old > 0 else views_per_hour
                
                # Content freshness factor
                freshness_factor = 1 / (days_old + 1) if days_old > 0 else 1
                
                # Engagement velocity (engagement per hour)
                engagement_per_hour = (likes + comments) / hours_since_published if hours_since_published > 0 else 0
                
                video_data = {
                    'video_id': video.get('id', ''),
                    'title': snippet.get('title', ''),
                    'thumbnail': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                    'published_at': published_at.isoformat() if published_at else '',
                    'published_date': published_at.strftime('%Y-%m-%d') if published_at else '',
                    'published_hour': published_at.hour if published_at else None,
                    'hours_since_published': round(hours_since_published, 2),
                    'days_since_published': round(hours_since_published / 24, 1),
                    'views': views,
                    'views_formatted': format_number(views),
                    'likes': likes,
                    'likes_formatted': format_number(likes),
                    'comments': comments,
                    'comments_formatted': format_number(comments),
                    'views_per_hour': round(views_per_hour, 2),
                    'engagement_rate': round(engagement_rate, 2),
                    'like_rate': round(like_rate, 2),
                    'comment_rate': round(comment_rate, 2),
                    'momentum_score': round(momentum_score, 2),
                    'freshness_factor': round(freshness_factor, 3),
                    'engagement_per_hour': round(engagement_per_hour, 2),
                    'duration': duration_formatted,
                    'url': f"https://www.youtube.com/watch?v={video.get('id', '')}",
                }
                
                all_videos.append(video_data)
        
        # Sort by views per hour
        all_videos.sort(key=lambda x: x['views_per_hour'], reverse=True)
        return all_videos
        
    except HttpError as e:
        print(f"✗ Error getting videos: {e}")
        return []

def capture_snapshot(videos: List[Dict[str, Any]]) -> pd.DataFrame:
    """Capture current snapshot of all videos with enhanced metrics"""
    snapshot_time = datetime.datetime.now()
    snapshot_data = []
    
    for video in videos:
        record = {
            'snapshot_timestamp': snapshot_time.isoformat(),
            'snapshot_date': snapshot_time.strftime('%Y-%m-%d'),
            'snapshot_time': snapshot_time.strftime('%H:%M:%S'),
            'snapshot_hour': snapshot_time.hour,
            'video_id': video['video_id'],
            'video_title': video['title'],
            'published_at': video['published_at'],
            'published_hour': video['published_hour'],
            'hours_since_published': video['hours_since_published'],
            'days_since_published': video['days_since_published'],
            'current_views': video['views'],
            'current_likes': video['likes'],
            'current_comments': video['comments'],
            'views_per_hour': video['views_per_hour'],
            'engagement_rate': video['engagement_rate'],
            'like_rate': video['like_rate'],
            'comment_rate': video['comment_rate'],
            'momentum_score': video['momentum_score'],
            'engagement_per_hour': video['engagement_per_hour'],
            'duration': video['duration'],
            'url': video['url']
        }
        snapshot_data.append(record)
    
    return pd.DataFrame(snapshot_data)

def capture_subscriber_snapshot(channel_details: Dict[str, Any]) -> pd.DataFrame:
    """Capture current subscriber count snapshot"""
    snapshot_time = datetime.datetime.now()
    
    snapshot_data = [{
        'snapshot_timestamp': snapshot_time.isoformat(),
        'snapshot_date': snapshot_time.strftime('%Y-%m-%d'),
        'snapshot_time': snapshot_time.strftime('%H:%M:%S'),
        'snapshot_hour': snapshot_time.hour,
        'channel_id': channel_details['channel_id'],
        'channel_title': channel_details['channel_title'],
        'subscriber_count': channel_details['subscriber_count'],
        'total_views': channel_details['total_views'],
        'video_count': channel_details['video_count']
    }]
    
    return pd.DataFrame(snapshot_data)

def load_historical_data() -> pd.DataFrame:
    """Load existing historical data if it exists"""
    filepath = os.path.join(DATA_DIR, HISTORICAL_CSV)
    
    if os.path.exists(filepath):
        try:
            df = pd.read_csv(filepath)
            print(f"✓ Loaded {len(df)} historical records")
            return df
        except Exception as e:
            print(f"⚠️ Error loading historical data: {e}")
            return pd.DataFrame()
    else:
        print("📊 Creating new historical tracking database")
        return pd.DataFrame()

def load_subscriber_data() -> pd.DataFrame:
    """Load existing subscriber tracking data"""
    filepath = os.path.join(DATA_DIR, SUBSCRIBER_CSV)
    
    if os.path.exists(filepath):
        try:
            df = pd.read_csv(filepath)
            print(f"✓ Loaded {len(df)} subscriber tracking records")
            return df
        except Exception as e:
            print(f"⚠️ Error loading subscriber data: {e}")
            return pd.DataFrame()
    else:
        print("📊 Creating new subscriber tracking database")
        return pd.DataFrame()

def save_snapshot(snapshot_df: pd.DataFrame):
    """Save current snapshot to historical CSV"""
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, HISTORICAL_CSV)
    
    existing_df = load_historical_data()
    
    if not existing_df.empty:
        combined_df = pd.concat([existing_df, snapshot_df], ignore_index=True)
    else:
        combined_df = snapshot_df
    
    combined_df = combined_df.drop_duplicates(subset=['video_id', 'snapshot_timestamp'])
    combined_df = combined_df.sort_values(['snapshot_timestamp', 'video_id'])
    
    combined_df.to_csv(filepath, index=False)
    print(f"✓ Saved snapshot with {len(snapshot_df)} videos to historical database")
    
    return combined_df

def save_subscriber_snapshot(snapshot_df: pd.DataFrame):
    """Save current subscriber snapshot to CSV"""
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, SUBSCRIBER_CSV)
    
    existing_df = load_subscriber_data()
    
    if not existing_df.empty:
        combined_df = pd.concat([existing_df, snapshot_df], ignore_index=True)
    else:
        combined_df = snapshot_df
    
    # Remove duplicates (same snapshot_timestamp)
    combined_df = combined_df.drop_duplicates(subset=['snapshot_timestamp'])
    
    # Sort by timestamp
    combined_df = combined_df.sort_values('snapshot_timestamp')
    
    # Save to CSV
    combined_df.to_csv(filepath, index=False)
    print(f"✓ Saved subscriber snapshot to tracking database")
    
    return combined_df

def analyze_subscriber_growth(subscriber_df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze subscriber growth patterns with enhanced insights"""
    if subscriber_df.empty or len(subscriber_df) < 2:
        return {
            'growth_data': [],
            'hourly_growth': {},
            'daily_growth': {},
            'total_growth': 0,
            'avg_growth_per_hour': 0,
            'best_growth_periods': [],
            'insights': []
        }
    
    # Convert timestamp to datetime
    subscriber_df['snapshot_datetime'] = pd.to_datetime(subscriber_df['snapshot_timestamp'])
    subscriber_df = subscriber_df.sort_values('snapshot_datetime')
    
    # Calculate growth between snapshots
    growth_data = []
    hourly_growth = defaultdict(list)
    daily_growth = defaultdict(list)
    
    for i in range(1, len(subscriber_df)):
        current = subscriber_df.iloc[i]
        previous = subscriber_df.iloc[i-1]
        
        time_diff = (current['snapshot_datetime'] - previous['snapshot_datetime']).total_seconds() / 3600  # hours
        
        if time_diff > 0:
            sub_growth = current['subscriber_count'] - previous['subscriber_count']
            view_growth = current['total_views'] - previous['total_views']
            
            subs_per_hour = sub_growth / time_diff if time_diff > 0 else 0
            
            growth_record = {
                'period_start': previous['snapshot_datetime'],
                'period_end': current['snapshot_datetime'],
                'period_hours': round(time_diff, 2),
                'start_hour': previous['snapshot_hour'],
                'end_hour': current['snapshot_hour'],
                'subscriber_growth': sub_growth,
                'view_growth': view_growth,
                'subs_per_hour': round(subs_per_hour, 2),
                'start_subs': previous['subscriber_count'],
                'end_subs': current['subscriber_count']
            }
            
            growth_data.append(growth_record)
            
            # Group by hour of day
            for hour in range(previous['snapshot_hour'], current['snapshot_hour'] + 1):
                if hour < 24:
                    hourly_growth[hour].append(subs_per_hour)
            
            # Group by day of week
            day_of_week = current['snapshot_datetime'].weekday()
            daily_growth[day_of_week].append(subs_per_hour)
    
    # Calculate averages
    hourly_averages = {}
    for hour in range(24):
        if hour in hourly_growth:
            hourly_averages[hour] = {
                'hour': f"{hour:02d}:00",
                'avg_subs_per_hour': round(sum(hourly_growth[hour]) / len(hourly_growth[hour]), 2),
                'sample_count': len(hourly_growth[hour])
            }
        else:
            hourly_averages[hour] = {
                'hour': f"{hour:02d}:00",
                'avg_subs_per_hour': 0,
                'sample_count': 0
            }
    
    # Calculate daily averages
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    daily_averages = []
    for day in range(7):
        if day in daily_growth:
            avg = sum(daily_growth[day]) / len(daily_growth[day])
            daily_averages.append(round(avg, 2))
        else:
            daily_averages.append(0)
    
    # Find best growth periods
    best_periods = sorted(growth_data, key=lambda x: x['subs_per_hour'], reverse=True)[:5]
    
    # Calculate totals
    total_growth = subscriber_df.iloc[-1]['subscriber_count'] - subscriber_df.iloc[0]['subscriber_count']
    total_hours = (subscriber_df.iloc[-1]['snapshot_datetime'] - subscriber_df.iloc[0]['snapshot_datetime']).total_seconds() / 3600
    avg_growth_per_hour = total_growth / total_hours if total_hours > 0 else 0
    
    # Enhanced insights
    insights = []
    if total_growth > 0:
        insights.append(f"Total subscriber growth: +{total_growth} subscribers")
        insights.append(f"Average growth rate: {avg_growth_per_hour:.2f} subscribers/hour")
        
        # Advanced growth insights
        if len(growth_data) >= 3:
            recent_growth = sum([g['subscriber_growth'] for g in growth_data[-3:]])
            older_growth = sum([g['subscriber_growth'] for g in growth_data[:3]]) if len(growth_data) > 3 else 0
            if recent_growth > older_growth:
                insights.append("📈 Growth is accelerating in recent snapshots")
            elif recent_growth < older_growth and older_growth > 0:
                insights.append("📉 Growth has slowed compared to earlier periods")
    
    if best_periods:
        best_hour = max(hourly_averages.values(), key=lambda x: x['avg_subs_per_hour'])
        if best_hour['avg_subs_per_hour'] > 0:
            insights.append(f"Best growth hour: {best_hour['hour']} ({best_hour['avg_subs_per_hour']:.2f} subs/hour)")
    
    return {
        'growth_data': growth_data,
        'hourly_growth': hourly_averages,
        'daily_growth': {
            'day_names': day_names,
            'averages': daily_averages
        },
        'total_growth': total_growth,
        'avg_growth_per_hour': round(avg_growth_per_hour, 2),
        'best_growth_periods': best_periods,
        'insights': insights,
        'current_subscribers': subscriber_df.iloc[-1]['subscriber_count'] if not subscriber_df.empty else 0,
        'tracking_duration_hours': round(total_hours, 1) if total_hours > 0 else 0
    }

def analyze_hourly_performance(historical_df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze hourly view gain patterns from historical snapshots"""
    if historical_df.empty or len(historical_df) < 2:
        return {
            'hourly_averages': [{'hour': h, 'hour_formatted': f"{h:02d}:00", 'avg_views_per_hour': 0, 'measurement_count': 0, 'total_views_gained': 0} for h in range(24)],
            'total_snapshots': 0,
            'total_gain_records': 0,
            'insights': ['Need more historical data - run script multiple times!'],
            'data_quality': 'insufficient'
        }
    
    historical_df['snapshot_datetime'] = pd.to_datetime(historical_df['snapshot_timestamp'])
    historical_df = historical_df.sort_values(['video_id', 'snapshot_datetime'])
    
    hourly_gains = defaultdict(list)
    total_gain_records = 0
    
    # Calculate view gains between snapshots for each video
    for video_id in historical_df['video_id'].unique():
        video_data = historical_df[historical_df['video_id'] == video_id].sort_values('snapshot_datetime')
        
        if len(video_data) < 2:
            continue
            
        for i in range(1, len(video_data)):
            current = video_data.iloc[i]
            previous = video_data.iloc[i-1]
            
            time_diff_hours = (current['snapshot_datetime'] - previous['snapshot_datetime']).total_seconds() / 3600
            view_gain = current['current_views'] - previous['current_views']
            
            if time_diff_hours > 0 and view_gain >= 0:
                views_gained_per_hour = view_gain / time_diff_hours
                measurement_hour = current['snapshot_hour']
                
                hourly_gains[measurement_hour].append({
                    'views_per_hour': views_gained_per_hour,
                    'total_gain': view_gain
                })
                total_gain_records += 1
    
    # Calculate hourly averages
    hourly_averages = []
    for hour in range(24):
        if hour in hourly_gains and hourly_gains[hour]:
            gains = hourly_gains[hour]
            avg_views_per_hour = sum(g['views_per_hour'] for g in gains) / len(gains)
            
            hourly_averages.append({
                'hour': hour,
                'hour_formatted': f"{hour:02d}:00",
                'avg_views_per_hour': round(avg_views_per_hour, 2),
                'measurement_count': len(gains),
                'total_views_gained': sum(g['total_gain'] for g in gains)
            })
        else:
            hourly_averages.append({
                'hour': hour,
                'hour_formatted': f"{hour:02d}:00",
                'avg_views_per_hour': 0,
                'measurement_count': 0,
                'total_views_gained': 0
            })
    
    # Generate insights
    insights = []
    if total_gain_records > 0:
        total_snapshots = len(historical_df['snapshot_timestamp'].unique())
        insights.append(f"📊 Analyzed {total_gain_records} view gain measurements from {total_snapshots} snapshots")
        
        # Find peak hours
        peak_hours = [h for h in hourly_averages if h['measurement_count'] > 0]
        if peak_hours:
            best_hour = max(peak_hours, key=lambda x: x['avg_views_per_hour'])
            insights.append(f"🔥 Peak viewing hour: {best_hour['hour_formatted']} ({best_hour['avg_views_per_hour']:.1f} views/hour avg)")
            
            # Coverage info
            hours_with_data = len(peak_hours)
            if hours_with_data >= 12:
                insights.append(f"✅ Good coverage: {hours_with_data}/24 hours have data")
            else:
                insights.append(f"⚠️ Limited coverage: {hours_with_data}/24 hours have data")
    
    return {
        'hourly_averages': hourly_averages,
        'total_snapshots': len(historical_df['snapshot_timestamp'].unique()) if not historical_df.empty else 0,
        'total_gain_records': total_gain_records,
        'insights': insights,
        'data_quality': 'good' if total_gain_records >= 10 else 'limited' if total_gain_records > 0 else 'insufficient'
    }

def analyze_all_data(videos: List[Dict[str, Any]], historical_df: pd.DataFrame, channel_details: Dict[str, Any], subscriber_df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze all data and create comprehensive analytics with enhanced public metrics"""
    
    # Basic analytics
    total_views = sum(v['views'] for v in videos)
    total_videos = len(videos)
    total_likes = sum(v['likes'] for v in videos)
    total_comments = sum(v['comments'] for v in videos)
    
    # Add hourly performance analysis
    hourly_performance = analyze_hourly_performance(historical_df)
    
    avg_views_per_hour = sum(v['views_per_hour'] for v in videos) / total_videos if total_videos > 0 else 0
    
    # Enhanced engagement calculations
    avg_engagement_rate = ((total_likes + total_comments) / total_views * 100) if total_views > 0 else 0
    avg_like_rate = (total_likes / total_views * 100) if total_views > 0 else 0
    avg_comment_rate = (total_comments / total_views * 100) if total_views > 0 else 0
    
    # Viral video counts
    viral_10k = len([v for v in videos if v['views'] >= 10000])
    viral_100k = len([v for v in videos if v['views'] >= 100000])
    viral_1m = len([v for v in videos if v['views'] >= 1000000])
    
    # Recent performance analysis
    recent_videos = [v for v in videos if v['days_since_published'] <= 30]
    recent_avg_views_per_hour = sum(v['views_per_hour'] for v in recent_videos) / len(recent_videos) if recent_videos else 0
    
    # Posting time analysis
    posting_hour_performance = defaultdict(list)
    for video in videos:
        if video['published_hour'] is not None:
            posting_hour_performance[video['published_hour']].append(video['views_per_hour'])
    
    # Calculate hourly averages
    hourly_data = []
    for hour in range(24):
        if hour in posting_hour_performance:
            performances = posting_hour_performance[hour]
            avg_performance = sum(performances) / len(performances)
            hourly_data.append({
                'hour': hour,
                'hour_formatted': f"{hour:02d}:00",
                'video_count': len(performances),
                'avg_views_per_hour': round(avg_performance, 2)
            })
        else:
            hourly_data.append({
                'hour': hour,
                'hour_formatted': f"{hour:02d}:00",
                'video_count': 0,
                'avg_views_per_hour': 0
            })
    
    # Day of week analysis
    daily_performance = defaultdict(list)
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for video in videos:
        if video.get('published_at'):
            try:
                pub_date = datetime.datetime.fromisoformat(video['published_at'].replace('Z', '+00:00'))
                day_of_week = pub_date.weekday()
                daily_performance[day_of_week].append(video['views_per_hour'])
            except:
                pass
    
    daily_averages = []
    for day in range(7):
        if day in daily_performance:
            avg = sum(daily_performance[day]) / len(daily_performance[day])
            daily_averages.append(round(avg, 2))
        else:
            daily_averages.append(0)
    
    # Find best posting times
    best_hours = sorted([h for h in hourly_data if h['video_count'] > 0], 
                       key=lambda x: x['avg_views_per_hour'], reverse=True)[:5]
    
    # Enhanced insights based on public data
    insights = []
    if best_hours:
        insights.append(f"Best posting time: {best_hours[0]['hour_formatted']} ({best_hours[0]['avg_views_per_hour']:.1f} views/hour)")
    
    insights.append(f"Viral success rate: {round((viral_10k/total_videos)*100, 1)}% of videos hit 10K+ views")
    insights.append(f"Average video age: {sum(v['days_since_published'] for v in videos)/len(videos):.1f} days")
    
    if recent_videos:
        insights.append(f"Recent videos (30d): {recent_avg_views_per_hour:.1f} avg views/hour")
    
    # Advanced insights based on enhanced metrics
    # High-performer analysis
    high_performers = [v for v in videos if v['views_per_hour'] > avg_views_per_hour * 1.5]
    if high_performers:
        avg_high_performer_age = sum(v['days_since_published'] for v in high_performers) / len(high_performers)
        insights.append(f"🚀 {len(high_performers)} high-performers average {avg_high_performer_age:.1f} days old")
    
    # Content freshness insights
    very_recent = [v for v in videos if v['days_since_published'] <= 7]
    if very_recent:
        recent_performance = sum(v['views_per_hour'] for v in very_recent) / len(very_recent)
        insights.append(f"📊 Last 7 days: {recent_performance:.1f} avg views/hour ({len(very_recent)} videos)")
    
    # Engagement pattern insights
    high_engagement = [v for v in videos if v['engagement_rate'] > avg_engagement_rate * 1.2]
    if high_engagement:
        insights.append(f"💬 {len(high_engagement)} videos show above-average engagement patterns")
    
    # Consistency insights
    if len(videos) >= 5:
        view_rates = [v['views_per_hour'] for v in videos if v['views_per_hour'] > 0]
        if view_rates:
            max_rate = max(view_rates)
            min_rate = min(view_rates)
            consistency = 1 - ((max_rate - min_rate) / max_rate) if max_rate > 0 else 0
            if consistency > 0.7:
                insights.append("📈 Channel shows consistent performance across videos")
            else:
                insights.append("📊 Performance varies significantly between videos")
    
    # Momentum insights
    high_momentum = [v for v in videos if v['momentum_score'] > 100]  # Arbitrary threshold
    if high_momentum:
        insights.append(f"⚡ {len(high_momentum)} videos have high momentum scores")
    
    # Best and worst performers
    best_performer = max(videos, key=lambda x: x['views_per_hour']) if videos else None
    worst_performer = min(videos, key=lambda x: x['views_per_hour']) if videos else None
    
    # Analyze subscriber growth
    subscriber_analysis = analyze_subscriber_growth(subscriber_df)
    
    return {
        'channel_info': channel_details,
        'subscriber_analytics': subscriber_analysis,
        'hourly_performance_analytics': hourly_performance,
        'summary': {
            'total_videos': total_videos,
            'total_views': total_views,
            'total_views_formatted': format_number(total_views),
            'total_likes': total_likes,
            'total_likes_formatted': format_number(total_likes),
            'total_comments': total_comments,
            'total_comments_formatted': format_number(total_comments),
            'avg_views_per_hour': round(avg_views_per_hour, 2),
            'avg_engagement_rate': round(avg_engagement_rate, 2),
            'avg_like_rate': round(avg_like_rate, 2),
            'avg_comment_rate': round(avg_comment_rate, 2),
            'viral_videos_10k': viral_10k,
            'viral_videos_100k': viral_100k,
            'viral_videos_1m': viral_1m,
            'viral_rate_10k': round((viral_10k / total_videos) * 100, 1) if total_videos > 0 else 0,
            'recent_avg_views_per_hour': round(recent_avg_views_per_hour, 2),
            'snapshots_count': len(historical_df['snapshot_timestamp'].unique()) if not historical_df.empty else 1,
            'last_updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        },
        'top_videos': videos[:15],  # Top 15 videos by views/hour
        'hourly_posting_data': hourly_data,
        'daily_posting_data': {
            'day_names': day_names,
            'averages': daily_averages
        },
        'best_posting_times': best_hours,
        'insights': insights,
        'best_performer': best_performer,
        'worst_performer': worst_performer,
        'chart_data': {
            'hourly_performance_chart': {
                'labels': [h['hour_formatted'] for h in hourly_performance['hourly_averages']],
                'data': [h['avg_views_per_hour'] for h in hourly_performance['hourly_averages']],
                'measurement_counts': [h['measurement_count'] for h in hourly_performance['hourly_averages']]
            },
            'top_videos_chart': {
                'labels': [v['title'][:25] + '...' if len(v['title']) > 25 else v['title'] for v in videos[:10]],
                'data': [v['views_per_hour'] for v in videos[:10]]
            },
            'engagement_chart': {
                'labels': [v['title'][:15] + '...' if len(v['title']) > 15 else v['title'] for v in videos[:6]],
                'data': [v['engagement_rate'] for v in videos[:6]]
            },
            'hourly_chart': {
                'labels': [h['hour_formatted'] for h in hourly_data],
                'data': [h['avg_views_per_hour'] for h in hourly_data]
            },
            'daily_chart': {
                'labels': day_names,
                'data': daily_averages
            },
            'momentum_chart': {
                'labels': [v['title'][:20] + '...' if len(v['title']) > 20 else v['title'] for v in videos[:8]],
                'data': [v['momentum_score'] for v in videos[:8]],
                'ages': [v['days_since_published'] for v in videos[:8]]
            },
            'subscriber_growth_chart': {
                'labels': [h['hour'] for h in subscriber_analysis['hourly_growth'].values()],
                'data': [h['avg_subs_per_hour'] for h in subscriber_analysis['hourly_growth'].values()]
            },
            'subscriber_timeline': subscriber_analysis['growth_data'][-20:] if subscriber_analysis['growth_data'] else []  # Last 20 data points
        }
    }

def serve_dashboard():
    """Start a local HTTP server and keep it running"""
    import http.server
    import socketserver
    import time
    
    # Change to the data directory
    original_dir = os.getcwd()
    data_dir_path = os.path.join(original_dir, DATA_DIR)
    
    if not os.path.exists(data_dir_path):
        print(f"✗ Data directory not found: {data_dir_path}")
        return
    
    print(f"📁 Serving files from: {data_dir_path}")
    os.chdir(data_dir_path)
    
    # Find an available port
    port = 8000
    httpd = None
    for attempt_port in range(8000, 8010):
        try:
            httpd = socketserver.TCPServer(("", attempt_port), http.server.SimpleHTTPRequestHandler)
            port = attempt_port
            break
        except OSError:
            continue
    
    if not httpd:
        print("✗ Could not find an available port")
        os.chdir(original_dir)
        return
    
    dashboard_url = f"http://localhost:{port}/dashboard.html"
    
    try:
        webbrowser.open(dashboard_url)
        print(f"✓ Dashboard opened at: {dashboard_url}")
    except Exception as e:
        print(f"✗ Error opening browser: {e}")
        print(f"💡 Manually open: {dashboard_url}")
    
    print(f"🚀 Server running on port {port}")
    print("📊 Dashboard should now load properly!")
    print("=" * 50)
    print("🔥 SERVER IS RUNNING - Keep this terminal open!")
    print("⏹️  Press Ctrl+C to stop the server")
    print("🌐 Dashboard URL: " + dashboard_url)
    print("=" * 50)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down server...")
        httpd.shutdown()
        httpd.server_close()
        print("✓ Server stopped")
    finally:
        os.chdir(original_dir)

def open_dashboard():
    """Open the dashboard HTML file via local server"""
    dashboard_path = os.path.join(DATA_DIR, DASHBOARD_HTML)
    analytics_path = os.path.join(DATA_DIR, ANALYTICS_JSON)
    
    print(f"\n🔍 Checking files...")
    print(f"Dashboard: {dashboard_path} - {'✓ Exists' if os.path.exists(dashboard_path) else '✗ Missing'}")
    print(f"Analytics: {analytics_path} - {'✓ Exists' if os.path.exists(analytics_path) else '✗ Missing'}")
    
    if not os.path.exists(dashboard_path):
        print(f"✗ Dashboard not found at {dashboard_path}")
        print("💡 Make sure you have dashboard.html in the fastfriends_data folder")
        print("💡 You can copy the dashboard.html file to this folder")
        return
    
    if not os.path.exists(analytics_path):
        print(f"✗ Analytics data not found at {analytics_path}")
        print("💡 Run the data collection first to generate analytics_data.json")
        return
    
    # Start local server and keep it running
    serve_dashboard()

def main():
    """Main function - Enhanced data collection with advanced public metrics"""
    print("Fast Friends Analytics - Enhanced Data Collector")
    print("=" * 60)
    print("📊 Collecting enhanced video + subscriber analytics...")
    print("💾 Saving to /fastfriends_data/ folder")
    print("🚀 Maximizing insights from public YouTube data")
    print("=" * 60)
    
    load_dotenv()
    API_KEY = os.getenv('YT_API_KEY')
    
    if not API_KEY:
        raise Exception("YouTube API key not found. Create .env with YT_API_KEY=your_key")
    
    print("✓ API key loaded")
    
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    print("✓ YouTube API client initialized")
    
    # Find Fast Friends channel
    channel_id = get_channel_id_from_handle(youtube, '@FastFriendsYT')
    
    if not channel_id:
        print("✗ Could not find Fast Friends channel")
        return
    
    # Get channel details (including subscriber count)
    print("\n📊 Getting channel details...")
    channel_details = get_channel_details(youtube, channel_id)
    
    if not channel_details:
        print("✗ Could not get channel details")
        return
    
    print(f"✓ Channel: {channel_details['channel_title']}")
    print(f"  Subscribers: {channel_details['subscriber_count_formatted']}")
    print(f"  Total Views: {channel_details['total_views_formatted']}")
    
    # Capture subscriber snapshot
    print("\n👥 Capturing subscriber snapshot...")
    subscriber_snapshot_df = capture_subscriber_snapshot(channel_details)
    subscriber_df = save_subscriber_snapshot(subscriber_snapshot_df)
    
    # Get current video data with enhanced analytics
    print("\n📡 Fetching enhanced video data...")
    current_videos = get_all_channel_videos(youtube, channel_id, max_videos=100)
    
    if not current_videos:
        print("✗ No videos found")
        return
    
    print(f"✓ Retrieved {len(current_videos)} videos with enhanced metrics")
    
    # Capture and save video snapshot for time-series
    print("\n💾 Saving enhanced video snapshot to time-series database...")
    video_snapshot_df = capture_snapshot(current_videos)
    historical_df = save_snapshot(video_snapshot_df)
    
    # Analyze all data with enhanced insights
    print("\n🧠 Analyzing enhanced performance data...")
    analytics_data = analyze_all_data(current_videos, historical_df, channel_details, subscriber_df)
    
    # Save analytics data as JSON
    print("\n📊 Saving enhanced analytics data...")
    os.makedirs(DATA_DIR, exist_ok=True)
    analytics_file = os.path.join(DATA_DIR, ANALYTICS_JSON)
    with open(analytics_file, 'w') as f:
        json.dump(analytics_data, f, indent=2, default=str)
    
    # Verify file was created
    if os.path.exists(analytics_file):
        file_size = os.path.getsize(analytics_file)
        print(f"✓ Enhanced analytics data saved: {analytics_file} ({file_size} bytes)")
    else:
        print(f"✗ Error: Analytics file not created at {analytics_file}")
    
    # Print enhanced summary
    print(f"\n{'='*70}")
    print("ENHANCED DATA COLLECTION COMPLETE")
    print(f"{'='*70}")
    print(f"📺 Channel: {channel_details['channel_title']}")
    print(f"👥 Subscribers: {channel_details['subscriber_count_formatted']}")
    print(f"📊 Videos: {analytics_data['summary']['total_videos']}")
    print(f"👀 Total Views: {analytics_data['summary']['total_views_formatted']}")
    print(f"⚡ Avg Views/Hour: {analytics_data['summary']['avg_views_per_hour']}")
    print(f"💬 Avg Engagement Rate: {analytics_data['summary']['avg_engagement_rate']:.2f}%")
    print(f"👍 Avg Like Rate: {analytics_data['summary']['avg_like_rate']:.2f}%")
    print(f"💭 Avg Comment Rate: {analytics_data['summary']['avg_comment_rate']:.2f}%")
    
    # Subscriber analytics summary
    if analytics_data.get('subscriber_analytics'):
        sub_analytics = analytics_data['subscriber_analytics']
        print(f"📈 Subscriber Growth: {sub_analytics['total_growth']} total")
        print(f"⏱️  Growth Rate: {sub_analytics['avg_growth_per_hour']:.2f} subs/hour")
    
    # Hourly performance summary
    if analytics_data.get('hourly_performance_analytics'):
        hourly_analytics = analytics_data['hourly_performance_analytics']
        print(f"⏰ Hourly Analysis: {hourly_analytics['total_gain_records']} measurements from {hourly_analytics['total_snapshots']} snapshots")
    
    print(f"\n📁 Files saved in /{DATA_DIR}/:")
    print(f"  📋 {HISTORICAL_CSV} (enhanced video time-series)")
    print(f"  👥 {SUBSCRIBER_CSV} (subscriber tracking)")
    print(f"  📊 {ANALYTICS_JSON} (enhanced analytics data)")
    
    print(f"\n🎯 Next step: Open {DATA_DIR}/dashboard.html to view enhanced analytics!")
    print(f"🔄 Run this script regularly to build historical data!")
    print(f"\n🚀 New Enhanced Features:")
    print(f"  • Engagement rate analysis")
    print(f"  • Video momentum scoring")
    print(f"  • Content freshness metrics")
    print(f"  • Advanced pattern recognition")
    print(f"  • Performance consistency tracking")
    print(f"  • Hourly view gain analysis")
    print(f"{'='*70}")
    
    # Automatically open dashboard
    open_dashboard()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--dashboard":
        # Just open the dashboard
        open_dashboard()
    else:
        # Run enhanced data collection
        main()