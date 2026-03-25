"""
RedNinjaYT — single entry point for Red Ninja channel management.

Usage:
    from digital_empire_tv.redninja import RedNinjaYT

    rn = RedNinjaYT()
    rn.studio_dashboard(days=28)
    rn.videos.find_deleted_videos()
    rn.videos.update_video('abc', description='new desc')
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from .auth import get_credentials, get_youtube_service, get_analytics_service
from .videos import VideoManager
from .analytics import ChannelAnalytics

logger = logging.getLogger('redninja')


class RedNinjaYT:
    """Full programmatic access to the Red Ninja YouTube channel."""

    def __init__(self):
        creds = get_credentials()
        self._youtube = get_youtube_service(creds)
        self._analytics_svc = get_analytics_service(creds)

        self.videos = VideoManager(self._youtube)
        self.analytics = ChannelAnalytics(self._analytics_svc, self._youtube)

    def channel_info(self) -> Dict[str, Any]:
        """Quick channel summary."""
        return self.videos.get_channel_info()

    def studio_dashboard(self, days: int = 28) -> Dict[str, Any]:
        """Mimic the YouTube Studio dashboard for the last N days.

        Returns:
            dict with: period, overview, top_videos, traffic_sources,
                       demographics, geography
        """
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        return {
            'period': f'{start} to {end}',
            'days': days,
            'overview': self.analytics.get_overview(start, end),
            'impressions': self.analytics.get_impressions(start, end),
            'top_videos': self.analytics.get_top_videos(start, end),
            'traffic_sources': self.analytics.get_traffic_sources(start, end),
            'demographics': self.analytics.get_demographics(start, end),
            'geography': self.analytics.get_geography(start, end),
        }

    def check_video(self, video_id: str) -> Dict[str, Any]:
        """Quick check if a video exists and its status."""
        return self.videos.get_video_status(video_id)
