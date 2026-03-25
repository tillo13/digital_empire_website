#!/usr/bin/env python3
"""
YouTube Competition Data Collector
---------------------------------
A script that collects data about YouTube channels matching specific keywords
and saves it to a CSV file, including their top video information.

Reads YouTube API key from .env file (YT_API_KEY=your_key_here)
"""

import os
import csv
import datetime
import time
import argparse
import json
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import pandas as pd
from googleapiclient.errors import HttpError

def discover_channels(project_dir=None, config=None):
    """Main function to discover and collect data about YouTube channels based on configuration."""
    
    if not config:
        if not project_dir:
            raise ValueError("Either project_dir or config must be provided")
        
        # Load configuration from project directory
        config_path = os.path.join(project_dir, "config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            full_config = json.load(f)
        
        # Check if market_analysis section exists
        if "market_analysis" not in full_config:
            print(f"\n{'='*50}")
            print(f"CREATING DEFAULT CONFIGURATION")
            print(f"{'='*50}")
            
            # Create a default market_analysis config
            default_market_config = {
                "search_keywords": ["example keyword 1", "example keyword 2"],
                "max_channels_per_search": 30,
                "max_videos_per_channel": 5,
                "output_directory": "data",
                "output_filename": "youtube_data.csv"
            }
            
            # Add the market_analysis section to the config
            full_config["market_analysis"] = default_market_config
            
            # Write the updated config back to the file
            with open(config_path, 'w') as f:
                json.dump(full_config, f, indent=2)
            
            print(f"Added 'market_analysis' section to your config.json file at: {config_path}")
            print(f"Please edit the 'search_keywords' in your config file to target your desired audience.")
            print(f"Then run this script again.")
            print(f"{'='*50}")
            return None
            
        config = full_config["market_analysis"]
    
    # Extract configuration
    search_keywords = config.get("search_keywords", [])
    search_max_channels = config.get("max_channels_per_search", 30)
    search_max_videos = config.get("max_videos_per_channel", 5)
    
    # Determine output filename and path
    output_filename = config.get("output_filename", "channels.csv")
    if project_dir:
        output_dir = os.path.join(project_dir, config.get("output_directory", "data"))
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)
    else:
        output_path = output_filename
    
    print(f"\n{'='*50}")
    print(f"YOUTUBE CHANNEL DATA COLLECTOR")
    print(f"{'='*50}")
    print(f"Using keywords: {search_keywords}")
    print(f"Output file: {output_path}")
    print(f"{'='*50}\n")
    
    # Setup environment
    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from tqdm import tqdm
    except ImportError:
        print("Installing required packages...")
        import subprocess
        subprocess.check_call(["pip", "install", "google-api-python-client", "pandas", "tqdm", "python-dotenv"])
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from tqdm import tqdm
        

    # Get the path to the root directory and load .env from there

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Get the parent directory of the script
    load_dotenv(os.path.join(root_dir, '.env'))  # Load .env from the parent directory

    API_KEY = os.getenv('YT_API_KEY')

    if not API_KEY:
        raise Exception("YouTube API key not found. Please create a .env file with YT_API_KEY=your_key_here")

    # Set up YouTube API client
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    
    # Check quota limits first
    if not check_quota_limits(youtube, search_keywords, search_max_channels, search_max_videos):
        return
    
    # Load existing channels to avoid duplicates
    existing_channels, existing_channel_ids = load_existing_channels(output_path)
    print(f"Found {len(existing_channel_ids)} existing channels in the CSV file")
    
    all_channels = []
    all_channel_ids = set(existing_channel_ids)  # Copy to track newly added channels
    
    # Track new channels found during this run
    channels_found_this_run = 0
    
    # Search for channels using keywords
    for keyword in search_keywords:
        search_results = search_channels(youtube, keyword, max_results=search_max_channels)
        
        for item in search_results:
            channel_id = item['id']['channelId']
            
            # Skip if we've already processed this channel
            if channel_id in all_channel_ids:
                print(f"Skipping already processed channel: {item['snippet']['title']}")
                continue
            
            all_channel_ids.add(channel_id)
            channels_found_this_run += 1
            
            # Get detailed channel information
            channel_details = get_channel_details(youtube, channel_id)
            
            if channel_details:
                # Get top video information
                top_video_data = get_channel_top_video(youtube, channel_id, max_videos=search_max_videos)
                
                # Update channel details with top video information
                channel_details.update(top_video_data)
                
                # Print progress to console
                print(f"Channel: {channel_details['title']}")
                print(f"  Subscribers: {int(channel_details['subscriber_count']):,}")
                print(f"  Videos: {int(channel_details['video_count']):,}")
                print(f"  Views: {int(channel_details['view_count']):,}")
                
                if top_video_data:
                    print(f"  Top Video: {channel_details['top_video_title']}")
                    print(f"  Top Video Views: {int(channel_details['top_video_views']):,}")
                    print(f"  Top Video URL: {channel_details['top_video_url']}")
                
                print(f"  URL: {channel_details['url']}")
                print("-----------------------------------------------")
                
                all_channels.append(channel_details)
                
                # Save periodically to avoid losing data if script crashes
                if len(all_channels) % 5 == 0:
                    save_channels_to_csv(all_channels, output_path)
                    all_channels = []  # Clear the list after saving
                
                # Pause briefly to avoid hitting rate limits
                time.sleep(0.5)
    
    # Save any remaining channels
    if all_channels:
        save_channels_to_csv(all_channels, output_path)
    
    print("\nData collection complete!")
    print(f"Channel data saved to: {output_path}")
    print(f"Total channels: {channels_found_this_run} new, {len(existing_channel_ids)} existing")
    
    return output_path

