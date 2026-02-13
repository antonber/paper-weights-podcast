#!/usr/bin/env python3
"""Add ID3 chapter markers to podcast MP3 based on script sections.

Usage: python3 add_chapters.py <mp3_file> <script_file>

Calculates chapter positions by measuring the duration of each TTS segment,
then maps section headers to cumulative timestamps.
"""

import re
import sys
import os
import subprocess
import json
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, CTOC, CHAP, TIT2, CTOCFlags

def get_segment_durations(mp3_dir, date_str):
    """Get duration of the full MP3 and estimate chapter positions from script structure."""
    pass

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

def calculate_chapter_times(mp3_path, sections):
    """Calculate chapter start times based on proportional segment counts."""
    audio = MP3(mp3_path)
    total_duration_ms = int(audio.info.length * 1000)
    
    total_segments = sum(s['segment_count'] for s in sections)
    
    # Each segment gets ~equal time (they have similar word counts + silence gap)
    # Calculate cumulative start times
    chapters = []
    current_ms = 0
    
    for section in sections:
        chapters.append({
            'title': section['title'],
            'start_ms': current_ms,
        })
        segment_duration = (section['segment_count'] / total_segments) * total_duration_ms
        current_ms += int(segment_duration)
    
    # Set end times
    for i, ch in enumerate(chapters):
        if i + 1 < len(chapters):
            ch['end_ms'] = chapters[i + 1]['start_ms']
        else:
            ch['end_ms'] = total_duration_ms
    
    return chapters, total_duration_ms

def add_chapters_to_mp3(mp3_path, chapters):
    """Add ID3v2 chapter frames to MP3."""
    audio = MP3(mp3_path)
    
    if audio.tags is None:
        audio.add_tags()
    
    tags = audio.tags
    
    # Remove existing chapter tags
    to_remove = [k for k in tags.keys() if k.startswith('CHAP') or k.startswith('CTOC')]
    for k in to_remove:
        del tags[k]
    
    # Add CHAP frames
    chap_ids = []
    for i, ch in enumerate(chapters):
        chap_id = f'chp{i}'
        chap_ids.append(chap_id)
        
        chap = CHAP(
            element_id=chap_id,
            start_time=ch['start_ms'],
            end_time=ch['end_ms'],
            start_offset=0xFFFFFFFF,
            end_offset=0xFFFFFFFF,
            sub_frames=[
                TIT2(encoding=3, text=[ch['title']])
            ]
        )
        tags.add(chap)
    
    # Add CTOC (table of contents)
    ctoc = CTOC(
        element_id='toc',
        flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
        child_element_ids=chap_ids,
        sub_frames=[
            TIT2(encoding=3, text=['Table of Contents'])
        ]
    )
    tags.add(ctoc)
    
    audio.save()
    return len(chapters)

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 add_chapters.py <mp3_file> <script_file>")
        sys.exit(1)
    
    mp3_path = sys.argv[1]
    script_path = sys.argv[2]
    
    print(f"📖 Parsing script: {script_path}")
    sections = parse_script_sections(script_path)
    
    for s in sections:
        print(f"  📌 {s['title']} ({s['segment_count']} segments)")
    
    print(f"\n⏱️ Calculating chapter times...")
    chapters, total_ms = calculate_chapter_times(mp3_path, sections)
    
    for ch in chapters:
        start_m = ch['start_ms'] // 60000
        start_s = (ch['start_ms'] % 60000) // 1000
        print(f"  [{start_m:02d}:{start_s:02d}] {ch['title']}")
    
    print(f"\n📝 Writing {len(chapters)} chapters to {mp3_path}")
    count = add_chapters_to_mp3(mp3_path, chapters)
    
    total_m = total_ms // 60000
    total_s = (total_ms % 60000) // 1000
    print(f"✅ Added {count} chapters to {total_m}m {total_s}s episode")

if __name__ == '__main__':
    main()
