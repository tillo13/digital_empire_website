"""
Video operations for the Red Ninja YouTube channel.

Handles: listing videos, fetching details, detecting deleted videos,
updating metadata (titles, descriptions, tags).
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from googleapiclient.errors import HttpError

logger = logging.getLogger('redninja.videos')

CHANNEL_ID = 'UCw9GzPJlEJCJeqqB3NwQbJQ'
_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_CACHE_PATH = os.path.join(_DIR, 'video_cache.json')


def _format_number(num: int) -> str:
    """Format large numbers with K/M/B suffixes."""
    num = int(num)
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def _format_duration(duration: str) -> str:
    """Convert YouTube duration (PT10M30S) to readable format (10:30)."""
    duration = duration.replace('PT', '')
    hours = minutes = seconds = 0

    if 'H' in duration:
        hours, duration = int(duration.split('H')[0]), duration.split('H')[1]
    if 'M' in duration:
        minutes, duration = int(duration.split('M')[0]), duration.split('M')[1]
    if 'S' in duration:
        seconds = int(duration.split('S')[0])

    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


class VideoManager:
    """Manages video operations for the Red Ninja channel."""

    def __init__(self, youtube_service):
        self.youtube = youtube_service
        self.channel_id = CHANNEL_ID

    def get_channel_info(self) -> Dict[str, Any]:
        """Get channel stats: subs, views, video count, description."""
        resp = self.youtube.channels().list(
            part="snippet,statistics,contentDetails,brandingSettings",
            id=self.channel_id
        ).execute()

        if not resp.get('items'):
            raise ValueError(f"Channel {self.channel_id} not found")

        ch = resp['items'][0]
        stats = ch['statistics']
        snippet = ch['snippet']

        return {
            'channel_id': self.channel_id,
            'title': snippet['title'],
            'description': snippet.get('description', ''),
            'custom_url': snippet.get('customUrl', ''),
            'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
            'country': snippet.get('country', ''),
            'published_at': snippet.get('publishedAt', ''),
            'subscriber_count': int(stats.get('subscriberCount', 0)),
            'view_count': int(stats.get('viewCount', 0)),
            'video_count': int(stats.get('videoCount', 0)),
            'uploads_playlist': ch['contentDetails']['relatedPlaylists']['uploads'],
        }

    def _get_uploads_playlist_id(self) -> str:
        """Get the uploads playlist ID for the channel."""
        resp = self.youtube.channels().list(
            part="contentDetails", id=self.channel_id
        ).execute()
        return resp['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    def _get_all_playlist_items(self) -> List[Dict]:
        """Get all items from the uploads playlist with full snippet data."""
        playlist_id = self._get_uploads_playlist_id()
        items = []
        page_token = None

        while True:
            resp = self.youtube.playlistItems().list(
                part="contentDetails,snippet",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=page_token
            ).execute()

            items.extend(resp.get('items', []))
            page_token = resp.get('nextPageToken')
            if not page_token:
                break

        return items

    def get_all_video_ids(self) -> List[str]:
        """Get all video IDs from the uploads playlist."""
        items = self._get_all_playlist_items()
        return [item['contentDetails']['videoId'] for item in items]

    def get_video_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """Get detailed info for videos, in batches of 50."""
        all_videos = []

        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]
            try:
                resp = self.youtube.videos().list(
                    part="snippet,statistics,contentDetails,status",
                    id=','.join(batch)
                ).execute()
                all_videos.extend(resp.get('items', []))
            except HttpError as e:
                logger.error(f"Error fetching video batch: {e}")

        return all_videos

    def get_all_videos_summary(self) -> List[Dict[str, Any]]:
        """Get a flat summary of all videos with key metrics."""
        video_ids = self.get_all_video_ids()
        logger.info(f"Fetching details for {len(video_ids)} videos...")
        raw_videos = self.get_video_details(video_ids)

        summaries = []
        for v in raw_videos:
            stats = v.get('statistics', {})
            snippet = v['snippet']
            status = v.get('status', {})

            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            comments = int(stats.get('commentCount', 0))

            summaries.append({
                'video_id': v['id'],
                'title': snippet['title'],
                'published_at': snippet['publishedAt'],
                'description': snippet.get('description', '')[:200],
                'duration': _format_duration(v['contentDetails']['duration']),
                'views': views,
                'views_formatted': _format_number(views),
                'likes': likes,
                'likes_formatted': _format_number(likes),
                'comments': comments,
                'comments_formatted': _format_number(comments),
                'engagement_rate': round(((likes + comments) / max(views, 1)) * 100, 2),
                'privacy': status.get('privacyStatus', 'unknown'),
                'url': f"https://www.youtube.com/watch?v={v['id']}",
            })

        summaries.sort(key=lambda x: x['views'], reverse=True)
        return summaries

    def find_deleted_videos(self) -> Dict[str, Any]:
        """Detect deleted/removed videos.

        Compares playlist entries against videos().list() responses.
        Also checks against a local video_cache.json for historical tracking.

        Returns dict with 'deleted' list and 'cache_stats'.
        """
        # Get all playlist items
        playlist_items = self._get_all_playlist_items()
        playlist_map = {}
        for item in playlist_items:
            vid_id = item['contentDetails']['videoId']
            playlist_map[vid_id] = {
                'title': item['snippet'].get('title', 'Unknown'),
                'published_at': item['snippet'].get('publishedAt', ''),
            }

        logger.info(f"Found {len(playlist_map)} videos in uploads playlist")

        # Query videos API in batches — missing ones are deleted
        existing_ids = set()
        all_ids = list(playlist_map.keys())
        for i in range(0, len(all_ids), 50):
            batch = all_ids[i:i + 50]
            try:
                resp = self.youtube.videos().list(
                    part="id,snippet", id=','.join(batch)
                ).execute()
                for item in resp.get('items', []):
                    existing_ids.add(item['id'])
            except HttpError as e:
                logger.error(f"Error checking video batch: {e}")

        # Deleted = in playlist but not returned by videos API
        deleted_from_playlist = []
        for vid_id, info in playlist_map.items():
            if vid_id not in existing_ids:
                deleted_from_playlist.append({
                    'video_id': vid_id,
                    'title': info['title'],
                    'published_at': info['published_at'],
                    'url': f"https://www.youtube.com/watch?v={vid_id}",
                    'detected_via': 'playlist_check',
                })

        # Check against local cache for older deletions
        deleted_from_cache = []
        cache = self._load_video_cache()
        if cache:
            cached_ids = set(cache.keys())
            still_in_playlist = set(playlist_map.keys())
            # Videos in cache but gone from playlist entirely
            gone_from_playlist = cached_ids - still_in_playlist
            for vid_id in gone_from_playlist:
                if vid_id not in existing_ids:
                    deleted_from_cache.append({
                        'video_id': vid_id,
                        'title': cache[vid_id].get('title', 'Unknown'),
                        'published_at': cache[vid_id].get('published_at', ''),
                        'url': f"https://www.youtube.com/watch?v={vid_id}",
                        'detected_via': 'cache_check',
                    })

        # Update cache with current playlist data
        self._save_video_cache(playlist_map, existing_ids)

        all_deleted = deleted_from_playlist + deleted_from_cache
        return {
            'deleted': all_deleted,
            'total_deleted': len(all_deleted),
            'playlist_count': len(playlist_map),
            'existing_count': len(existing_ids),
            'cache_count': len(cache) if cache else 0,
            'checked_at': datetime.now().isoformat(),
        }

    def _load_video_cache(self) -> Dict:
        """Load the local video ID cache."""
        if os.path.exists(VIDEO_CACHE_PATH):
            try:
                with open(VIDEO_CACHE_PATH, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_video_cache(self, playlist_map: Dict, existing_ids: set):
        """Update the local video cache with current data."""
        cache = self._load_video_cache()

        # Add/update all known videos
        for vid_id, info in playlist_map.items():
            if vid_id not in cache:
                cache[vid_id] = {
                    'title': info['title'],
                    'published_at': info['published_at'],
                    'first_seen': datetime.now().isoformat(),
                }
            # Mark deleted ones
            if vid_id not in existing_ids:
                cache[vid_id]['deleted'] = True
                cache[vid_id]['deleted_at'] = cache[vid_id].get(
                    'deleted_at', datetime.now().isoformat()
                )

        with open(VIDEO_CACHE_PATH, 'w') as f:
            json.dump(cache, f, indent=2)
        logger.info(f"Video cache updated: {len(cache)} total entries")

    def update_video(self, video_id: str, title: str = None,
                     description: str = None, tags: List[str] = None,
                     category_id: str = None) -> Dict[str, Any]:
        """Update video metadata. Only changes fields you pass in.

        Fetches current snippet first, merges your changes, then updates.
        """
        # Get current video data
        resp = self.youtube.videos().list(
            part="snippet", id=video_id
        ).execute()

        if not resp.get('items'):
            raise ValueError(f"Video {video_id} not found")

        snippet = resp['items'][0]['snippet']

        if title is not None:
            snippet['title'] = title
        if description is not None:
            snippet['description'] = description
        if tags is not None:
            snippet['tags'] = tags
        if category_id is not None:
            snippet['categoryId'] = category_id

        result = self.youtube.videos().update(
            part="snippet",
            body={'id': video_id, 'snippet': snippet}
        ).execute()

        logger.info(f"Updated video {video_id}: {result['snippet']['title']}")
        return result

    def get_video_status(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Check if a specific video exists and get its status."""
        resp = self.youtube.videos().list(
            part="snippet,status,statistics", id=video_id
        ).execute()

        if not resp.get('items'):
            return {'video_id': video_id, 'exists': False, 'status': 'deleted_or_private'}

        item = resp['items'][0]
        return {
            'video_id': video_id,
            'exists': True,
            'title': item['snippet']['title'],
            'privacy': item['status']['privacyStatus'],
            'views': int(item['statistics'].get('viewCount', 0)),
            'upload_status': item['status'].get('uploadStatus', ''),
        }
