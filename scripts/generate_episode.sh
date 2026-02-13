#!/bin/bash
# Generate podcast episode from script
# Usage: ./generate_episode.sh <date>
set -e

DATE="${1:-$(date +%Y-%m-%d)}"
SCRIPT="$HOME/projects/arxiv-podcast/episodes/${DATE}-script.md"
DIGEST="$HOME/projects/arxiv-llm-digest/digests/${DATE}.md"
OUTDIR="$HOME/projects/arxiv-podcast/episodes"
TMPDIR=$(mktemp -d)
OUTPUT="${OUTDIR}/${DATE}-podcast.mp3"
METADATA="${OUTDIR}/${DATE}-metadata.json"

ALEX_VOICE="iP95p4xoKVk53GoZ742B"
MAYA_VOICE="FGY2WhTYpPnrIDTdsKH5"

echo "📝 Script: $SCRIPT"
echo "📖 Digest: $DIGEST"
echo "📁 Temp dir: $TMPDIR"

# Extract paper links from digest for show notes
echo "🔗 Extracting paper links..."
PAPER_LINKS=$(python3 << EOF
import re
import os

digest_path = "$DIGEST"
with open(digest_path) as f:
    content = f.read()

# Find all paper sections with titles and arXiv links
papers = []

# Pattern for paper entries
lines = content.split('\n')
current_title = None

for line in lines:
    # Look for paper titles (usually start with ### or bold)
    title_match = re.search(r'(?:^### |\*\*)([^\*]+?)(?:\*\*|\n|$)', line)
    if title_match:
        current_title = title_match.group(1).strip()
    
    # Look for arXiv links
    arxiv_match = re.search(r'https?://arxiv\.org/abs/(\d+\.\d+)', line)
    if arxiv_match and current_title:
        papers.append({
            'title': current_title,
            'url': f"https://arxiv.org/abs/{arxiv_match.group(1)}"
        })
        current_title = None

# Format as Markdown list
output = "\n## Papers Mentioned\n\n"
for p in papers[:18]:  # Limit to top 18 papers
    output += f"- [{p['title']}]({p['url']})\n"

print(output)
EOF
)

echo "Found papers:"
echo "$PAPER_LINKS"

echo "🎙️ Generating segments..."

# Create silence gap
ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=mono -t 0.4 -q:a 9 "$TMPDIR/silence.mp3" 2>/dev/null

# Parse and generate segments
SEG=0
SEGMENT_DURATIONS=()
SEGMENT_SPEAKERS=()

python3 << EOF | while read -r line; do
import re
import json

with open('$SCRIPT') as f:
    content = f.read()

pattern = r'\*\*(\w+)\*\*:\s*(.*?)(?=\n\n\*\*\w+\*\*:|\n---|\Z)'
matches = re.findall(pattern, content, re.DOTALL)

for i, (speaker, text) in enumerate(matches):
    text = text.strip().replace('"', '\\"')
    print(json.dumps({'idx': i, 'speaker': speaker, 'text': text}))
EOF
do
    idx=$(echo "$line" | python3 -c "import json,sys; print(json.load(sys.stdin)['idx'])")
    speaker=$(echo "$line" | python3 -c "import json,sys; print(json.load(sys.stdin)['speaker'])")
    text=$(echo "$line" | python3 -c "import json,sys; print(json.load(sys.stdin)['text'])")
    
    if [ "$speaker" = "Alex" ]; then
        voice="$ALEX_VOICE"
    else
        voice="$MAYA_VOICE"
    fi
    
    padded=$(printf "%03d" $idx)
    outfile="$TMPDIR/seg_${padded}.mp3"
    
    echo "  [$padded] $speaker (${#text} chars)"
    
    # Split if over 2500 chars
    if [ ${#text} -gt 2500 ]; then
        echo "    ⚠️ Long segment, splitting..."
        text="${text:0:2500}"
    fi
    
    sag --model-id eleven_v3 -v "$voice" -o "$outfile" "$text" 2>/dev/null
    
    if [ ! -f "$outfile" ]; then
        echo "    ❌ Failed to generate segment $padded"
        continue
    fi
    
    # Get segment duration
    seg_duration=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$outfile" 2>/dev/null || echo "0")
    SEGMENT_DURATIONS+=("$seg_duration")
    SEGMENT_SPEAKERS+=("$speaker")
    
    SEG=$((SEG + 1))
done

# Generate timestamps JSON
echo "⏰ Generating timestamp metadata..."
TIMESTAMPS_FILE="$OUTDIR/${DATE}-timestamps.json"

# Write segment durations to temp file
DURATIONS_FILE="$TMPDIR/durations.txt"
for duration in "${SEGMENT_DURATIONS[@]}"; do
    echo "$duration" >> "$DURATIONS_FILE"
done

python3 << EOF > "$TIMESTAMPS_FILE"
import re
import json

# Parse script sections
with open('$SCRIPT') as f:
    content = f.read()

# Split by ## headers
parts = re.split(r'^## ', content, flags=re.MULTILINE)

sections = []
total_segments = 0
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
        'start_segment': total_segments
    })
    total_segments += len(segments)

