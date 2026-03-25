"""
OAuth2 authentication for Red Ninja YouTube channel management.

Scopes:
  - youtube              : read + write channel data
  - youtube.force-ssl    : required for video.update()
  - yt-analytics.readonly: YouTube Analytics API (Studio-level metrics)

First run opens a browser for OAuth consent. Token is cached locally.
"""

import os
import pickle
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger('redninja.auth')

SCOPES = [
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/yt-analytics.readonly',
]

# Paths
_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(_DIR, 'token_redninja.pickle')
OAUTH_CREDS_PATH = os.path.join(_DIR, '..', '..', 'credentials', 'oauth_credentials.json')


def get_credentials() -> Credentials:
    """Get OAuth credentials with auto-refresh. Opens browser on first run."""
    creds = None

    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired token...")
            creds.refresh(Request())
        else:
            creds_path = os.path.normpath(OAUTH_CREDS_PATH)
            if not os.path.exists(creds_path):
                raise FileNotFoundError(
                    f"OAuth credentials not found at {creds_path}\n"
                    "Expected: credentials/oauth_credentials.json"
                )
            logger.info("No valid token found. Opening browser for OAuth consent...")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, 'wb') as f:
            pickle.dump(creds, f)
        logger.info(f"Token saved to {TOKEN_PATH}")

    return creds


def get_youtube_service(creds: Credentials = None):
    """Build authenticated YouTube Data API v3 service."""
    if not creds:
        creds = get_credentials()
    return build('youtube', 'v3', credentials=creds)


def get_analytics_service(creds: Credentials = None):
    """Build authenticated YouTube Analytics API v2 service."""
    if not creds:
        creds = get_credentials()
    return build('youtubeAnalytics', 'v2', credentials=creds)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("Authenticating...")
    creds = get_credentials()
    yt = get_youtube_service(creds)
    # Quick test: fetch our channel
    resp = yt.channels().list(part="snippet", id="UCw9GzPJlEJCJeqqB3NwQbJQ").execute()
    if resp.get('items'):
        print(f"Authenticated. Channel: {resp['items'][0]['snippet']['title']}")
    else:
        print("Auth succeeded but channel not found. Check channel ID.")
