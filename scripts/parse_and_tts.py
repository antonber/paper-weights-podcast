#!/usr/bin/env python3
"""Parse podcast script and generate TTS segments, then concatenate."""

import subprocess
import os
import re
import sys
import tempfile
import json

DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-02-11"
SCRIPT = os.path.expanduser(f"~/projects/arxiv-podcast/episodes/{DATE}-script.md")
OUTDIR = os.path.expanduser("~/projects/arxiv-podcast/episodes")
OUTPUT = os.path.join(OUTDIR, f"{DATE}-podcast.mp3")

VOICES = {
    "Alex": "iP95p4xoKVk53GoZ742B",
    "Maya": "FGY2WhTYpPnrIDTdsKH5",
}

def parse_script(path):
    with open(path) as f:
        content = f.read()
    pattern = r'\*\*(\w+)\*\*:\s*(.*?)(?=\n\n\*\*\w+\*\*:|\n---|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)
    lines = []
    for speaker, text in matches:
        if speaker in VOICES:
            text = text.strip()
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            text = re.sub(r'\*(.+?)\*', r'\1', text)
            text = text.replace('\n', ' ')
            text = re.sub(r'\s+', ' ', text).strip()
            if text:
                lines.append((speaker, text))
    return lines

def get_audio_duration(path):
    """Get duration of an audio file in seconds."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def validate_segment(outfile, text_len):
    """
    Validate a TTS segment for quality issues.
    Returns (is_valid, reason).
    """
    if not os.path.exists(outfile):
        return False, "file missing"
    
    file_size = os.path.getsize(outfile)
    duration = get_audio_duration(outfile)
    
    # Check 1: File too small (likely empty or corrupted)
    if file_size < 1000:
        return False, f"file too small ({file_size} bytes)"
    
    # Check 2: Duration too short for text length
    # Rough heuristic: ~15 chars per second of speech
    expected_min_duration = max(0.5, text_len / 25)  # very generous lower bound
    if duration < 0.5:
        return False, f"duration too short ({duration:.1f}s)"
    
    # Check 3: Abnormal bitrate (garbled audio often has weird bitrate)
    # Normal MP3 at 128kbps: ~16KB per second
    if duration > 0:
        bytes_per_sec = file_size / duration
        if bytes_per_sec < 2000:  # way below normal MP3
            return False, f"abnormal bitrate ({bytes_per_sec:.0f} B/s)"
        if bytes_per_sec > 100000:  # way above normal
            return False, f"abnormal bitrate ({bytes_per_sec:.0f} B/s)"
    
    # Check 4: Duration way too long for text (possible looping/stuck)
    expected_max_duration = text_len / 5  # very generous upper bound (~5 chars/sec)
    if duration > expected_max_duration and duration > 30:
        return False, f"duration too long ({duration:.1f}s for {text_len} chars)"
    
    return True, f"ok ({duration:.1f}s, {file_size/1024:.0f}KB)"


def generate_segment(speaker, text, voice_id, index, tmpdir, max_retries=2):
    outfile = os.path.join(tmpdir, f"seg_{index:04d}.mp3")
    # Truncate if too long
    if len(text) > 2500:
        # Split at sentence boundary
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunk = ""
        for s in sentences:
            if len(chunk) + len(s) < 2400:
                chunk += s + " "
            else:
                break
        text = chunk.strip() if chunk.strip() else text[:2500]
    
    for attempt in range(max_retries + 1):
        cmd = ["sag", "--model-id", "eleven_v3", "-v", voice_id, "-o", outfile, text]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        except Exception as e:
            print(f"  ❌ Segment {index} generation failed (attempt {attempt+1}): {e}")
            if attempt < max_retries:
                print(f"  🔄 Retrying...")
                continue
            return None
        
        # Validate the output
        is_valid, reason = validate_segment(outfile, len(text))
        if is_valid:
            if attempt > 0:
                print(f"  ✅ Segment {index} passed validation on retry {attempt+1}: {reason}")
            return outfile
        else:
            print(f"  ⚠️  Segment {index} failed validation (attempt {attempt+1}): {reason}")
            if attempt < max_retries:
                print(f"  🔄 Retrying...")
                # Remove bad file before retry
                try:
                    os.remove(outfile)
                except OSError:
                    pass
            else:
                print(f"  ❌ Segment {index} failed all {max_retries+1} attempts — SKIPPING")
                return None
    
    return None

def main():
    print(f"📝 Parsing script: {SCRIPT}")
    lines = parse_script(SCRIPT)
    print(f"  Found {len(lines)} dialogue segments")
    
    if not lines:
        print("❌ No dialogue found!")
        sys.exit(1)
    
    tmpdir = tempfile.mkdtemp()
    
    # Generate silence
    silence = os.path.join(tmpdir, "silence.mp3")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                     "-t", "0.4", "-q:a", "9", silence], capture_output=True)
    
    segments = []
    skipped = []
    for i, (speaker, text) in enumerate(lines):
        print(f"  [{i:03d}] {speaker} ({len(text)} chars)")
        outfile = generate_segment(speaker, text, VOICES[speaker], i, tmpdir)
        if outfile and os.path.exists(outfile):
            segments.append(outfile)
        else:
            skipped.append(i)
            print(f"  ⚠️  Segment {i} skipped entirely")
    
    if skipped:
        print(f"\n⚠️  {len(skipped)} segments skipped due to quality issues: {skipped}")
    
    print(f"\n🔗 Concatenating {len(segments)} segments...")
    concat_file = os.path.join(tmpdir, "concat.txt")
    with open(concat_file, "w") as f:
        for i, seg in enumerate(segments):
            f.write(f"file '{seg}'\n")
            if i < len(segments) - 1:
                f.write(f"file '{silence}'\n")
    
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
                     "-c", "copy", OUTPUT], capture_output=True)
    
    # Stats
    size = os.path.getsize(OUTPUT)
    result = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                            "-of", "csv=p=0", OUTPUT], capture_output=True, text=True)
    duration = float(result.stdout.strip())
    
    print(f"\n✅ Output: {OUTPUT}")
    print(f"  Size: {size / 1024 / 1024:.1f} MB")
    print(f"  Duration: {int(duration // 60)}m {int(duration % 60)}s")
    print(f"  Segments: {len(segments)}")
    
    # Cleanup
    import shutil
    shutil.rmtree(tmpdir)

if __name__ == "__main__":
    main()
