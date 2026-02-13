#!/usr/bin/env python3
import re
import subprocess
import json
import os
import sys
from pathlib import Path

DATE = "2026-02-11"
SCRIPT = Path.home() / "projects/arxiv-podcast/episodes" / f"{DATE}-script.md"
TMPDIR = Path("/tmp/podcast-" + DATE)
TMPDIR.mkdir(exist_ok=True)

ALEX_VOICE = "iP95p4xoKVk53GoZ742B"  # Chris
MAYA_VOICE = "FGY2WhTYpPnrIDTdsKH5"  # Laura

print(f"📝 Script: {SCRIPT}")
print(f"📁 Temp dir: {TMPDIR}")

# Read script
with open(SCRIPT) as f:
    content = f.read()

# Parse dialogue segments
pattern = r'\*\*(\w+)\*\*:\s*(.*?)(?=\n\n\*\*\w+\*\*:|\n---|\Z)'
matches = re.findall(pattern, content, re.DOTALL)

print(f"🎙️ Found {len(matches)} segments")

# Generate silence
silence_path = TMPDIR / "silence.mp3"
subprocess.run([
    "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
    "-t", "0.4", "-q:a", "9", str(silence_path)
], capture_output=True)

# Generate each segment
segment_files = []
for idx, (speaker, text) in enumerate(matches):
    text = text.strip()
    voice = ALEX_VOICE if speaker == "Alex" else MAYA_VOICE
    
    padded = f"{idx:03d}"
    outfile = TMPDIR / f"seg_{padded}.mp3"
    
    # Truncate if too long
    if len(text) > 2500:
        print(f"  [{padded}] {speaker} (truncating from {len(text)} chars)")
        text = text[:2500]
    else:
        print(f"  [{padded}] {speaker} ({len(text)} chars)")
    
    # Generate with sag CLI
    result = subprocess.run([
        "sag", "--model-id", "eleven_v3",
        "-v", voice, "-o", str(outfile), text
    ], capture_output=True)
    
    if result.returncode != 0:
        print(f"    ❌ Failed: {result.stderr.decode()}")
        continue
    
    if outfile.exists():
        segment_files.append(str(outfile))

print(f"\n🔗 Concatenating {len(segment_files)} segments...")

# Build concat list
concat_list = TMPDIR / "concat.txt"
with open(concat_list, 'w') as f:
    for i, seg in enumerate(segment_files):
        f.write(f"file '{seg}'\n")
        if i < len(segment_files) - 1:  # Add silence between segments
            f.write(f"file '{silence_path}'\n")

# Concatenate
output = Path.home() / "projects/arxiv-podcast/episodes" / f"{DATE}-podcast.mp3"
result = subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
    "-i", str(concat_list), "-c", "copy", str(output)
], capture_output=True)

if result.returncode != 0:
    print(f"❌ Concatenation failed: {result.stderr.decode()}")
    sys.exit(1)

# Get stats
stats = subprocess.run([
    "ffprobe", "-v", "quiet", "-show_format", "-print_format", "json",
    str(output)
], capture_output=True, text=True)

if stats.returncode == 0:
    info = json.loads(stats.stdout)
    duration = float(info['format']['duration'])
    size = int(info['format']['size'])
    
    print(f"\n✅ Episode complete!")
    print(f"📊 Duration: {int(duration // 60)}:{int(duration % 60):02d}")
    print(f"📦 Size: {size / 1024 / 1024:.2f} MB")
    print(f"🎵 Segments: {len(segment_files)}")
    print(f"📍 Output: {output}")
else:
    print(f"\n✅ Episode generated: {output}")
    print(f"🎵 Segments: {len(segment_files)}")
