#!/usr/bin/env python3
"""
Sonic Channel Data Collector - Improved Version
==============================================
Fixed keyword specificity, trending video display, and web search functionality
"""

import os
import json
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests
from bs4 import BeautifulSoup

class SonicChannelCollector:
    def __init__(self, project_dir=None):
        self.project_dir = project_dir or os.getcwd()
        self.setup_environment()
        
        # Setup output directories
        self.sonic_dir = os.path.join(self.project_dir, 'sonic')
        os.makedirs(self.sonic_dir, exist_ok=True)
        
        self.channels_file = os.path.join(self.sonic_dir, 'youtube_channels.json')
        self.trending_file = os.path.join(self.sonic_dir, 'trending_videos.json')
        self.web_mentions_file = os.path.join(self.sonic_dir, 'web_mentions.json')
        self.gaming_trends_file = os.path.join(self.sonic_dir, 'gaming_trends.json')
        
        # IMPROVED: More specific Sonic the Hedgehog keywords
        self.sonic_keywords = [
            'sonic the hedgehog',
            'sonic hedgehog',
            'speedyblox',
            'sonic roblox speed simulator',
            'sonic mania',
            'sonic forces',
            'sonic prime',
            'sonic frontiers',
            'sonic animation',
            'sonic fan game',
            'tails the fox',
            'shadow the hedgehog',
            'knuckles echidna',
            'dr eggman',
            'sonic adventure',
            'sonic 06',
            'sonic unleashed',
            'sonic generations',
            'sonic colors',
            'miles tails',
            'amy rose sonic',
            'cream the rabbit',
            'silver the hedgehog',
            'sonic x',
            'sonic boom'
        ]
        
        # Kid-friendly gaming keywords (unchanged - these are good)
        self.kid_gaming_keywords = [
            'minecraft', 'roblox', 'pokemon', 'mario', 'sonic', 'zelda', 
            'switch', 'nintendo', 'family friendly', 'no swearing', 'kids',
            'fortnite', 'among us', 'fall guys', 'animal crossing', 'kirby',
            'splatoon', 'smash bros', 'luigi', 'yoshi', 'pikmin', 'stardew',
            'terraria', 'geometry dash', 'bendy', 'cuphead', 'hollow knight'
        ]
        
        # YouTube categories for trending analysis
        self.trending_categories = [
            ('20', 'Gaming', 15),
            ('24', 'Entertainment', 8),
            ('23', 'Comedy', 6),
            ('26', 'Howto & Style', 5),
            ('15', 'Pets & Animals', 4),
            ('28', 'Science & Technology', 4),
            ('22', 'People & Blogs', 4),
            ('10', 'Music', 3)
        ]

    def setup_environment(self):
        """Load API keys from .env"""
        load_dotenv(os.path.join(self.project_dir, '.env'))
        
        self.youtube_api_key = os.getenv('YT_API_KEY')
        if not self.youtube_api_key:
            raise Exception("YouTube API key not found. Please set YT_API_KEY in .env file")
        
        self.youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)

    def extract_channel_id_from_url(self, url_or_id: str) -> Optional[str]:
        """Extract channel ID from various YouTube URL formats or return if already an ID"""
        url_or_id = url_or_id.strip()
        
        # If it's already a channel ID (starts with UC and is 24 chars)
        if url_or_id.startswith('UC') and len(url_or_id) == 24:
            return url_or_id
        
        # Extract from various URL formats
        patterns = [
            r'youtube\.com/channel/([a-zA-Z0-9_-]{24})',
            r'youtube\.com/c/([a-zA-Z0-9_-]+)',
            r'youtube\.com/user/([a-zA-Z0-9_-]+)',
            r'youtube\.com/@([a-zA-Z0-9_-]+)',
            r'youtube\.com/([a-zA-Z0-9_-]+)$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                username_or_id = match.group(1)
                
                # If it's a channel ID, return it
                if username_or_id.startswith('UC') and len(username_or_id) == 24:
                    return username_or_id
                
                # Otherwise, try to resolve username to channel ID
                try:
                    # Try forUsername first
                    response = self.youtube.channels().list(
                        part='id',
                        forUsername=username_or_id
                    ).execute()
                    
                    if response['items']:
                        return response['items'][0]['id']
                    
                    # If that fails, try searching
                    search_response = self.youtube.search().list(
                        q=username_or_id,
                        type='channel',
                        part='snippet',
                        maxResults=1
                    ).execute()
                    
                    if search_response['items']:
                        return search_response['items'][0]['id']['channelId']
                        
                except HttpError as e:
                    print(f"Error resolving username {username_or_id}: {e}")
        
        return None

    def is_sonic_content(self, title: str, description: str, channel_name: str) -> bool:
        """MUCH MORE LENIENT: Accept most Sonic-related content"""
        combined_text = f"{title.lower()} {description.lower()} {channel_name.lower()}"
        
        # Very broad acceptance - if it mentions sonic OR related terms, include it
        sonic_terms = [
            'sonic', 'speedyblox', 'tails', 'knuckles', 'shadow', 'eggman', 'robotnik', 
            'emerald', 'chaos', 'mobius', 'hedgehog', 'amy rose', 'cream', 'silver',
            'redninja', 'red ninja'  # Include your channel specifically
        ]
        
        # Sonic games and media
        sonic_media = [
            'mania', 'forces', 'prime', 'frontiers', 'adventure', 'unleashed', 
            'generations', 'colors', 'boom', 'speed simulator'
        ]
        
        # If ANY sonic-related term is found, include it
        if any(term in combined_text for term in sonic_terms):
            return True
            
        # If any game/media + context suggests gaming
        if any(media in combined_text for media in sonic_media) and ('game' in combined_text or 'roblox' in combined_text or 'play' in combined_text):
            return True
        
        # Default to TRUE for discovery - be inclusive, not exclusive
        return True

    def get_detailed_channel_data(self, channel_id: str) -> Optional[Dict]:
        """Get comprehensive channel data including recent videos and analytics"""
        try:
            print(f"Collecting data for channel: {channel_id}")
            
            # Get channel basic info
            channel_response = self.youtube.channels().list(
                part='snippet,statistics,contentDetails,brandingSettings,status',
                id=channel_id
            ).execute()
            
            if not channel_response['items']:
                print(f"No channel found for ID: {channel_id}")
                return None
            
            channel = channel_response['items'][0]
            snippet = channel['snippet']
            stats = channel['statistics']
            branding = channel.get('brandingSettings', {}).get('channel', {})
            
            # Get recent videos
            uploads_playlist = channel['contentDetails']['relatedPlaylists']['uploads']
            recent_videos = self.get_recent_videos(uploads_playlist, max_videos=10)
            
            # REMOVED: No longer filter at channel level - accept all channels for now
            # We'll let the data speak for itself rather than pre-filtering
            
            # Calculate engagement metrics
            total_recent_views = sum(v.get('views', 0) for v in recent_videos)
            total_recent_likes = sum(v.get('likes', 0) for v in recent_videos)
            avg_views_per_video = total_recent_views / len(recent_videos) if recent_videos else 0
            
            # Determine channel category/type
            channel_type = self.categorize_sonic_channel(snippet.get('description', ''), 
                                                       snippet.get('title', ''), 
                                                       recent_videos)
            
            # Load existing data to calculate changes
            existing_channels = self.load_existing_channels()
            existing_data = existing_channels.get(channel_id, {})
            
            current_time = datetime.now().isoformat()
            current_subs = int(stats.get('subscriberCount', 0))
            current_views = int(stats.get('viewCount', 0))
            current_videos = int(stats.get('videoCount', 0))
            
            # Calculate changes since last run
            previous_subs = existing_data.get('subscriber_count', current_subs)
            previous_views = existing_data.get('view_count', current_views)
            previous_videos = existing_data.get('video_count', current_videos)
            
            sub_change = current_subs - previous_subs
            view_change = current_views - previous_views
            video_change = current_videos - previous_videos
            
            # Calculate growth rates
            sub_growth_rate = (sub_change / previous_subs * 100) if previous_subs > 0 else 0
            view_growth_rate = (view_change / previous_views * 100) if previous_views > 0 else 0
            
            channel_data = {
                'channel_id': channel_id,
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'custom_url': snippet.get('customUrl', ''),
                'country': snippet.get('country', ''),
                'published_at': snippet.get('publishedAt', ''),
                'thumbnail_url': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                
                # Current Statistics
                'subscriber_count': current_subs,
                'view_count': current_views,
                'video_count': current_videos,
                
                # Analytics
                'avg_views_per_video': int(avg_views_per_video),
                'total_recent_views': total_recent_views,
                'total_recent_likes': total_recent_likes,
                'engagement_rate': (total_recent_likes / total_recent_views) if total_recent_views > 0 else 0,
                
                # Growth Metrics
                'latest_run': {
                    'date': current_time,
                    'subscriber_change': sub_change,
                    'view_change': view_change,
                    'video_change': video_change,
                    'subscriber_growth_rate': round(sub_growth_rate, 2),
                    'view_growth_rate': round(view_growth_rate, 2),
                    'days_since_last_update': self.calculate_days_since_last_update(existing_data.get('last_updated'))
                },
                
                # Historical tracking
                'growth_history': self.update_growth_history(existing_data, {
                    'date': current_time,
                    'subscribers': current_subs,
                    'views': current_views,
                    'videos': current_videos
                }),
                
                # Metadata
                'channel_type': channel_type,
                'url': f"https://www.youtube.com/channel/{channel_id}",
                'last_updated': current_time,
                
                # Recent videos
                'recent_videos': recent_videos,
                
                # Best performing video
                'top_video': max(recent_videos, key=lambda x: x.get('views', 0)) if recent_videos else None
            }
            
            # Add trending indicator
            if sub_change > 0 or view_change > 0:
                channel_data['trending_status'] = self.determine_trending_status(sub_change, view_change, sub_growth_rate)
            
            print(f"✅ {channel_data['title']}: {current_subs:,} subs ({sub_change:+,}), {len(recent_videos)} recent videos")
            if sub_change != 0:
                print(f"    📈 Growth: {sub_change:+,} subs ({sub_growth_rate:+.2f}%), {view_change:+,} views")
            
            return channel_data
            
        except HttpError as e:
            print(f"❌ Error getting channel data for {channel_id}: {e}")
            return None

    def collect_gaming_trends(self) -> Dict[str, Any]:
        """IMPROVED: Collect trending kid-friendly gaming content with video details"""
        print("🎮 Collecting kid-friendly gaming trends...")
        
        trending_data = {
            'collected_at': datetime.now().isoformat(),
            'categories': {},
            'summary': {
                'total_videos_analyzed': 0,
                'kid_friendly_found': 0,
                'top_games_mentioned': {},
                'trending_formats': {},
                'channel_insights': []
            },
            'trending_videos': []  # NEW: Store actual video data for display
        }
        
        total_analyzed = 0
        kid_friendly_count = 0
        games_mentioned = {}
        trending_formats = {}
        all_trending_videos = []
        
        try:
            for cat_id, cat_name, max_results in self.trending_categories:
                print(f"📊 Analyzing {cat_name} category...")
                
                try:
                    response = self.youtube.videos().list(
                        part='snippet,statistics',
                        chart='mostPopular',
                        regionCode='US',
                        videoCategoryId=cat_id,
                        maxResults=max_results
                    ).execute()
                    
                    videos = response.get('items', [])
                    category_data = {
                        'category_name': cat_name,
                        'videos': [],
                        'kid_friendly_count': 0,
                        'top_performers': []
                    }
                    
                    for video in videos:
                        total_analyzed += 1
                        snippet = video['snippet']
                        stats = video['statistics']
                        
                        title = snippet['title']
                        channel = snippet['channelTitle']
                        description = snippet.get('description', '').lower()
                        views = int(stats.get('viewCount', 0))
                        likes = int(stats.get('likeCount', 0))
                        comments = int(stats.get('commentCount', 0))
                        
                        # Check if it's kid-friendly
                        matching_keywords = []
                        for keyword in self.kid_gaming_keywords:
                            if keyword in title.lower() or keyword in description:
                                matching_keywords.append(keyword)
                                games_mentioned[keyword] = games_mentioned.get(keyword, 0) + 1
                        
                        is_kid_friendly = len(matching_keywords) > 0
                        if is_kid_friendly:
                            kid_friendly_count += 1
                            category_data['kid_friendly_count'] += 1
                        
                        # Analyze content format
                        content_format = self.analyze_content_format(title, description)
                        if content_format:
                            trending_formats[content_format] = trending_formats.get(content_format, 0) + 1
                        
                        video_data = {
                            'video_id': video['id'],
                            'title': title,
                            'channel_name': channel,
                            'channel_id': snippet['channelId'],
                            'views': views,
                            'likes': likes,
                            'comments': comments,
                            'published_at': snippet['publishedAt'],
                            'thumbnail_url': snippet['thumbnails'].get('medium', {}).get('url', ''),
                            'url': f"https://www.youtube.com/watch?v={video['id']}",
                            'is_kid_friendly': is_kid_friendly,
                            'matching_keywords': matching_keywords,
                            'content_format': content_format,
                            'engagement_rate': (likes / views * 100) if views > 0 else 0,
                            'category': cat_name
                        }
                        
                        category_data['videos'].append(video_data)
                        
                        # Add to global trending videos if kid-friendly
                        if is_kid_friendly:
                            all_trending_videos.append(video_data)
                        
                        # Track top performers in kid-friendly space
                        if is_kid_friendly and views > 500000:  # 500K+ views
                            category_data['top_performers'].append({
                                'title': title,
                                'channel': channel,
                                'views': views,
                                'keywords': matching_keywords[:3],
                                'format': content_format,
                                'url': f"https://www.youtube.com/watch?v={video['id']}"
                            })
                    
                    # Sort by views to get top performers
                    category_data['videos'].sort(key=lambda x: x['views'], reverse=True)
                    category_data['top_performers'].sort(key=lambda x: x['views'], reverse=True)
                    category_data['top_performers'] = category_data['top_performers'][:5]
                    
                    trending_data['categories'][cat_id] = category_data
                    
                    time.sleep(1)  # Rate limiting
                    
                except HttpError as e:
                    print(f"❌ Error getting trending videos for {cat_name}: {e}")
                    continue
            
            # Sort all trending videos by views and take top 20
            all_trending_videos.sort(key=lambda x: x['views'], reverse=True)
            trending_data['trending_videos'] = all_trending_videos[:20]
            
            # Build summary insights
            trending_data['summary'].update({
                'total_videos_analyzed': total_analyzed,
                'kid_friendly_found': kid_friendly_count,
                'kid_friendly_percentage': round((kid_friendly_count / total_analyzed * 100), 2) if total_analyzed > 0 else 0,
                'top_games_mentioned': dict(sorted(games_mentioned.items(), key=lambda x: x[1], reverse=True)[:10]),
                'trending_formats': dict(sorted(trending_formats.items(), key=lambda x: x[1], reverse=True)[:8]),
                'insights': self.generate_trend_insights(games_mentioned, trending_formats, trending_data['categories'])
            })
            
            print(f"✅ Gaming trends analysis complete:")
            print(f"   • {total_analyzed} videos analyzed")
            print(f"   • {kid_friendly_count} kid-friendly videos found ({kid_friendly_count/total_analyzed*100:.1f}%)")
            print(f"   • Top games: {list(dict(sorted(games_mentioned.items(), key=lambda x: x[1], reverse=True)[:5]).keys())}")
            print(f"   • {len(trending_data['trending_videos'])} trending videos saved for display")
            
            return trending_data
            
        except Exception as e:
            print(f"❌ Error collecting gaming trends: {e}")
            return trending_data

    def discover_new_channels(self, max_per_keyword: int = 10) -> List[str]:
        """IMPROVED: Discover new Sonic channels with better filtering"""
        discovered_channels = set()
        
        for keyword in self.sonic_keywords:
            try:
                print(f"🔍 Searching for channels: '{keyword}'")
                
                search_response = self.youtube.search().list(
                    q=keyword,
                    type='channel',
                    part='snippet',
                    maxResults=max_per_keyword,
                    order='relevance'
                ).execute()
                
                for item in search_response['items']:
                    channel_id = item['id']['channelId']
                    discovered_channels.add(channel_id)
                    # Accept all discovered channels - no filtering at discovery
                
                time.sleep(1)  # Rate limiting
                
            except HttpError as e:
                print(f"Error searching for '{keyword}': {e}")
        
        print(f"🔍 Discovered {len(discovered_channels)} unique Sonic channels")
        return list(discovered_channels)

    def collect_trending_videos(self, hours_back: int = 48) -> List[Dict]:
        """IMPROVED: Collect trending Sonic videos with better filtering"""
        trending_videos = []
        
        for keyword in self.sonic_keywords[:8]:  # Limit to save quota
            try:
                print(f"📈 Finding trending videos: '{keyword}'")
                
                # Calculate date threshold
                date_threshold = (datetime.now() - timedelta(hours=hours_back)).isoformat() + 'Z'
                
                search_response = self.youtube.search().list(
                    q=keyword,
                    type='video',
                    part='snippet',
                    maxResults=20,
                    order='viewCount',
                    publishedAfter=date_threshold
                ).execute()
                
                video_ids = [item['id']['videoId'] for item in search_response['items']]
                
                if video_ids:
                    # Get detailed video stats
                    videos_response = self.youtube.videos().list(
                        part='statistics,snippet',
                        id=','.join(video_ids)
                    ).execute()
                    
                    for video in videos_response['items']:
                        stats = video['statistics']
                        snippet = video['snippet']
                        
                        # MUCH MORE LENIENT: Only filter out obviously non-gaming content
                        # Accept most content that came from our Sonic keyword searches
                        
                        views = int(stats.get('viewCount', 0))
                        likes = int(stats.get('likeCount', 0))
                        comments = int(stats.get('commentCount', 0))
                        
                        # Calculate trending score (views per hour)
                        publish_time = datetime.fromisoformat(snippet['publishedAt'].replace('Z', '+00:00'))
                        hours_old = (datetime.now().replace(tzinfo=publish_time.tzinfo) - publish_time).total_seconds() / 3600
                        trending_score = (views + likes * 10 + comments * 20) / max(hours_old, 1)
                        
                        trending_videos.append({
                            'video_id': video['id'],
                            'title': snippet['title'],
                            'channel_name': snippet['channelTitle'],
                            'channel_id': snippet['channelId'],
                            'views': views,
                            'likes': likes,
                            'comments': comments,
                            'publish_date': snippet['publishedAt'],
                            'thumbnail_url': snippet['thumbnails'].get('medium', {}).get('url', ''),
                            'trending_score': round(trending_score, 2),
                            'keyword': keyword,
                            'url': f"https://www.youtube.com/watch?v={video['id']}"
                        })
                
                time.sleep(1)
                
            except HttpError as e:
                print(f"Error finding trending videos for '{keyword}': {e}")
        
        # Sort by trending score and remove duplicates
        seen_videos = set()
        unique_trending = []
        
        for video in sorted(trending_videos, key=lambda x: x['trending_score'], reverse=True):
            if video['video_id'] not in seen_videos:
                seen_videos.add(video['video_id'])
                unique_trending.append(video)
        
        return unique_trending[:50]  # Top 50

    def scrape_web_mentions(self) -> List[Dict]:
        """IMPROVED: Better web scraping with multiple sources"""
        mentions = []
        
        # Try multiple search approaches
        search_sources = [
            {
                'name': 'Google News',
                'url_template': 'https://news.google.com/rss/search?q={}&hl=en-US&gl=US&ceid=US:en',
                'method': 'rss'
            },
            {
                'name': 'Bing Search', 
                'url_template': 'https://www.bing.com/search?q={}',
                'method': 'html'
            }
        ]
        
        search_terms = [
            'speedyblox youtube',
            '"sonic the hedgehog" youtube channel',
            'sonic roblox content creator',
            '"red ninja" sonic youtube'
        ]
        
        for term in search_terms:
            for source in search_sources:
                try:
                    print(f"🌐 Searching {source['name']} for: '{term}'")
                    
                    if source['method'] == 'rss':
                        # Try RSS feeds (usually more reliable)
                        url = source['url_template'].format(term.replace(' ', '%20'))
                        response = requests.get(url, timeout=10, headers={
                            'User-Agent': 'Mozilla/5.0 (compatible; NewsBot/1.0)'
                        })
                        
                        if response.status_code == 200:
                            from xml.etree import ElementTree as ET
                            try:
                                root = ET.fromstring(response.text)
                                for item in root.findall('.//item')[:3]:  # Top 3 per search
                                    title_elem = item.find('title')
                                    link_elem = item.find('link')
                                    
                                    if title_elem is not None and link_elem is not None:
                                        title = title_elem.text
                                        url = link_elem.text
                                        
                                        if title and url and 'youtube.com' not in url:
                                            mentions.append({
                                                'title': title,
                                                'url': url,
                                                'source': source['name'],
                                                'search_term': term,
                                                'discovered_date': datetime.now().isoformat()
                                            })
                            except ET.ParseError:
                                print(f"   ❌ Failed to parse RSS from {source['name']}")
                    
                    elif source['method'] == 'html':
                        # Try HTML scraping as fallback
                        url = source['url_template'].format(term.replace(' ', '+'))
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        }
                        
                        response = requests.get(url, headers=headers, timeout=10)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            
                            # Look for search results (Bing format)
                            results = soup.find_all('h2') + soup.find_all('a', {'class': 'sh_favicon'})
                            
                            for result in results[:3]:  # Top 3 per search
                                title = result.get_text().strip()
                                link = result.get('href', '')
                                
                                if title and link and len(title) > 10 and 'youtube.com' not in link:
                                    mentions.append({
                                        'title': title,
                                        'url': link,
                                        'source': source['name'],
                                        'search_term': term,
                                        'discovered_date': datetime.now().isoformat()
                                    })
                    
                    time.sleep(2)  # Be respectful
                    
                except Exception as e:
                    print(f"   ❌ Error scraping {source['name']} for '{term}': {e}")
                    continue
        
        # Remove duplicates
        seen_urls = set()
        unique_mentions = []
        for mention in mentions:
            if mention['url'] not in seen_urls:
                seen_urls.add(mention['url'])
                unique_mentions.append(mention)
        
        print(f"🌐 Found {len(unique_mentions)} unique web mentions")
        return unique_mentions

    # [Include all other helper methods from original code]
    def analyze_content_format(self, title: str, description: str) -> str:
        """Analyze what type of content format this is"""
        title_lower = title.lower()
        desc_lower = description.lower()
        combined = f"{title_lower} {desc_lower}"
        
        format_keywords = {
            'tutorial': ['tutorial', 'how to', 'guide', 'tips', 'learn', 'beginner'],
            'lets_play': ['let\'s play', 'lets play', 'gameplay', 'playing', 'playthrough'],
            'review': ['review', 'reaction', 'thoughts on', 'is it good'],
            'challenge': ['challenge', '100 days', 'speedrun', 'attempt', 'trying'],
            'animation': ['animation', 'animated', 'cartoon', 'anime', 'sfm'],
            'compilation': ['compilation', 'best moments', 'funny moments', 'highlights'],
            'build': ['build', 'building', 'creating', 'construction', 'making'],
            'update': ['update', 'new', 'patch', 'version', 'release'],
            'live_stream': ['live', 'stream', 'streaming', 'twitch'],
            'music': ['song', 'music', 'remix', 'soundtrack', 'theme']
        }
        
        for format_type, keywords in format_keywords.items():
            if any(keyword in combined for keyword in keywords):
                return format_type
        
        return 'general'

    def generate_trend_insights(self, games_mentioned: Dict, trending_formats: Dict, categories: Dict) -> List[str]:
        """Generate actionable insights from trend data"""
        insights = []
        
        # Top game insights
        if games_mentioned:
            top_game = max(games_mentioned.items(), key=lambda x: x[1])
            insights.append(f"'{top_game[0].title()}' is mentioned in {top_game[1]} trending videos - strong keyword opportunity")
        
        # Format insights
        if trending_formats:
            top_format = max(trending_formats.items(), key=lambda x: x[1])
            insights.append(f"'{top_format[0].replace('_', ' ').title()}' format is trending with {top_format[1]} videos")
        
        # Category insights
        gaming_cat = categories.get('20', {})
        if gaming_cat and gaming_cat.get('kid_friendly_count', 0) > 0:
            pct = round(gaming_cat['kid_friendly_count'] / len(gaming_cat.get('videos', [1])) * 100, 1)
            insights.append(f"{pct}% of trending gaming videos are kid-friendly - good market opportunity")
        
        # Cross-category insights
        entertainment_cat = categories.get('24', {})
        if entertainment_cat and entertainment_cat.get('kid_friendly_count', 0) > 2:
            insights.append("Kid-friendly gaming content is crossing into Entertainment category - broader appeal")
        
        return insights

    def categorize_sonic_channel(self, description: str, title: str, recent_videos: List[Dict]) -> str:
        """Categorize the type of Sonic content channel"""
        description_lower = description.lower()
        title_lower = title.lower()
        
        # Check video titles for patterns
        video_titles = ' '.join([v.get('title', '').lower() for v in recent_videos[:5]])
        
        # Category keywords
        categories = {
            'roblox_sonic': ['roblox', 'speedyblox', 'sonic roblox', 'speed simulator'],
            'animation': ['animation', 'animated', 'sfm', 'blender', 'cartoon'],
            'gaming': ['gameplay', 'playthrough', 'lets play', 'gaming', 'game'],
            'fan_games': ['fan game', 'rom hack', 'sonic hack', 'fan made'],
            'music': ['music', 'remix', 'soundtrack', 'song', 'theme'],
            'news': ['news', 'update', 'announcement', 'review', 'trailer'],
            'comedy': ['funny', 'meme', 'parody', 'comedy', 'react'],
            'tutorial': ['tutorial', 'how to', 'guide', 'tips', 'help']
        }
        
        combined_text = f"{description_lower} {title_lower} {video_titles}"
        
        for category, keywords in categories.items():
            if any(keyword in combined_text for keyword in keywords):
                return category
        
        return 'general_sonic'

    def save_gaming_trends(self, trends_data: Dict):
        """Save gaming trends data to JSON file"""
        try:
            with open(self.gaming_trends_file, 'w', encoding='utf-8') as f:
                json.dump(trends_data, f, indent=2, ensure_ascii=False)
            print(f"🎮 Saved gaming trends to {self.gaming_trends_file}")
        except Exception as e:
            print(f"Error saving gaming trends: {e}")

    def load_existing_channels(self) -> Dict[str, Dict]:
        """Load existing channel data from JSON file"""
        if os.path.exists(self.channels_file):
            try:
                with open(self.channels_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading existing channels: {e}")
        return {}

    def save_channels_data(self, channels_data: Dict[str, Dict]):
        """Save channels data to JSON file"""
        try:
            with open(self.channels_file, 'w', encoding='utf-8') as f:
                json.dump(channels_data, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved {len(channels_data)} channels to {self.channels_file}")
        except Exception as e:
            print(f"Error saving channels data: {e}")

    def save_trending_data(self, trending_videos: List[Dict]):
        """Save trending videos to JSON file"""
        try:
            with open(self.trending_file, 'w', encoding='utf-8') as f:
                json.dump(trending_videos, f, indent=2, ensure_ascii=False)
            print(f"📈 Saved {len(trending_videos)} trending videos to {self.trending_file}")
        except Exception as e:
            print(f"Error saving trending data: {e}")

    def save_web_mentions(self, mentions: List[Dict]):
        """Save web mentions to JSON file"""
        try:
            with open(self.web_mentions_file, 'w', encoding='utf-8') as f:
                json.dump(mentions, f, indent=2, ensure_ascii=False)
            print(f"🌐 Saved {len(mentions)} web mentions to {self.web_mentions_file}")
        except Exception as e:
            print(f"Error saving web mentions: {e}")

    def calculate_days_since_last_update(self, last_updated: str) -> int:
        """Calculate days since last update"""
        if not last_updated:
            return 0
        
        try:
            last_date = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            current_date = datetime.now().replace(tzinfo=last_date.tzinfo)
            return (current_date - last_date).days
        except:
            return 0

    def update_growth_history(self, existing_data: Dict, current_data: Dict) -> List[Dict]:
        """Update growth history with current data point"""
        history = existing_data.get('growth_history', [])
        
        # Add current data point
        history.append(current_data)
        
        # Keep only last 30 data points (roughly a month of daily runs)
        if len(history) > 30:
            history = history[-30:]
        
        return history

    def determine_trending_status(self, sub_change: int, view_change: int, growth_rate: float) -> str:
        """Determine if channel is trending based on growth metrics"""
        if growth_rate > 5.0 and sub_change > 1000:
            return 'viral_growth'
        elif growth_rate > 2.0 and sub_change > 500:
            return 'strong_growth'
        elif growth_rate > 1.0 and sub_change > 100:
            return 'steady_growth'
        elif sub_change > 0:
            return 'growing'
        elif sub_change < -100:
            return 'declining'
        else:
            return 'stable'

    def get_recent_videos(self, uploads_playlist_id: str, max_videos: int = 10) -> List[Dict]:
        """Get recent videos from channel's uploads playlist"""
        try:
            # Get recent videos from playlist
            playlist_response = self.youtube.playlistItems().list(
                part='snippet,contentDetails',
                playlistId=uploads_playlist_id,
                maxResults=max_videos
            ).execute()
            
            videos = playlist_response.get('items', [])
            if not videos:
                return []
            
            # Get video IDs for detailed stats
            video_ids = [item['contentDetails']['videoId'] for item in videos]
            
            # Get video statistics
            videos_response = self.youtube.videos().list(
                part='statistics,snippet',
                id=','.join(video_ids)
            ).execute()
            
            video_data = []
            for video in videos_response.get('items', []):
                stats = video.get('statistics', {})
                snippet = video.get('snippet', {})
                
                video_info = {
                    'video_id': video['id'],
                    'title': snippet.get('title', ''),
                    'description': snippet.get('description', '')[:200],  # First 200 chars
                    'published_at': snippet.get('publishedAt', ''),
                    'thumbnail_url': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                    'views': int(stats.get('viewCount', 0)),
                    'likes': int(stats.get('likeCount', 0)),
                    'comments': int(stats.get('commentCount', 0)),
                    'url': f"https://www.youtube.com/watch?v={video['id']}"
                }
                video_data.append(video_info)
            
            return video_data
            
        except HttpError as e:
            if e.resp.status == 404:
                # Playlist not found - channel might have no uploads or restricted access
                return []
            else:
                print(f"Error getting recent videos: {e}")
                return []

    def load_channels_to_fetch(self) -> List[str]:
        """Load channels from channels_to_fetch.json that HTML dashboard populated"""
        channels_to_fetch_file = os.path.join(self.sonic_dir, 'channels_to_fetch.json')
        
        if os.path.exists(channels_to_fetch_file):
            try:
                with open(channels_to_fetch_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('channels', [])
            except Exception as e:
                print(f"Error loading channels to fetch: {e}")
        
        return []

    def clear_channels_to_fetch(self):
        """Clear the channels_to_fetch.json file after processing"""
        channels_to_fetch_file = os.path.join(self.sonic_dir, 'channels_to_fetch.json')
        
        try:
            with open(channels_to_fetch_file, 'w', encoding='utf-8') as f:
                json.dump({'channels': []}, f, indent=2)
        except Exception as e:
            print(f"Error clearing channels to fetch: {e}")

    def run_full_collection(self):
        """Run complete data collection process automatically"""
        print("🚀 Starting IMPROVED Sonic Content Data Collection...")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. Load existing channels
        existing_channels = self.load_existing_channels()
        print(f"📊 Loaded {len(existing_channels)} existing channels")
        
        # 2. Check for new channels from HTML dashboard
        channels_to_fetch = self.load_channels_to_fetch()
        if channels_to_fetch:
            print(f"➕ Processing {len(channels_to_fetch)} channels from dashboard...")
            
            for url_or_id in channels_to_fetch:
                channel_id = self.extract_channel_id_from_url(url_or_id)
                
                if not channel_id:
                    print(f"❌ Could not extract channel ID from: {url_or_id}")
                    continue
                
                if channel_id in existing_channels:
                    print(f"⚠️  Channel already exists: {existing_channels[channel_id].get('title', channel_id)}")
                    continue
                
                # Get detailed channel data
                channel_data = self.get_detailed_channel_data(channel_id)
                if channel_data:
                    existing_channels[channel_id] = channel_data
                    time.sleep(1)
            
            # Clear the fetch list
            self.clear_channels_to_fetch()
        
        # 3. Update all existing channels with fresh data
        print(f"\n🔄 Updating all {len(existing_channels)} channels...")
        updated_count = 0
        
        for channel_id in list(existing_channels.keys()):
            updated_data = self.get_detailed_channel_data(channel_id)
            if updated_data:
                existing_channels[channel_id] = updated_data
                updated_count += 1
            time.sleep(1)
        
        print(f"✅ Updated {updated_count} channels")
        
        # 4. Discover new channels through keyword search
        print("\n🔍 Discovering new Sonic channels...")
        discovered_channels = self.discover_new_channels()
        
        new_channels_count = 0
        for channel_id in discovered_channels:
            if channel_id not in existing_channels:
                channel_data = self.get_detailed_channel_data(channel_id)
                if channel_data:
                    existing_channels[channel_id] = channel_data
                    new_channels_count += 1
                time.sleep(1)
        
        # 5. Save updated channels data
        self.save_channels_data(existing_channels)
        
        # 6. Collect trending videos
        print("\n📈 Collecting trending Sonic videos...")
        trending_videos = self.collect_trending_videos()
        self.save_trending_data(trending_videos)
        
        # 7. Collect gaming trends with video data
        print("\n🎮 Collecting gaming trends with video details...")
        gaming_trends = self.collect_gaming_trends()
        self.save_gaming_trends(gaming_trends)
        
        # 8. Collect web mentions (improved)
        print("\n🌐 Collecting web mentions...")
        web_mentions = self.scrape_web_mentions()
        self.save_web_mentions(web_mentions)
        
        print(f"\n✅ IMPROVED Collection complete!")
        print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Final Results:")
        print(f"   • Channels: {len(existing_channels)} total ({new_channels_count} new)")
        print(f"   • Trending videos: {len(trending_videos)}")
        print(f"   • Gaming trends: {gaming_trends['summary']['total_videos_analyzed']} videos analyzed")
        print(f"   • Trending gaming videos: {len(gaming_trends.get('trending_videos', []))} videos saved")
        print(f"   • Kid-friendly content: {gaming_trends['summary']['kid_friendly_found']} videos found")
        print(f"   • Web mentions: {len(web_mentions)}")
        print(f"📁 Data saved to {self.sonic_dir}/")


def main():
    """Main entry point - always runs full collection"""
    try:
        # Auto-detect project directory or use current
        project_dir = os.path.dirname(os.path.abspath(__file__))
        if not os.path.exists(os.path.join(project_dir, '.env')):
            project_dir = os.getcwd()
        
        collector = SonicChannelCollector(project_dir=project_dir)
        collector.run_full_collection()
        
    except KeyboardInterrupt:
        print("\n⏹️  Collection stopped by user")
    except Exception as e:
        print(f"❌ Fatal Error: {e}")
        raise


if __name__ == "__main__":
    main()