def estimate_quota_usage(search_keywords, max_channels, max_videos):
    """
    Estimate the quota usage for the script.
    """
    # Quota costs
    search_cost = 100   # search.list
    channel_cost = 1    # channels.list
    videos_cost = 1     # videos.list per batch (of up to 50 videos)
    
    # Calculate estimated usage
    estimated_searches = len(search_keywords)
    estimated_channels = max_channels
    estimated_video_lookups = estimated_channels  # One lookup per channel for top videos
    
    total_estimated_cost = (estimated_searches * search_cost) + \
                          (estimated_channels * channel_cost) + \
                          (estimated_video_lookups * videos_cost)
    
    print("\nEstimated Quota Usage:")
    print(f"- Search operations: {estimated_searches} × {search_cost} = {estimated_searches * search_cost} units")
    print(f"- Channel lookups: {estimated_channels} × {channel_cost} = {estimated_channels * channel_cost} units")
    print(f"- Video lookups: {estimated_video_lookups} × {videos_cost} = {estimated_video_lookups * videos_cost} units")
    print(f"- Total estimated usage: {total_estimated_cost} units of 10,000 daily quota\n")
    
    return total_estimated_cost

def check_quota_limits(youtube, search_keywords, max_channels, max_videos):
    """
    Query the API to check if it's working and show quota information.
    """
    try:
        # Make a minimal API call to check if API is working
        request = youtube.channels().list(part="id", id="UC_x5XG1OV2P6uZZ5FSM9Ttw", maxResults=1)
        request.execute()
        
        print("YouTube API connection successful!")
        print("Default quota limit: 10,000 units per day")
        
        # Show the estimated quota usage
        estimate_quota_usage(search_keywords, max_channels, max_videos)
        
        return True
    except HttpError as e:
        print(f"Error checking quota: {e}")
        if "quota" in str(e).lower():
            print("You have exceeded your YouTube API quota. Please try again tomorrow or use a different API key.")
        return False

def load_existing_channels(output_path):
    """
    Load existing channels from the CSV file if it exists.
    Returns a dict of channel_id -> row data.
    """
    if not os.path.exists(output_path):
        return {}, set()
    
    try:
        df = pd.read_csv(output_path)
        
        # Create a dictionary of existing channel data
        existing_channels = {}
        for _, row in df.iterrows():
            channel_id = row['channel_id']
            existing_channels[channel_id] = row.to_dict()
        
        # Also return a set of just the IDs for quick lookup
        return existing_channels, set(existing_channels.keys())
    except Exception as e:
        print(f"Error loading existing channels: {e}")
        return {}, set()

