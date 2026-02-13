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
    """Parse script into sections with their segment counts.
    
    Handles multiple script formats:
    - ## Deep Dive 1: Paper Title (one section per paper)
    - ## Paper 1: Title (one section per paper)  
    - ### SEGMENT: PAPER 1 — Title (### sub-headers)
    - ## Deep Dives (single section with --- dividers between papers)
    """
    with open(script_path) as f:
        content = f.read()
    
    # First check for ### SEGMENT headers (Feb 9 format)
    segment_headers = re.findall(r'^### SEGMENT:\s*PAPER\s*\d+\s*[—–-]\s*(.+)', content, re.MULTILINE)
    if segment_headers:
        return _parse_segment_format(content)
    
    # Check if we have a "## Deep Dives" section with --- dividers
    if re.search(r'^## Deep Dives\s*$', content, re.MULTILINE):
        return _parse_deep_dives_block(content)
    
    # Default: split by ## headers
    return _parse_standard_sections(content)


def _parse_segment_format(content):
    """Parse ### SEGMENT: PAPER N — Title format."""
    parts = re.split(r'^### ', content, flags=re.MULTILINE)
    sections = []
    for part in parts[1:]:
        lines = part.strip().split('\n')
        title = lines[0].strip()
        body = '\n'.join(lines[1:])
        segments = re.findall(r'\*\*\w+\*\*:', body)
        
        paper_name = None
        m = re.match(r'SEGMENT:\s*PAPER\s*\d+\s*[—–-]\s*(.+)', title, re.IGNORECASE)
        if m:
            paper_name = m.group(1).strip()
        
        clean_title = re.sub(r'\s*\(\d+ (?:min|sec)(?:, [^)]+)?\)\s*$', '', title)
        
        sections.append({
            'title': clean_title,
            'segment_count': len(segments),
            'paper_name': paper_name,
            'is_quick_hits': False,
        })
    return sections


def _parse_deep_dives_block(content):
    """Parse ## Deep Dives with --- dividers between papers, plus ## Quick Hits."""
    sections = []
    
    # Split into top-level ## sections first
    top_parts = re.split(r'^## ', content, flags=re.MULTILINE)
    
    for part in top_parts[1:]:
        lines = part.strip().split('\n')
        section_title = lines[0].strip()
        body = '\n'.join(lines[1:])
        
        if section_title.lower() == 'deep dives':
            # Split by --- dividers to get individual paper discussions
            paper_blocks = re.split(r'\n---+\n', body)
            for block in paper_blocks:
                block = block.strip()
                if not block:
                    continue
                segs = re.findall(r'\*\*\w+\*\*:', block)
                if not segs:
                    continue
                # Try to identify paper name from first few dialogue lines
                paper_name = _extract_paper_name_from_dialogue(block)
                sections.append({
                    'title': paper_name or 'Deep Dive',
                    'segment_count': len(segs),
                    'paper_name': paper_name,
                    'is_quick_hits': False,
                })
        elif 'quick hit' in section_title.lower():
            segs = re.findall(r'\*\*\w+\*\*:', body)
            sections.append({
                'title': section_title,
                'segment_count': len(segs),
                'paper_name': None,
                'is_quick_hits': True,
            })
        else:
            # Cold Open, Outro, etc.
            segs = re.findall(r'\*\*\w+\*\*:', body)
            sections.append({
                'title': section_title,
                'segment_count': len(segs),
                'paper_name': None,
                'is_quick_hits': False,
            })
    
    return sections


def _extract_paper_name_from_dialogue(block):
    """Try to identify the paper being discussed from dialogue text."""
    # Look for quoted paper titles or key phrases
    # Common patterns: "called X", "paper called", "titled", or just quoted titles
    patterns = [
        r'(?:called|titled|paper[—–-]|it\'s)\s+["""]?([A-Z][^""".,]{10,60})',
        r'(?:paper|research|study)(?:\s+is)?\s+(?:about\s+)?["""]([^"""]{10,60})["""]',
    ]
    for pat in patterns:
        m = re.search(pat, block)
        if m:
            return m.group(1).strip().rstrip('.')
    return None


def _parse_standard_sections(content):
    """Parse standard ## Section Title format."""
    parts = re.split(r'^## ', content, flags=re.MULTILINE)
    
    sections = []
    for part in parts[1:]:
        lines = part.strip().split('\n')
        title = lines[0].strip()
        
        clean_title = re.sub(r'\s*\(\d+ (?:min|sec)(?:, [^)]+)?\)\s*$', '', title)
        
        body = '\n'.join(lines[1:])
        segments = re.findall(r'\*\*\w+\*\*:', body)
        
        paper_name = None
        for pat in [
            r'Deep Dive\s*\d*(?:\s*\([^)]*\))?:\s*(.+)',
            r'Paper\s*\d+:\s*(.+)',
        ]:
            m = re.match(pat, clean_title, re.IGNORECASE)
            if m:
                paper_name = m.group(1).strip()
                break
        
        is_quick_hits = 'quick hit' in clean_title.lower()
        
        sections.append({
            'title': clean_title,
            'segment_count': len(segments),
            'paper_name': paper_name,
            'is_quick_hits': is_quick_hits,
        })
    
    return sections


def get_paper_timestamps(mp3_path, script_path, date_str=None):
    """
    Get timestamps for paper sections.
    Returns dict with:
      - '__deep_dive_timestamps__': list of "MM:SS" strings in order (one per deep dive paper)
      - '__quick_hits__': "MM:SS" for start of quick hits
    The RSS generator maps these by index to its paper lists.
    """
    episodes_dir = Path(script_path).parent
    
    # Try precise timestamps first
    if date_str:
        precise = load_precise_timestamps(date_str, episodes_dir)
        if precise:
            mapping = {'__deep_dive_timestamps__': []}
            for ts in precise:
                if ts.get('paper_name'):
                    mapping['__deep_dive_timestamps__'].append(ts['timestamp_str'])
                if ts.get('is_quick_hits'):
                    mapping['__quick_hits__'] = ts['timestamp_str']
            if mapping['__deep_dive_timestamps__']:
                return mapping
    
    sections = parse_script_sections(script_path)
    audio = MP3(mp3_path)
    total_duration_ms = int(audio.info.length * 1000)
    total_segments = sum(s['segment_count'] for s in sections)
    if total_segments == 0:
        return {}
    
    mapping = {'__deep_dive_timestamps__': []}
    current_ms = 0
    
    for section in sections:
        minutes = current_ms // 60000
        seconds = (current_ms % 60000) // 1000
        ts_str = f"{minutes:02d}:{seconds:02d}"
        
        if section['paper_name'] or (section['segment_count'] > 0 and not section['is_quick_hits'] and section['title'] not in ('Cold Open', 'Outro', 'Wrap-Up', 'INTRO', 'WRAP-UP')):
            # Only add if it looks like a paper section (has dialogue, not intro/outro)
            if section['paper_name'] or section['segment_count'] >= 2:
                mapping['__deep_dive_timestamps__'].append(ts_str)
        if section['is_quick_hits']:
            mapping['__quick_hits__'] = ts_str
        
        segment_duration = (section['segment_count'] / total_segments) * total_duration_ms
        current_ms += int(segment_duration)
    
    return mapping


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