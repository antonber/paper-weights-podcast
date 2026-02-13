#!/usr/bin/env python3
"""
Extract timestamps for podcast sections from MP3 file and script.

Usage: python3 extract_timestamps.py <mp3_file> <script_file> [date_str]

This utility:
1. Parses the script into sections (## headers = chapters)
2. Uses proportional method from add_chapters.py (segment count / total segments * total duration)
3. Returns timestamps as "MM:SS" format
4. Can optionally read from {date_str}-timestamps.json for precise timestamps

Returns list of {title, timestamp_str} dicts.
"""

import re
import sys
import json
from pathlib import Path
from mutagen.mp3 import MP3


def parse_script_sections(script_path):
    """Parse script into sections with their segment counts."""
    with open(script_path) as f:
        content = f.read()
    
    # Split by ## headers
    parts = re.split(r'^## ', content, flags=re.MULTILINE)
    
    sections = []
    for part in parts[1:]:  # skip content before first ##
        lines = part.strip().split('\n')
        title = lines[0].strip()
        
        # Clean up title - remove duration hints
        clean_title = re.sub(r'\s*\(\d+ (?:min|sec)(?:, [^)]+)?\)\s*$', '', title)
        
        # Count dialogue segments in this section
        body = '\n'.join(lines[1:])
        segments = re.findall(r'\*\*\w+\*\*:', body)
        
        sections.append({
            'title': clean_title,
            'segment_count': len(segments),
        })
    
    return sections


def calculate_proportional_timestamps(mp3_path, sections):
    """Calculate proportional timestamps based on segment counts."""
    audio = MP3(mp3_path)
    total_duration_ms = int(audio.info.length * 1000)
    
    total_segments = sum(s['segment_count'] for s in sections)
    if total_segments == 0:
        return []
    
    # Calculate cumulative start times
    timestamps = []
    current_ms = 0
    
    for section in sections:
        # Format timestamp as MM:SS
        minutes = current_ms // 60000
        seconds = (current_ms % 60000) // 1000
        timestamp_str = f"{minutes:02d}:{seconds:02d}"
        
        timestamps.append({
            'title': section['title'],
            'timestamp_str': timestamp_str
        })
        
        # Move to next section
        if total_segments > 0:
            segment_duration = (section['segment_count'] / total_segments) * total_duration_ms
            current_ms += int(segment_duration)
    
    return timestamps


def load_precise_timestamps(date_str, episodes_dir):
    """Load precise timestamps from {date}-timestamps.json if available."""
    if not date_str:
        return None
        
    timestamps_file = Path(episodes_dir) / f"{date_str}-timestamps.json"
    if not timestamps_file.exists():
        return None
        
    try:
        with open(timestamps_file) as f:
            data = json.load(f)
            
        # Convert to our format
        timestamps = []
        for item in data:
            if 'title' in item and 'timestamp_ms' in item:
                ms = item['timestamp_ms']
                minutes = ms // 60000
                seconds = (ms % 60000) // 1000
                timestamp_str = f"{minutes:02d}:{seconds:02d}"
                
                timestamps.append({
                    'title': item['title'],
                    'timestamp_str': timestamp_str
                })
                
        return timestamps
    except Exception as e:
        print(f"Warning: Could not load precise timestamps from {timestamps_file}: {e}", file=sys.stderr)
        return None


def extract_timestamps(mp3_path, script_path, date_str=None):
    """Main function to extract timestamps from MP3 and script."""
    episodes_dir = Path(script_path).parent
    
    # Try to load precise timestamps first
    if date_str:
        precise_timestamps = load_precise_timestamps(date_str, episodes_dir)
        if precise_timestamps:
            print(f"Using precise timestamps from {date_str}-timestamps.json", file=sys.stderr)
            return precise_timestamps
    
    # Fall back to proportional calculation
    print(f"Calculating proportional timestamps from script structure", file=sys.stderr)
    sections = parse_script_sections(script_path)
    return calculate_proportional_timestamps(mp3_path, sections)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 extract_timestamps.py <mp3_file> <script_file> [date_str]")
        sys.exit(1)
    
    mp3_path = sys.argv[1]
    script_path = sys.argv[2]
    date_str = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        timestamps = extract_timestamps(mp3_path, script_path, date_str)
        
        # Output as JSON for easy consumption
        print(json.dumps(timestamps, indent=2))
        
    except Exception as e:
        print(f"Error extracting timestamps: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()