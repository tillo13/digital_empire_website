"""
YouTube Analytics API v2 wrapper for the Red Ninja channel.

Provides programmatic access to everything in YouTube Studio's analytics:
views, watch time, impressions, CTR, traffic sources, demographics, geography.

Requires the yt-analytics.readonly OAuth scope (handled by auth.py).
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger('redninja.analytics')

CHANNEL_ID = 'UCw9GzPJlEJCJeqqB3NwQbJQ'


class ChannelAnalytics:
    """YouTube Studio-level analytics for the Red Ninja channel."""

    def __init__(self, analytics_service, youtube_service=None):
        self.analytics = analytics_service
        self.youtube = youtube_service
        self.channel_id = CHANNEL_ID

    def get_overview(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Channel overview — the main YouTube Studio dashboard.

        Args:
            start_date: YYYY-MM-DD format
            end_date: YYYY-MM-DD format

        Returns dict with: views, estimatedMinutesWatched, averageViewDuration,
            subscribersGained, subscribersLost, likes, shares, comments,
            impressions, impressionClickThroughRate
        """
        response = self.analytics.reports().query(
            ids=f'channel=={self.channel_id}',
            startDate=start_date,
            endDate=end_date,
            metrics=','.join([
                'views', 'estimatedMinutesWatched', 'averageViewDuration',
                'subscribersGained', 'subscribersLost',
                'likes', 'dislikes', 'shares', 'comments',
            ]),
        ).execute()
        return self._parse_report(response)

    def get_impressions(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Impressions and CTR — the "Reach" tab in YouTube Studio."""
        response = self.analytics.reports().query(
            ids=f'channel=={self.channel_id}',
            startDate=start_date,
            endDate=end_date,
            metrics='views,impressions,impressionClickThroughRate',
        ).execute()
        return self._parse_report(response)

    def get_daily_views(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Day-by-day breakdown of views, watch time, and subscriber changes."""
        response = self.analytics.reports().query(
            ids=f'channel=={self.channel_id}',
            startDate=start_date,
            endDate=end_date,
            dimensions='day',
            metrics='views,estimatedMinutesWatched,subscribersGained,subscribersLost',
            sort='day',
        ).execute()
        return self._parse_rows(response)

    def get_traffic_sources(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Traffic sources — how viewers find the videos.

        Source types: ADVERTISING, ANNOTATION, CAMPAIGN_CARD, END_SCREEN,
        EXT_URL, HASHTAGS, NOTIFICATION, PLAYLIST, PROMOTED, RELATED_VIDEO,
        SHORTS, SUBSCRIBER, YT_CHANNEL, YT_OTHER_PAGE, YT_SEARCH, etc.
        """
        response = self.analytics.reports().query(
            ids=f'channel=={self.channel_id}',
            startDate=start_date,
            endDate=end_date,
            dimensions='insightTrafficSourceType',
            metrics='views,estimatedMinutesWatched',
            sort='-views',
        ).execute()
        return self._parse_rows(response)

    def get_demographics(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Audience demographics — age group and gender breakdown."""
        response = self.analytics.reports().query(
            ids=f'channel=={self.channel_id}',
            startDate=start_date,
            endDate=end_date,
            dimensions='ageGroup,gender',
            metrics='viewerPercentage',
        ).execute()
        return self._parse_rows(response)

    def get_geography(self, start_date: str, end_date: str,
                      max_results: int = 25) -> List[Dict[str, Any]]:
        """Top countries by views."""
        response = self.analytics.reports().query(
            ids=f'channel=={self.channel_id}',
            startDate=start_date,
            endDate=end_date,
            dimensions='country',
            metrics='views,estimatedMinutesWatched',
            sort='-views',
            maxResults=max_results,
        ).execute()
        return self._parse_rows(response)

    def get_top_videos(self, start_date: str, end_date: str,
                       max_results: int = 20) -> List[Dict[str, Any]]:
        """Top videos by views in date range — like the Studio "Content" tab.

        Returns video IDs with views, watch time, avg duration, likes, subs gained.
        """
        response = self.analytics.reports().query(
            ids=f'channel=={self.channel_id}',
            startDate=start_date,
            endDate=end_date,
            dimensions='video',
            metrics='views,estimatedMinutesWatched,averageViewDuration,likes,subscribersGained',
            sort='-views',
            maxResults=max_results,
        ).execute()

        rows = self._parse_rows(response)

        # Enrich with video titles if youtube service is available
        if self.youtube and rows:
            video_ids = [r['video'] for r in rows]
            titles = self._get_video_titles(video_ids)
            for row in rows:
                row['title'] = titles.get(row['video'], row['video'])
                row['url'] = f"https://www.youtube.com/watch?v={row['video']}"

        return rows

    def get_video_analytics(self, video_id: str,
                            start_date: str, end_date: str) -> Dict[str, Any]:
        """Detailed analytics for a specific video."""
        response = self.analytics.reports().query(
            ids=f'channel=={self.channel_id}',
            startDate=start_date,
            endDate=end_date,
            filters=f'video=={video_id}',
            metrics=','.join([
                'views', 'estimatedMinutesWatched', 'averageViewDuration',
                'likes', 'dislikes', 'shares', 'comments',
                'subscribersGained', 'subscribersLost',
            ]),
        ).execute()
        result = self._parse_report(response)
        result['video_id'] = video_id

        # Get title if possible
        if self.youtube:
            titles = self._get_video_titles([video_id])
            result['title'] = titles.get(video_id, video_id)

        return result

    def get_video_daily(self, video_id: str,
                        start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Daily breakdown for a specific video."""
        response = self.analytics.reports().query(
            ids=f'channel=={self.channel_id}',
            startDate=start_date,
            endDate=end_date,
            filters=f'video=={video_id}',
            dimensions='day',
            metrics='views,estimatedMinutesWatched,likes,subscribersGained',
            sort='day',
        ).execute()
        return self._parse_rows(response)

    def get_video_traffic_sources(self, video_id: str,
                                  start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Traffic sources for a specific video."""
        response = self.analytics.reports().query(
            ids=f'channel=={self.channel_id}',
            startDate=start_date,
            endDate=end_date,
            filters=f'video=={video_id}',
            dimensions='insightTrafficSourceType',
            metrics='views,estimatedMinutesWatched',
            sort='-views',
        ).execute()
        return self._parse_rows(response)

    def _get_video_titles(self, video_ids: List[str]) -> Dict[str, str]:
        """Fetch video titles from the Data API."""
        titles = {}
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]
            try:
                resp = self.youtube.videos().list(
                    part="snippet", id=','.join(batch)
                ).execute()
                for item in resp.get('items', []):
                    titles[item['id']] = item['snippet']['title']
            except Exception as e:
                logger.warning(f"Could not fetch titles: {e}")
        return titles

    def _parse_report(self, response: dict) -> Dict[str, Any]:
        """Convert single-row Analytics response to a clean dict."""
        headers = [col['name'] for col in response.get('columnHeaders', [])]
        rows = response.get('rows', [])
        if rows:
            return dict(zip(headers, rows[0]))
        return {h: 0 for h in headers}

    def _parse_rows(self, response: dict) -> List[Dict[str, Any]]:
        """Convert multi-row Analytics response to list of dicts."""
        headers = [col['name'] for col in response.get('columnHeaders', [])]
        return [dict(zip(headers, row)) for row in response.get('rows', [])]
