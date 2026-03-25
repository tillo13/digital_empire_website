#!/usr/bin/env python3
"""
Rename transcript files to include video titles.
Changes: transcript_{id}.txt → transcript_{id}_{title}.txt
"""

import os
import re
from pathlib import Path

TRANSCRIPT_DIR = "fastfriends_videos"

def sanitize_filename(title, max_length=50):
    """Make title safe for filenames."""
    # Remove or replace invalid characters
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    # Replace spaces and other chars with underscores
    safe = re.sub(r'[\s\-]+', '_', safe)
    # Remove any remaining non-alphanumeric (except underscore)
    safe = re.sub(r'[^\w]', '', safe)
    # Truncate if too long
    if len(safe) > max_length:
        safe = safe[:max_length]
    # Remove trailing underscores
    safe = safe.rstrip('_')
    return safe

def main():
    transcript_path = Path(TRANSCRIPT_DIR)
    
    if not transcript_path.exists():
        print(f"❌ Directory not found: {TRANSCRIPT_DIR}")
        return
    
    files = list(transcript_path.glob("transcript_*.txt"))
    print(f"📂 Found {len(files)} transcript files\n")
    
    renamed = 0
    skipped = 0
    
    for file in files:
        # Skip if already has a title in filename (more than just ID)
        name_parts = file.stem.split('_')
        if len(name_parts) > 2:
            print(f"⏭️  Already renamed: {file.name}")
            skipped += 1
            continue
        
        # Extract video ID
        video_id = file.stem.replace("transcript_", "")
        
        # Read title from first line
        with open(file, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        
        if first_line.startswith("# "):
            title = first_line[2:]  # Remove "# "
        else:
            print(f"⚠️  No title found: {file.name}")
            skipped += 1
            continue
        
        # Create new filename
        safe_title = sanitize_filename(title)
        new_name = f"transcript_{video_id}_{safe_title}.txt"
        new_path = transcript_path / new_name
        
        # Rename
        print(f"📝 {file.name}")
        print(f"   → {new_name}")
        
        file.rename(new_path)
        renamed += 1
    
    print(f"\n✅ Done! Renamed: {renamed}, Skipped: {skipped}")

if __name__ == "__main__":
    main()