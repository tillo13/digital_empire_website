#!/usr/bin/env python3
"""
Fast Friends Content Checker
Analyzes video transcripts for potentially flaggable content before YPP reapplication.

Usage:
1. Copy claude_utils.py to this directory
2. Run fastfriends_transcripts.py first to download transcripts
3. Run this script to analyze them

Set ANTHROPIC_API_KEY and YT_API_KEY in environment or .env file
"""

import os
import csv
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from googleapiclient.discovery import build

# Import from your existing claude_utils
from claude_utils import create_client

load_dotenv()

# === CONFIG ===
TRANSCRIPT_DIR = "fastfriends_videos"
OUTPUT_CSV = "fastfriends_content_review.csv"
YT_API_KEY = os.getenv("YT_API_KEY")

# Content categories YouTube flags for "harmful content involving minors"
ANALYSIS_PROMPT = """You are a YouTube content policy expert helping a Sonic/Shadow reaction channel prepare for YPP reapplication after a 90-day demonetization for "Harmful content involving minors."

VIDEO TITLE: {title}

VIDEO TRANSCRIPT:
{transcript}

IMPORTANT CONTEXT:
- Sonic.EXE and creepypasta REFERENCES alone are NOT a problem - many monetized channels discuss these
- Normal cartoon action/fighting is fine
- The issue is specifically HARMFUL CONTENT in the actual dialogue/reactions

Only flag content if the transcript contains:
1. **Graphic violence descriptions** - detailed gore, blood, death beyond cartoon level
2. **Gross-out content** - vomiting, bodily functions, bathroom humor in detail
3. **Sexual/suggestive content** - inappropriate for children
4. **Self-harm or suicide references** - even joking
5. **Extreme fear content targeting kids** - jump scare descriptions aimed at scaring child viewers
6. **Baby/child characters in disturbing scenarios** - Baby Sonic combined with truly inappropriate content

DO NOT flag for:
- Simply mentioning Sonic.EXE or creepypasta characters
- Normal video game violence (fighting Eggman, etc.)
- Spooky/Halloween themes without graphic content
- Characters being scared in a cartoon way

Respond with this JSON format ONLY:
{{
    "has_real_issues": true/false,
    "detailed_assessment": "2-4 sentences explaining what's actually in this video. Be specific about whether content is genuinely problematic or just spooky-themed but fine.",
    "poor_phrases": ["exact quote 1 that's problematic", "exact quote 2", ...] or [] if none found,
    "action_required": "REMOVE - [specific reason]" OR "EDIT - [specific part to remove]" OR "KEEP - [why it's actually fine]",
    "risk_score": 1-10 (10 = definitely will get flagged, 1 = totally safe, 5 = uncertain)
}}

Be FAIR - most Sonic content is fine. Only high scores for genuinely problematic dialogue."""

def load_transcripts(transcript_dir):
    """Load all transcripts from directory."""
    transcripts = {}
    transcript_path = Path(transcript_dir)
    
    if not transcript_path.exists():
        print(f"❌ Transcript directory not found: {transcript_dir}")
        print("   Run fastfriends_transcripts.py first!")
        return {}
    
    for file in transcript_path.glob("transcript_*.txt"):
        # Handle both old format (transcript_ID.txt) and new format (transcript_ID_title.txt)
        filename = file.stem
        parts = filename.replace("transcript_", "").split("_", 1)
        video_id = parts[0]
        
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            # Extract title from first line if present
            lines = content.split("\n", 2)
            title = lines[0].replace("# ", "") if lines[0].startswith("# ") else "Unknown"
            transcript_text = "\n".join(lines[2:]) if len(lines) > 2 else content
            
            transcripts[video_id] = {
                "title": title,
                "transcript": transcript_text,
                "file": str(file)
            }
    
    return transcripts

