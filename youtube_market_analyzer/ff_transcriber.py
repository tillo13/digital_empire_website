#!/usr/bin/env python3
"""
Fast Friends Transcript Downloader
Downloads all video transcripts from the Fast Friends YouTube channel.
"""

import os
import time
import random
from dotenv import load_dotenv
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi

# Load .env file
load_dotenv()

# === CONFIG ===
CHANNEL_ID = "UCdZ8WmPJK-wN22wTSUIU-Ag"  # Fast Friends (Sonic & Shadow) - 80 videos
OUTPUT_DIR = "fastfriends_videos"
API_KEY = os.getenv("YT_API_KEY")
DELAY_MIN = 2  # Min seconds between requests
DELAY_MAX = 5  # Max seconds between requests

def get_all_video_ids(youtube, channel_id):
    """Get all video IDs from a channel."""
    video_ids = []
    
    # Get uploads playlist ID
    res = youtube.channels().list(id=channel_id, part="contentDetails").execute()
    
    if not res.get("items"):
        print(f"❌ No channel found for ID: {channel_id}")
        return []
    
    uploads_id = res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    print(f"📂 Uploads playlist: {uploads_id}")
    
    # Paginate through all videos
    next_page = None
    page = 1
    while True:
        pl_res = youtube.playlistItems().list(
            playlistId=uploads_id,
            part="contentDetails,snippet",
            maxResults=50,
            pageToken=next_page
        ).execute()
        
        for item in pl_res["items"]:
            vid_id = item["contentDetails"]["videoId"]
            title = item["snippet"]["title"]
            video_ids.append((vid_id, title))
        
        print(f"  Page {page}: found {len(pl_res['items'])} videos")
        
        next_page = pl_res.get("nextPageToken")
        if not next_page:
            break
        page += 1
    
    return video_ids

def get_transcript(video_id):
    """Get transcript for a video, returns None if unavailable."""
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)
        return " ".join([t.text for t in transcript])
    except Exception as e:
        error_msg = str(e)
        if "blocking" in error_msg.lower() or "IP" in error_msg:
            print(f"  🚫 IP BLOCKED - waiting 60s cooldown...")
            time.sleep(60)
            return "IP_BLOCKED"  # Signal to retry
        print(f"  ⚠️  No transcript: {error_msg[:80]}")
        return None

def main():
    if not API_KEY:
        print("❌ Set YOUTUBE_API_KEY environment variable")
        print("   export YOUTUBE_API_KEY='your-key-here'")
        return
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    youtube = build("youtube", "v3", developerKey=API_KEY)
    
    print(f"📺 Fetching videos from Fast Friends ({CHANNEL_ID})...")
    videos = get_all_video_ids(youtube, CHANNEL_ID)
    print(f"✅ Found {len(videos)} videos\n")
    
    saved = 0
    skipped = 0
    no_transcript = 0
    
    for i, (vid, title) in enumerate(videos, 1):
        out_path = os.path.join(OUTPUT_DIR, f"transcript_{vid}.txt")
        
        if os.path.exists(out_path):
            print(f"[{i}/{len(videos)}] {vid} - already exists, skipping")
            skipped += 1
            continue
        
        print(f"[{i}/{len(videos)}] {title[:50]}... ({vid})")
        transcript = get_transcript(vid)
        
        # Retry once if IP was blocked
        if transcript == "IP_BLOCKED":
            print(f"  🔄 Retrying after cooldown...")
            transcript = get_transcript(vid)
        
        if transcript and transcript != "IP_BLOCKED":
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n{transcript}")
            print(f"  ✅ Saved: {out_path}")
            saved += 1
        else:
            no_transcript += 1
        
        # Random delay to avoid IP blocking
        if i < len(videos):
            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            print(f"  ⏱️  Waiting {delay:.1f}s...")
            time.sleep(delay)
    
    print(f"\n🎉 Done! Saved: {saved}, Skipped: {skipped}, No transcript: {no_transcript}")

if __name__ == "__main__":
    main()