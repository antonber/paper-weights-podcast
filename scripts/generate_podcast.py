#!/usr/bin/env python3
"""Generate podcast audio from script using ElevenLabs via sag CLI."""

import subprocess
import os
import re
import tempfile
import json

SCRIPT_PATH = os.path.expanduser("~/projects/arxiv-podcast/episodes/2026-02-09-script.md")
OUTPUT_DIR = os.path.expanduser("~/projects/arxiv-podcast/episodes")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "2026-02-09-podcast-v2.mp3")

# Voice mapping
VOICES = {
    "Alex": "iP95p4xoKVk53GoZ742B",   # Chris - Charming, Down-to-Earth
    "Maya": "FGY2WhTYpPnrIDTdsKH5",   # Laura - Enthusiast, Quirky Attitude
}

def parse_script(path):
    """Parse script into ordered list of (speaker, text) tuples."""
    with open(path, 'r') as f:
        content = f.read()
    
    # Find all dialogue lines: **Speaker**: text
    pattern = r'\*\*(\w+)\*\*:\s*(.*?)(?=\n\n\*\*\w+\*\*:|\n###|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    lines = []
    for speaker, text in matches:
        if speaker in VOICES:
            # Clean up markdown formatting
            text = text.strip()
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # Remove bold
            text = re.sub(r'\*(.+?)\*', r'\1', text)  # Remove italic
            text = text.replace('—', ' — ')
            text = text.replace('\n', ' ')
            text = re.sub(r'\s+', ' ', text).strip()
            if text:
                lines.append((speaker, text))
    
    return lines

def generate_audio_segment(speaker, text, voice_id, index, tmpdir):
    """Generate audio for one dialogue segment using sag."""
    outfile = os.path.join(tmpdir, f"seg_{index:04d}.mp3")
    
    # Truncate very long segments for sag (split into chunks if needed)
    max_chars = 2500
    if len(text) > max_chars:
        # Split at sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current = ""
        for s in sentences:
            if len(current) + len(s) > max_chars:
                if current:
                    chunks.append(current.strip())
                current = s
            else:
                current += " " + s
        if current:
            chunks.append(current.strip())
        
        # Generate each chunk
        chunk_files = []
        for ci, chunk in enumerate(chunks):
            chunk_file = os.path.join(tmpdir, f"seg_{index:04d}_chunk_{ci:02d}.mp3")
            cmd = ["sag", "-v", voice_id, "-o", chunk_file, "--model-id", "eleven_v3", chunk]
            print(f"  Generating chunk {ci+1}/{len(chunks)} for {speaker}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                print(f"  ERROR: {result.stderr[:200]}")
                return None
            chunk_files.append(chunk_file)
        
        # Concatenate chunks
        if len(chunk_files) > 1:
            list_file = os.path.join(tmpdir, f"seg_{index:04d}_list.txt")
            with open(list_file, 'w') as f:
                for cf in chunk_files:
                    f.write(f"file '{cf}'\n")
            subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, 
                          "-c", "copy", outfile], capture_output=True, timeout=30)
        else:
            os.rename(chunk_files[0], outfile)
    else:
        cmd = ["sag", "-v", voice_id, "-o", outfile, "--model-id", "eleven_v3", text]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr[:200]}")
            return None
    
    return outfile if os.path.exists(outfile) else None

def add_short_silence(tmpdir, index, duration_ms=400):
    """Generate a short silence file."""
    outfile = os.path.join(tmpdir, f"silence_{index:04d}.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono",
        "-t", str(duration_ms/1000), "-q:a", "9", outfile
    ], capture_output=True, timeout=10)
    return outfile if os.path.exists(outfile) else None

def main():
    print("=== arXiv AI Podcast Generator ===\n")
    
    # Parse script
    lines = parse_script(SCRIPT_PATH)
    print(f"Parsed {len(lines)} dialogue segments\n")
    
    if not lines:
        print("ERROR: No dialogue lines found!")
        return
    
    tmpdir = tempfile.mkdtemp(prefix="podcast_")
    print(f"Working directory: {tmpdir}\n")
    
    # Generate audio for each segment
    audio_files = []
    for i, (speaker, text) in enumerate(lines):
        voice_id = VOICES[speaker]
        print(f"[{i+1}/{len(lines)}] {speaker}: {text[:80]}...")
        
        seg_file = generate_audio_segment(speaker, text, voice_id, i, tmpdir)
        if seg_file:
            audio_files.append(seg_file)
            # Add short pause between speakers
            silence = add_short_silence(tmpdir, i)
            if silence:
                audio_files.append(silence)
        else:
            print(f"  FAILED - skipping segment")
    
    if not audio_files:
        print("\nERROR: No audio segments generated!")
        return
    
    # Concatenate all segments
    print(f"\nConcatenating {len(audio_files)} audio files...")
    list_file = os.path.join(tmpdir, "final_list.txt")
    with open(list_file, 'w') as f:
        for af in audio_files:
            f.write(f"file '{af}'\n")
    
    result = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
        "-c:a", "libmp3lame", "-q:a", "2", OUTPUT_FILE
    ], capture_output=True, text=True, timeout=120)
    
    if result.returncode == 0:
        size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
        print(f"\n✅ Podcast saved: {OUTPUT_FILE} ({size_mb:.1f} MB)")
        
        # Get duration
        probe = subprocess.run([
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "json", OUTPUT_FILE
        ], capture_output=True, text=True)
        if probe.returncode == 0:
            dur = json.loads(probe.stdout)['format']['duration']
            mins = float(dur) / 60
            print(f"Duration: {mins:.1f} minutes")
    else:
        print(f"\nERROR concatenating: {result.stderr[:300]}")

if __name__ == "__main__":
    main()