def get_video_stats(youtube, video_ids):
    """Fetch view counts for a list of video IDs."""
    stats = {}
    
    # YouTube API allows up to 50 IDs per request
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        try:
            response = youtube.videos().list(
                part="statistics",
                id=",".join(batch)
            ).execute()
            
            for item in response.get("items", []):
                vid_id = item["id"]
                view_count = int(item["statistics"].get("viewCount", 0))
                stats[vid_id] = view_count
        except Exception as e:
            print(f"  ⚠️  Error fetching stats: {e}")
    
    return stats

def analyze_transcript(client, video_id, video_data):
    """Analyze a single transcript for problematic content."""
    transcript = video_data["transcript"]
    title = video_data["title"]
    
    # Truncate very long transcripts (keep first 8000 chars for analysis)
    if len(transcript) > 8000:
        transcript = transcript[:8000] + "\n\n[TRANSCRIPT TRUNCATED FOR ANALYSIS]"
    
    prompt = ANALYSIS_PROMPT.format(title=title, transcript=transcript)
    
    try:
        response = client.generate_text(
            prompt=prompt,
            max_tokens=1024,
            temperature=0.3  # Lower temp for consistent analysis
        )
        
        # Parse JSON response
        # Clean up response if wrapped in markdown
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        
        import json
        result = json.loads(response.strip())
        result["video_id"] = video_id
        result["title"] = title
        result["url"] = f"https://youtube.com/watch?v={video_id}"
        
        # Convert poor_phrases list to string for CSV
        phrases = result.get("poor_phrases", [])
        if isinstance(phrases, list):
            result["poor_phrases_str"] = " | ".join(phrases) if phrases else "None"
        else:
            result["poor_phrases_str"] = str(phrases) if phrases else "None"
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON parse error: {e}")
        return {
            "video_id": video_id,
            "title": title,
            "url": f"https://youtube.com/watch?v={video_id}",
            "has_real_issues": False,
            "detailed_assessment": f"Analysis failed to parse response. Manual review needed.",
            "poor_phrases_str": "Error - manual review",
            "action_required": "REVIEW - Analysis error",
            "risk_score": 5,
            "error": str(e)
        }
    except Exception as e:
        print(f"  ❌ Analysis error: {e}")
        return {
            "video_id": video_id,
            "title": title,
            "url": f"https://youtube.com/watch?v={video_id}",
            "has_real_issues": False,
            "detailed_assessment": f"Analysis failed: {str(e)}",
            "poor_phrases_str": "Error - manual review",
            "action_required": "REVIEW - Analysis error",
            "risk_score": 5,
            "error": str(e)
        }

def save_to_csv(results, video_stats, output_path):
    """Save all results to a CSV file with views data."""
    # Add views to results
    for result in results:
        vid_id = result.get("video_id", "")
        result["total_lifetime_views"] = video_stats.get(vid_id, 0)
    
    # Sort by risk score descending (highest risk first)
    sorted_results = sorted(results, key=lambda x: x.get("risk_score", 0), reverse=True)
    
    fieldnames = [
        "risk_score",
        "total_lifetime_views",
        "action_required",
        "title",
        "poor_phrases",
        "detailed_assessment",
        "video_id",
        "url",
        "has_issues"
    ]
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        
        for result in sorted_results:
            row = {
                "risk_score": result.get("risk_score", "N/A"),
                "total_lifetime_views": result.get("total_lifetime_views", 0),
                "action_required": result.get("action_required", "REVIEW"),
                "title": result.get("title", "Unknown"),
                "poor_phrases": result.get("poor_phrases_str", "None"),
                "detailed_assessment": result.get("detailed_assessment", ""),
                "video_id": result.get("video_id", ""),
                "url": result.get("url", ""),
                "has_issues": "YES" if result.get("has_real_issues") else "NO"
            }
            writer.writerow(row)
    
    return sorted_results

