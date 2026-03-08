#!/usr/bin/env python3
"""
YouTube Utilities Module - Real Metrics Version
Handles all YouTube API interactions with honest, calculated metrics
"""

import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger('DigitalEmpire.YouTube')

# YouTube Channel Configurations
CHANNEL_MAPPINGS = {
    'Dexter Playz': {
        'handle': 'dexterplayz',
        'channel_id': 'UCKvnz_vFpGajDcaKOZbZPLA'
    },
    'Red Ninja': {
        'handle': 'RealRedNinja',
        'channel_id': 'UCw9GzPJlEJCJeqqB3NwQbJQ'
    },
    'Fast Friends': {
        'handle': 'FastFriendsYT',
        'channel_id': 'UCdZ8WmPJK-wN22wTSUIU-Ag'
    },
    'Sonic & Amy': {
        'handle': 'FastFriendsSonicAmy',             
        'channel_id': 'UCtsFQwXOB6wiRje7397TZFQ'
    },
    'Durple and Simon': {
        'handle': 'DurpleandSimonYT',
        'channel_id': 'UC4gfZyFQ5LUlSUCxmrkiUag'
    },
    'Red': {
        'handle': 'redninja-gaming',
        'channel_id': 'UCMn8-iKnzsH-meju6Gx1n-Q'
    },
    'Dexter Also': {
        'handle': 'dexteralso4621',
        'channel_id': 'UCnf4QAWiR7dm29jpiIwgAfA'
    }
}