def search_channels(youtube, keyword, max_results=30):
    """Search for channels using a keyword."""
    try:
        print(f"Searching for channels with keyword: '{keyword}'")
        search_response = youtube.search().list(
            q=keyword,
            type="channel",
            part="snippet",
            maxResults=max_results
        ).execute()
        
        channels_found = search_response.get('items', [])
        print(f"Found {len(channels_found)} channels for keyword '{keyword}'")
        return channels_found
    except HttpError as e:
        print(f"Error searching for channels: {e}")
        return []

def get_channel_details(youtube, channel_id):
    """Get detailed information about a specific channel."""
    try:
        channel_response = youtube.channels().list(
            part="snippet,statistics,contentDetails,status,brandingSettings",
            id=channel_id
        ).execute()
        
        if not channel_response.get('items'):
            print(f"No details found for channel ID: {channel_id}")
            return {}
        
        channel_info = channel_response['items'][0]
        snippet = channel_info.get('snippet', {})
        statistics = channel_info.get('statistics', {})
        branding = channel_info.get('brandingSettings', {}).get('channel', {})
        
        # Extract the data we need
        channel_data = {
            'channel_id': channel_id,
            'title': snippet.get('title', ''),
            'description': snippet.get('description', ''),
            'custom_url': snippet.get('customUrl', ''),
            'country': snippet.get('country', ''),
            'view_count': statistics.get('viewCount', 0),
            'subscriber_count': statistics.get('subscriberCount', 0),
            'video_count': statistics.get('videoCount', 0),
            'joined_date': snippet.get('publishedAt', ''),
            'url': f"https://www.youtube.com/channel/{channel_id}",
            'email': branding.get('email', ''),
            'top_video_title': '',
            'top_video_views': 0,
            'top_video_url': ''
        }
        
        return channel_data
    except HttpError as e:
        print(f"Error getting channel details: {e}")
        return {}

def get_channel_top_video(youtube, channel_id, max_videos=5):
    """Get the top (most viewed) video for a channel."""
    try:
        # First, get the upload playlist ID
        channel_response = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        ).execute()
        
        if not channel_response.get('items'):
            return {}
        
        uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        # Get videos from the uploads playlist
        playlist_response = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=max_videos
        ).execute()
        
        videos = playlist_response.get('items', [])
        
        if not videos:
            return {}
        
        # Get video IDs
        video_ids = [video['contentDetails']['videoId'] for video in videos]
        
        # Get detailed video information including view counts
        videos_response = youtube.videos().list(
            part="snippet,statistics",
            id=','.join(video_ids)
        ).execute()
        
        video_items = videos_response.get('items', [])
        
        if not video_items:
            return {}
        
        # Find the video with the most views
        top_video = max(video_items, key=lambda x: int(x.get('statistics', {}).get('viewCount', 0)))
        
        top_video_data = {
            'top_video_title': top_video.get('snippet', {}).get('title', ''),
            'top_video_views': int(top_video.get('statistics', {}).get('viewCount', 0)),
            'top_video_url': f"https://www.youtube.com/watch?v={top_video.get('id', '')}"
        }
        
        return top_video_data
    except HttpError as e:
        print(f"Error getting top video: {e}")
        return {}

def save_channels_to_csv(channels, output_path):
    """Save channel data to CSV file."""
    if not channels:
        print("No channels to save.")
        return
    
    # Check if file exists to determine if we need to write headers
    file_exists = os.path.exists(output_path)
    
    # Convert to DataFrame
    df = pd.DataFrame(channels)
    
    # Ensure numeric columns are handled correctly
    numeric_cols = ['subscriber_count', 'video_count', 'view_count', 'top_video_views']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    
    # Sort by subscriber count (highest first)
    df = df.sort_values(by='subscriber_count', ascending=False)
    
    # Save to CSV
    if file_exists:
        # Append without headers
        df.to_csv(output_path, mode='a', header=False, index=False)
        print(f"Appended {len(channels)} channels to {output_path}")
    else:
        # Create new file with headers
        df.to_csv(output_path, index=False)
        print(f"Created new file {output_path} with {len(channels)} channels")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='YouTube Competition Data Collector')
    parser.add_argument('--project', help='Path to project directory', required=True)
    args = parser.parse_args()
    
    discover_channels(project_dir=args.project)