def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Set ANTHROPIC_API_KEY environment variable")
        return
    
    if not YT_API_KEY:
        print("⚠️  YT_API_KEY not set - views will be 0")
    
    print("=" * 60)
    print("FAST FRIENDS CONTENT CHECKER")
    print("Preparing for December 19 YPP Reapplication")
    print("=" * 60)
    
    # Load transcripts
    print(f"\n📂 Loading transcripts from {TRANSCRIPT_DIR}...")
    transcripts = load_transcripts(TRANSCRIPT_DIR)
    
    if not transcripts:
        print("❌ No transcripts found. Run fastfriends_transcripts.py first!")
        return
    
    print(f"✅ Found {len(transcripts)} transcripts to analyze")
    
    # Fetch video stats from YouTube
    video_stats = {}
    if YT_API_KEY:
        print(f"\n📊 Fetching view counts from YouTube API...")
        youtube = build("youtube", "v3", developerKey=YT_API_KEY)
        video_ids = list(transcripts.keys())
        video_stats = get_video_stats(youtube, video_ids)
        print(f"✅ Got stats for {len(video_stats)} videos\n")
    else:
        print("⚠️  Skipping view counts (no YT_API_KEY)\n")
    
    # Create Claude client (using Sonnet 4 - 3.5 was retired July 2025)
    client = create_client(api_key=api_key, model="claude-sonnet-4-20250514")
    
    results = []
    
    for i, (video_id, video_data) in enumerate(transcripts.items(), 1):
        views = video_stats.get(video_id, 0)
        views_str = f"{views:,}" if views else "?"
        print(f"[{i}/{len(transcripts)}] {video_data['title'][:45]}... ({views_str} views)")
        
        result = analyze_transcript(client, video_id, video_data)
        results.append(result)
        
        # Show immediate feedback with risk score
        risk = result.get("risk_score", 0)
        action = result.get("action_required", "REVIEW")[:40]
        
        if risk >= 7:
            icon = "🔴"
        elif risk >= 4:
            icon = "🟠"
        elif risk >= 2:
            icon = "🟡"
        else:
            icon = "🟢"
            
        print(f"   {icon} Risk: {risk}/10 | {action}")
        
        # Small delay to avoid rate limits
        if i < len(transcripts):
            time.sleep(1)
    
    # Save to CSV with views
    print(f"\n💾 Saving detailed report to {OUTPUT_CSV}...")
    sorted_results = save_to_csv(results, video_stats, OUTPUT_CSV)
    
    # Print summary
    remove_count = sum(1 for r in results if "REMOVE" in r.get("action_required", ""))
    edit_count = sum(1 for r in results if "EDIT" in r.get("action_required", ""))
    keep_count = sum(1 for r in results if "KEEP" in r.get("action_required", ""))
    high_risk = [r for r in results if r.get("risk_score", 0) >= 7]
    
    print("\n" + "=" * 60)
    print("CONTENT REVIEW COMPLETE")
    print("=" * 60)
    print(f"📊 Total Videos Analyzed: {len(results)}")
    print(f"🔴 REMOVE recommended: {remove_count}")
    print(f"🟠 EDIT recommended:   {edit_count}")
    print(f"🟢 KEEP (safe):        {keep_count}")
    print("")
    print(f"📁 Full report saved to: {OUTPUT_CSV}")
    print("   Open in Excel/Google Sheets to review all details")
    print("")
    
    if high_risk:
        print("⚠️  HIGH RISK VIDEOS TO ADDRESS BEFORE DEC 19:")
        print("-" * 60)
        for r in high_risk[:10]:  # Show top 10
            views = r.get("total_lifetime_views", 0)
            print(f"   [{r.get('risk_score')}/10] {r.get('title', 'Unknown')[:40]} ({views:,} views)")
            print(f"          → {r.get('action_required', 'REVIEW')[:55]}")
        if len(high_risk) > 10:
            print(f"   ... and {len(high_risk) - 10} more (see CSV)")
    
    print("")
    print("=" * 60)
    print("NEXT STEPS:")
    print("=" * 60)
    print("1. Open fastfriends_content_review.csv in Excel/Sheets")
    print("2. Review risk_score vs total_lifetime_views")
    print("3. Check poor_phrases column for actual problematic quotes")
    print("4. High views + low risk = KEEP")
    print("5. High risk + any views = Review poor_phrases carefully")
    print("=" * 60)

if __name__ == "__main__":
    main()