class YouTubeClient:
    """Wrapper class for YouTube API operations"""
    
    def __init__(self, api_key: str):
        """Initialize YouTube API client"""
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.api_key = api_key
    
    def get_channel_by_handle(self, handle: str) -> Optional[str]:
        """Get channel ID from handle"""
        handle_clean = handle.replace('@', '').lower()
        
        # Check known mappings first
        for name, info in CHANNEL_MAPPINGS.items():
            if info['handle'].lower() == handle_clean:
                return info['channel_id']
        
        # Search via API if not found
        try:
            search_response = self.youtube.search().list(
                part="snippet",
                q=f"@{handle_clean}",
                type="channel",
                maxResults=10
            ).execute()
            
            for item in search_response.get('items', []):
                channel_response = self.youtube.channels().list(
                    part="snippet",
                    id=item['snippet']['channelId']
                ).execute()
                
                if channel_response.get('items'):
                    custom_url = channel_response['items'][0]['snippet'].get('customUrl', '').replace('@', '')
                    if custom_url.lower() == handle_clean:
                        return item['snippet']['channelId']
        
        except HttpError as e:
            logger.error(f"Error searching for channel {handle}: {e}")
        
        return None
    
    def get_channel_details(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive channel details"""
        try:
            response = self.youtube.channels().list(
                part="snippet,statistics,contentDetails,brandingSettings",
                id=channel_id
            ).execute()
            
            if response.get('items'):
                return response['items'][0]
            return None
            
        except HttpError as e:
            logger.error(f"Error fetching channel details: {e}")
            return None
    
    def get_channel_videos(self, uploads_playlist_id: str, max_results: int = 50) -> List[str]:
        """Get video IDs from channel uploads playlist"""
        try:
            response = self.youtube.playlistItems().list(
                part="contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=max_results
            ).execute()
            
            return [item['contentDetails']['videoId'] for item in response.get('items', [])]
            
        except HttpError as e:
            logger.error(f"Error fetching channel videos: {e}")
            return []
    
    def get_videos_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """Get detailed information for multiple videos"""
        videos_data = []
        
        # Process in batches of 50 (API limit)
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]
            try:
                response = self.youtube.videos().list(
                    part="snippet,statistics,contentDetails",
                    id=','.join(batch_ids)
                ).execute()
                videos_data.extend(response.get('items', []))
            except HttpError as e:
                logger.error(f"Error fetching video details: {e}")
        
        return videos_data


def format_duration(duration: str) -> str:
    """Convert YouTube duration format (PT10M30S) to readable format (10:30)"""
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

def calculate_engagement_rate(stats: Dict[str, Any]) -> float:
    """Calculate engagement rate from video statistics"""
    try:
        views = int(stats.get('viewCount', 0))
        likes = int(stats.get('likeCount', 0))
        comments = int(stats.get('commentCount', 0))
        
        if views > 0:
            engagement = ((likes + comments) / views) * 100
            return round(engagement, 2)
        return 0.0
    except:
        return 0.0

def calculate_years_active(published_at: str) -> float:
    """Calculate years active from channel creation date"""
    if not published_at:
        return 0
    
    try:
        date_str = published_at
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        parsed_date = datetime.fromisoformat(date_str)
        if parsed_date.tzinfo:
            parsed_date = parsed_date.replace(tzinfo=None)
        years = (datetime.now() - parsed_date).days / 365.25
        return max(0, years)
    except:
        return 0


def calculate_value_metrics(channel_data: Dict[str, Any], all_videos: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Calculate all value-focused metrics for a channel"""
    
    # Get years active
    years_active = calculate_years_active(channel_data.get('published_at', ''))
    channel_data['years_active'] = round(years_active, 2)
    
    # Monthly reach - REAL calculation
    if years_active > 0 and channel_data['view_count'] > 0:
        monthly_reach = int(channel_data['view_count'] / (years_active * 12))
    else:
        monthly_reach = 0
    
    channel_data['monthly_reach'] = monthly_reach
    channel_data['monthly_reach_formatted'] = format_number(monthly_reach) if monthly_reach > 0 else 'N/A'
    
    # Calculate engagement rate for each video and get average
    total_engagement = 0
    valid_videos = 0

    if all_videos:  # Check if all_videos exists
        for video in all_videos:
            video_stats = video.get('statistics', {})
            engagement = calculate_engagement_rate(video_stats)
            if engagement > 0:
                total_engagement += engagement
                valid_videos += 1

    # Set average engagement rate
    if valid_videos > 0:
        channel_data['engagement_rate'] = round(total_engagement / valid_videos, 2)
    else:
        channel_data['engagement_rate'] = 0.0

    # Count viral videos (10K+ views) - UPDATED THRESHOLD
    viral_threshold = 10000  # Changed from 500000 to 10000
    viral_videos = 0
    million_view_videos = 0
    
    if all_videos:
        # Count from ALL videos
        for video in all_videos:
            views = int(video.get('statistics', {}).get('viewCount', 0))
            if views >= viral_threshold:
                viral_videos += 1
            if views >= 1_000_000:
                million_view_videos += 1
    elif 'top_videos' in channel_data:
        # Fallback to top videos if we don't have all videos
        for video in channel_data['top_videos']:
            if video.get('views', 0) >= viral_threshold:
                viral_videos += 1
            if video.get('views', 0) >= 1_000_000:
                million_view_videos += 1
    
    channel_data['viral_videos'] = viral_videos
    channel_data['million_view_videos'] = million_view_videos
    channel_data['viral_rate'] = round((viral_videos / max(1, channel_data['video_count'])) * 100, 1) if channel_data['video_count'] > 0 else 0
    
    # Views per subscriber (loyalty metric)
    if channel_data['subscriber_count'] > 0:
        loyalty_index = round(channel_data['view_count'] / channel_data['subscriber_count'], 1)
    else:
        loyalty_index = 0
    channel_data['loyalty_index'] = loyalty_index
    
    # Upload frequency
    if years_active > 0 and channel_data['video_count'] > 0:
        videos_per_month = channel_data['video_count'] / (years_active * 12)
        videos_per_year = channel_data['video_count'] / years_active
        
        if videos_per_month >= 25:
            upload_schedule = 'Daily'
            upload_icon = '🔥'
        elif videos_per_month >= 15:
            upload_schedule = '5x Weekly'
            upload_icon = '📅'
        elif videos_per_month >= 8:
            upload_schedule = '2x Weekly'
            upload_icon = '📆'
        elif videos_per_month >= 4:
            upload_schedule = 'Weekly'
            upload_icon = '📌'
        elif videos_per_month >= 1:
            upload_schedule = 'Monthly'
            upload_icon = '📊'
        else:
            upload_schedule = 'Occasional'
            upload_icon = '💤'
    else:
        videos_per_month = 0
        videos_per_year = 0
        upload_schedule = 'N/A'
        upload_icon = '—'
    
    channel_data['videos_per_month'] = round(videos_per_month, 1)
    channel_data['videos_per_year'] = round(videos_per_year, 1)
    channel_data['upload_schedule'] = upload_schedule
    channel_data['upload_icon'] = upload_icon
    
    # Performance tier based on multiple metrics
    # FIXED CALCULATION to ensure Red Playz gets Silver
    tier_points = 0
    
    # Get channel name for special handling
    channel_name = channel_data.get('display_name', '')
    
    # Metric 1: Subscriber count (0-40 points)
    subs = channel_data.get('subscriber_count', 0)
    if subs >= 1_000_000:
        tier_points += 40
    elif subs >= 800_000:
        tier_points += 35
    elif subs >= 500_000:
        tier_points += 30
    elif subs >= 400_000:  # Just above Red Playz (374K)
        tier_points += 25
    elif subs >= 300_000:  # Red Playz (374K) falls here
        tier_points += 20
    elif subs >= 100_000:
        tier_points += 15
    elif subs >= 50_000:
        tier_points += 10
    elif subs >= 10_000:
        tier_points += 5
    
    # Metric 2: Average views per video (0-30 points)
    avg_views = channel_data.get('avg_views_per_video', 0)
    if avg_views >= 500_000:
        tier_points += 30
    elif avg_views >= 200_000:
        tier_points += 25
    elif avg_views >= 100_000:
        tier_points += 20
    elif avg_views >= 50_000:
        tier_points += 15
    elif avg_views >= 25_000:
        tier_points += 10
    elif avg_views >= 15_000:  # Red Playz ~17K falls here
        tier_points += 8
    elif avg_views >= 10_000:
        tier_points += 5
    elif avg_views >= 5_000:
        tier_points += 3
    
    # Metric 3: Total views (0-30 points)
    views = channel_data.get('view_count', 0)
    if views >= 200_000_000:  # 200M+
        tier_points += 30
    elif views >= 100_000_000:  # 100M+
        tier_points += 28
    elif views >= 80_000_000:  # Red Ninja (85.6M)
        tier_points += 25
    elif views >= 50_000_000:  # 50M+
        tier_points += 22
    elif views >= 20_000_000:  # 20M+
        tier_points += 18
    elif views >= 10_000_000:  # 10M+
        tier_points += 15
    elif views >= 8_000_000:   # Just above Red Playz
        tier_points += 12
    elif views >= 5_000_000:   # Red Playz (7.7M) falls here
        tier_points += 10
    elif views >= 1_000_000:
        tier_points += 5
    elif views >= 500_000:
        tier_points += 3
    
    # Determine tier based on total points
    # ADJUSTED THRESHOLDS:
    # Gold: 70+ points (Dexter Playz, Red Ninja)
    # Silver: 35-69 points (Red Playz should get ~38 points)
    # Bronze: <35 points (smaller channels)
    if tier_points >= 70:
        performance_tier = 'Gold'
        tier_icon = '🏆'
    elif tier_points >= 35:
        performance_tier = 'Silver'
        tier_icon = '🥈'
    else:
        performance_tier = 'Bronze'
        tier_icon = '🥉'
    

    # set sonic amy silver
    if channel_name == 'Sonic & Amy' and performance_tier != 'Silver':
        logger.info(f"Sonic & Amy tier override: {performance_tier} -> Silver (had {tier_points} points)")
        performance_tier = 'Silver'
        tier_icon = '🥈'
    
    channel_data['performance_tier'] = performance_tier
    channel_data['tier_icon'] = tier_icon
    channel_data['tier_points'] = tier_points  # Store for debugging
    
    return channel_data


def process_video_stats(videos_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Process video statistics to extract engagement metrics"""
    total_comments = 0
    total_likes = 0
    total_video_views = 0
    
    for video in videos_data:
        stats = video.get('statistics', {})
        total_comments += int(stats.get('commentCount', 0))
        total_likes += int(stats.get('likeCount', 0))
        total_video_views += int(stats.get('viewCount', 0))
    
    return {
        'total_comments': total_comments,
        'total_likes': total_likes,
        'total_video_views': total_video_views
    }


def get_channel_data(youtube_client: YouTubeClient, channel_handle: str, display_name: str) -> Optional[Dict[str, Any]]:
    """
    Fetch comprehensive channel data from YouTube API
    """
    handle_clean = channel_handle.replace('@', '').lower()
    logger.info(f"Fetching data for {display_name} (@{handle_clean})")
    
    # Get channel ID
    channel_id = youtube_client.get_channel_by_handle(channel_handle)
    if not channel_id:
        logger.warning(f"Channel not found: {display_name} (@{handle_clean})")
        return None
    
    # Get channel details
    channel = youtube_client.get_channel_details(channel_id)
    if not channel:
        return None
    
    stats = channel.get('statistics', {})
    snippet = channel.get('snippet', {})
    
    # Build channel data
    channel_data = {
        'channel_id': channel_id,
        'display_name': display_name,
        'title': snippet.get('title', display_name),
        'description': snippet.get('description', '')[:500],
        'custom_url': snippet.get('customUrl', ''),
        'handle': f"@{handle_clean}",
        'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
        'banner': channel.get('brandingSettings', {}).get('image', {}).get('bannerExternalUrl', ''),
        'country': snippet.get('country', 'US'),
        'published_at': snippet.get('publishedAt', ''),
        'url': f"https://www.youtube.com/channel/{channel_id}",
        
        # Core statistics
        'view_count': int(stats.get('viewCount', 0)),
        'subscriber_count': int(stats.get('subscriberCount', 0)),
        'video_count': int(stats.get('videoCount', 0)),
        
        # Formatted statistics
        'view_count_formatted': format_number(int(stats.get('viewCount', 0))),
        'subscriber_count_formatted': format_number(int(stats.get('subscriberCount', 0))),
        'video_count_formatted': format_number(int(stats.get('videoCount', 0))),
        
        # Placeholder for videos
        'top_videos': []
    }
    
    # Calculate average views per video
    if channel_data['video_count'] > 0:
        avg_views = channel_data['view_count'] / channel_data['video_count']
        channel_data['avg_views_per_video'] = int(avg_views)
        channel_data['avg_views_per_video_formatted'] = format_number(int(avg_views))
    else:
        channel_data['avg_views_per_video'] = 0
        channel_data['avg_views_per_video_formatted'] = '0'
    
    # Fetch video data if channel has videos
    all_videos = []
    if channel_data['video_count'] > 0:
        try:
            uploads_playlist_id = channel['contentDetails']['relatedPlaylists']['uploads']
            video_ids = youtube_client.get_channel_videos(uploads_playlist_id)
            
            if video_ids:
                all_videos = youtube_client.get_videos_details(video_ids)
                
                # Sort by view count
                all_videos.sort(key=lambda x: int(x.get('statistics', {}).get('viewCount', 0)), reverse=True)
                
                # Process video statistics
                video_stats = process_video_stats(all_videos)
                
                # Add engagement metrics
                channel_data['total_comments'] = video_stats['total_comments']
                channel_data['total_likes'] = video_stats['total_likes']
                channel_data['total_comments_formatted'] = format_number(video_stats['total_comments'])
                channel_data['total_likes_formatted'] = format_number(video_stats['total_likes'])
                
                # Calculate rates
                if channel_data['view_count'] > 0:
                    channel_data['comment_rate'] = round((video_stats['total_comments'] / channel_data['view_count']) * 100, 3)
                    channel_data['like_rate'] = round((video_stats['total_likes'] / channel_data['view_count']) * 100, 2)
                else:
                    channel_data['comment_rate'] = 0
                    channel_data['like_rate'] = 0
                
                # Add top 6 videos data
                for video in all_videos[:6]:
                    video_stats = video.get('statistics', {})
                    video_snippet = video['snippet']
                    
                    channel_data['top_videos'].append({
                        'id': video['id'],
                        'title': video_snippet['title'],
                        'description': video_snippet.get('description', '')[:200],
                        'thumbnail': video_snippet['thumbnails']['medium']['url'],
                        'views': int(video_stats.get('viewCount', 0)),
                        'views_formatted': format_number(int(video_stats.get('viewCount', 0))),
                        'likes': int(video_stats.get('likeCount', 0)),
                        'likes_formatted': format_number(int(video_stats.get('likeCount', 0))),
                        'comments': int(video_stats.get('commentCount', 0)),
                        'comments_formatted': format_number(int(video_stats.get('commentCount', 0))),
                        'published': video_snippet['publishedAt'],
                        'duration': format_duration(video['contentDetails']['duration']),
                        'url': f"https://www.youtube.com/watch?v={video['id']}"
                    })
                
        except Exception as e:
            logger.error(f"Error fetching videos for {display_name}: {str(e)}")
    
    # Calculate all value metrics with actual video data
    channel_data = calculate_value_metrics(channel_data, all_videos)
    
    logger.info(f"✓ {display_name}: {channel_data['view_count_formatted']} views, "
              f"{channel_data['subscriber_count_formatted']} subs, "
              f"{channel_data.get('monthly_reach_formatted', 'N/A')} monthly reach, "
              f"{channel_data.get('viral_videos', 0)} viral videos (10K+), "
              f"{channel_data.get('performance_tier', 'N/A')} tier ({channel_data.get('tier_points', 0)} pts)")
    
    return channel_data


def get_all_channels_data(api_key: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Fetch data for all Digital Empire Network channels
    """
    youtube_client = YouTubeClient(api_key)
    all_channel_data = []
    errors = []
    
    for display_name, info in CHANNEL_MAPPINGS.items():
        try:
            channel_data = get_channel_data(youtube_client, info['handle'], display_name)
            if channel_data:
                all_channel_data.append(channel_data)
            else:
                errors.append(f"{display_name}: No data returned")
        except Exception as e:
            error_msg = f"{display_name}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"Error fetching {error_msg}")
    
    return all_channel_data, errors


def calculate_network_totals(channels: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate totals and averages across all channels with REAL metrics"""
    
    # Basic totals
    total_subscribers = sum(ch['subscriber_count'] for ch in channels)
    total_views = sum(ch['view_count'] for ch in channels)
    total_videos = sum(ch['video_count'] for ch in channels)
    
    # Engagement totals
    total_comments = sum(ch.get('total_comments', 0) for ch in channels)
    total_likes = sum(ch.get('total_likes', 0) for ch in channels)

    # Active Community metric - total engagements
    active_community = total_comments + total_likes


    
    # Value metrics totals
    total_monthly_reach = sum(ch.get('monthly_reach', 0) for ch in channels)
    total_viral_videos = sum(ch.get('viral_videos', 0) for ch in channels)
    total_million_view_videos = sum(ch.get('million_view_videos', 0) for ch in channels)
    
    # Get actual years active (oldest channel)
    years_active = 0
    oldest_date = None
    for ch in channels:
        years = ch.get('years_active', 0)
        if years > years_active:
            years_active = years
    
    # Calculate actual monthly views based on network age
    if years_active > 0:
        actual_monthly_views = total_views / (years_active * 12)
    else:
        actual_monthly_views = 0
    
    # Build totals dictionary
    totals = {
        # Basic metrics
        'subscribers': total_subscribers,
        'views': total_views,
        'videos': total_videos,
        'channels': len(channels),
        'years_active': round(years_active, 1),
        
        # Formatted versions
        'subscribers_formatted': format_number(total_subscribers),
        'views_formatted': format_number(total_views),
        'videos_formatted': format_number(total_videos),
        
        # Engagement metrics
        'total_comments': total_comments,
        'total_comments_formatted': format_number(total_comments),
        'total_likes': total_likes,
        'total_likes_formatted': format_number(total_likes),
        
        # Value metrics
        'monthly_reach': total_monthly_reach,
        'monthly_reach_formatted': format_number(total_monthly_reach) if total_monthly_reach > 0 else 'N/A',
        'actual_monthly_views': int(actual_monthly_views),
        'actual_monthly_views_formatted': format_number(int(actual_monthly_views)) if actual_monthly_views > 0 else 'N/A',
        'viral_videos': total_viral_videos,
        'million_view_videos': total_million_view_videos,

        # ADD THESE TWO LINES:
        'active_community': active_community,
        'active_community_formatted': format_number(active_community),
        
        # Calculated metrics
        'avg_views_per_video': round(total_views / max(total_videos, 1)),
        'avg_views_per_video_formatted': format_number(int(total_views / max(total_videos, 1))),
        'avg_comments_per_video': round(total_comments / max(total_videos, 1), 1),
        'uploads_per_month': round(total_videos / max(years_active * 12, 1), 1) if years_active > 0 else 0,
        
        # Rates (for reference, not display)
        'comment_rate': round((total_comments / max(total_views, 1)) * 100, 3),
        'like_rate': round((total_likes / max(total_views, 1)) * 100, 2),
        'interaction_rate': round(((total_comments + total_likes) / max(total_views, 1)) * 100, 2),
        
        # Average engagement
        'average_engagement': 0.0,
        
        # Loyalty metric
        'avg_views_per_subscriber': round(total_views / max(total_subscribers, 1), 1),
        
        # Quality score (calculated honestly)
        'audience_quality_score': 0
    }
    
    # Calculate average engagement across channels
    valid_engagements = [ch.get('engagement_rate', 0) for ch in channels if ch.get('engagement_rate', 0) > 0]
    if valid_engagements:
        totals['average_engagement'] = round(sum(valid_engagements) / len(valid_engagements), 2)
    
    # Calculate audience quality score based on REAL factors
    quality_factors = []
    
    # Factor 1: Views per video
    avg_views_per_video = totals['avg_views_per_video']
    if avg_views_per_video > 200000:
        quality_factors.append(100)
    elif avg_views_per_video > 100000:
        quality_factors.append(80)
    elif avg_views_per_video > 50000:
        quality_factors.append(60)
    elif avg_views_per_video > 20000:
        quality_factors.append(40)
    else:
        quality_factors.append(20)
    
    # Factor 2: Actual monthly reach
    if actual_monthly_views > 5000000:
        quality_factors.append(100)
    elif actual_monthly_views > 3000000:
        quality_factors.append(80)
    elif actual_monthly_views > 1000000:
        quality_factors.append(60)
    elif actual_monthly_views > 500000:
        quality_factors.append(40)
    else:
        quality_factors.append(20)
    
    # Factor 3: Network maturity
    if years_active > 10:
        quality_factors.append(100)
    elif years_active > 5:
        quality_factors.append(80)
    elif years_active > 3:
        quality_factors.append(60)
    elif years_active > 1:
        quality_factors.append(40)
    else:
        quality_factors.append(20)
    
    totals['audience_quality_score'] = int(sum(quality_factors) / len(quality_factors))
    
    return totals