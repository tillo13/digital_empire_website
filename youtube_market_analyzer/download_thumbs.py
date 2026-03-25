#!/usr/bin/env python3
import os, time, re, requests
from dotenv import load_dotenv

CHANNELS = ["https://www.youtube.com/@RealRedNinja", "https://www.youtube.com/@speedybloxx"]

load_dotenv()
API_KEY = os.getenv('YT_API_KEY')
if not API_KEY: raise Exception("YouTube API key not found. Create .env with YT_API_KEY=your_key")

try: from googleapiclient.discovery import build; from googleapiclient.errors import HttpError
except ImportError: import subprocess; subprocess.check_call(["pip", "install", "google-api-python-client", "requests", "python-dotenv"]); from googleapiclient.discovery import build; from googleapiclient.errors import HttpError

def get_channel_id_from_url(url):
    if url.startswith('UC') and len(url) > 20: return url
    try:
        if not url.startswith(('http://', 'https://')):
            url = f"https://www.youtube.com/{url}" if url.startswith('@') else f"https://www.youtube.com/@{url}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200: return None
        html_content = response.text
        
        patterns = [
            r'UC[-_0-9A-Za-z]{21}[AQgw]',
            r'"externalId":\s*"(UC[-_0-9A-Za-z]{21}[AQgw])"',
            r'channelId"?\s*[:=]\s*"(UC[-_0-9A-Za-z]{21}[AQgw])"'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content)
            if matches: return matches[0]
        
        return None
    except Exception: return None

def download_thumbnail(video_id, output_dir, quality="maxres"):
    os.makedirs(output_dir, exist_ok=True)
    quality_options = {"maxres": "maxresdefault.jpg", "hq": "hqdefault.jpg"}
    thumbnail_file = quality_options.get(quality, "maxresdefault.jpg")
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/{thumbnail_file}"
    output_path = os.path.join(output_dir, f"{video_id}.jpg")
    
    if os.path.exists(output_path): return output_path
    
    try:
        response = requests.get(thumbnail_url, timeout=10)
        if response.status_code == 200:
            with open(output_path, 'wb') as f: f.write(response.content)
            print(f"  Downloaded: {video_id}.jpg")
            return output_path
        elif response.status_code == 404 and quality == "maxres":
            return download_thumbnail(video_id, output_dir, "hq")
        return None
    except Exception: return None

def download_all_channel_thumbnails(youtube, channel_url, max_videos=100):
    channel_id = get_channel_id_from_url(channel_url)
    if not channel_id: 
        print(f"Could not determine channel ID for {channel_url}")
        return []
    
    try:
        channel_response = youtube.channels().list(part="snippet", id=channel_id).execute()
        if not channel_response.get('items'):
            folder_name = channel_id
        else:
            channel_title = channel_response['items'][0]['snippet']['title']
            folder_name = channel_title.replace('/', '_').replace('\\', '_')
            print(f"Channel: {channel_title} (ID: {channel_id})")
    except Exception:
        folder_name = channel_id.replace('UC', '')
    
    output_dir = os.path.join("thumbnails", folder_name)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        channel_content = youtube.channels().list(part="contentDetails", id=channel_id).execute()
        if not channel_content.get('items'): return []
        uploads_playlist_id = channel_content['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        next_page_token = None
        video_ids = []
        total_videos_processed = 0
        
        while total_videos_processed < max_videos:
            playlist_response = youtube.playlistItems().list(
                part="contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=min(50, max_videos - total_videos_processed),
                pageToken=next_page_token
            ).execute()
            
            batch_videos = playlist_response.get('items', [])
            if not batch_videos: break
            
            batch_video_ids = [video['contentDetails']['videoId'] for video in batch_videos]
            video_ids.extend(batch_video_ids)
            total_videos_processed += len(batch_videos)
            next_page_token = playlist_response.get('nextPageToken')
            if not next_page_token: break
        
        print(f"Found {len(video_ids)} videos")
        
        thumbnail_paths = []
        for video_id in video_ids:
            path = download_thumbnail(video_id, output_dir, "maxres")
            if path: thumbnail_paths.append(path)
            time.sleep(0.1)
        
        print(f"Downloaded {len(thumbnail_paths)} thumbnails")
        return thumbnail_paths
    except Exception: return []

def main():
    start_time = time.time()
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    
    for channel_url in CHANNELS:
        print(f"Processing: {channel_url}")
        download_all_channel_thumbnails(youtube, channel_url)
    
    elapsed_time = time.time() - start_time
    print(f"Execution time: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()