# Load actual segment durations from temp file
durations = []
try:
    with open('$DURATIONS_FILE') as f:
        for line in f:
            durations.append(float(line.strip()))
except:
    pass

silence_duration = 0.4  # 400ms silence gaps

# Calculate cumulative timestamps
timestamps = []
current_s = 0.0

for section in sections:
    timestamps.append({
        'title': section['title'],
        'timestamp_ms': int(current_s * 1000)
    })
    
    # Add durations for all segments in this section + silence gaps
    for i in range(section['segment_count']):
        seg_idx = section['start_segment'] + i
        if seg_idx < len(durations):
            current_s += durations[seg_idx]
            if seg_idx < len(durations) - 1:  # Add silence except after last segment
                current_s += silence_duration

print(json.dumps(timestamps, indent=2))
EOF

echo "📝 Saved timestamps: $TIMESTAMPS_FILE"

echo "🔗 Concatenating segments..."

# Build concat list
CONCAT_FILE="$TMPDIR/concat.txt"
> "$CONCAT_FILE"

for f in $(ls "$TMPDIR"/seg_*.mp3 2>/dev/null | sort); do
    echo "file '$f'" >> "$CONCAT_FILE"
    echo "file '$TMPDIR/silence.mp3'" >> "$CONCAT_FILE"
done

# Remove trailing silence
sed -i '' '$ d' "$CONCAT_FILE" 2>/dev/null || sed -i '$ d' "$CONCAT_FILE"

SEGCOUNT=$(grep -c "^file.*seg_" "$CONCAT_FILE" || echo 0)
echo "  Segments to concat: $SEGCOUNT"

ffmpeg -y -f concat -safe 0 -i "$CONCAT_FILE" -c copy "$OUTPUT" 2>/dev/null

# Add chapter markers
echo "📖 Adding chapters..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/add_chapters.py" "$OUTPUT" "$SCRIPT"

echo "✅ Output: $OUTPUT"
echo "📊 Stats:"
ls -lh "$OUTPUT"
DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUTPUT")
echo "  Duration: $(python3 -c "d=float('$DURATION'); print(f'{int(d//60)}m {int(d%60)}s')")"

# Generate metadata file with full description
echo "📝 Generating metadata..."
TITLE=$(python3 << EOF
import re
with open('$SCRIPT') as f:
    content = f.read()
# Find first paper title
match = re.search(r'Paper \d+:\s*([^\n(]+)', content)
title = match.group(1).strip() if match else "AI Research Digest"
print(f"Paper Weights: {title}")
EOF
)

cat > "$METADATA" << EOF
{
  "title": "$TITLE",
  "description": "Every morning, two hosts break down the AI papers that actually matter — one explains the science, one asks where the money is.\\n\\nToday covers $(echo "$SEGCOUNT" | python3 -c "import sys; n=int(sys.stdin.read().strip())//2; print(f'{n}')") papers from the arXiv LLM digest, including self-feedback reasoning, next-concept prediction, robot scientists, and more.\\n\\n$PAPER_LINKS",
  "duration": $(python3 -c "print(int(float('$DURATION')))")
}
EOF

echo "  Metadata: $METADATA"

# Cleanup
rm -rf "$TMPDIR"
echo "🎉 Done!"
