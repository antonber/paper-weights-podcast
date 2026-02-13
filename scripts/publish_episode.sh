#!/bin/bash
# publish_episode.sh - Upload podcast episode to GitHub Releases and update RSS feed
# Usage: ./publish_episode.sh YYYY-MM-DD

set -euo pipefail

# Configuration
REPO="antonber/paper-weights-podcast"
PROJECT_DIR="$HOME/projects/arxiv-podcast"
EPISODES_DIR="$PROJECT_DIR/episodes"
SCRIPTS_DIR="$PROJECT_DIR/scripts"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    log_error "GitHub CLI (gh) is not installed or not in PATH"
fi

# Check if ffprobe is available
if ! command -v ffprobe &> /dev/null; then
    log_error "ffprobe is not installed or not in PATH"
fi

# Check if date argument is provided
if [ $# -eq 0 ]; then
    log_error "Usage: $0 YYYY-MM-DD"
fi

DATE="$1"

# Validate date format
if ! [[ "$DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    log_error "Invalid date format. Use YYYY-MM-DD"
fi

# Find the MP3 file (could be podcast.mp3 or podcast-v2.mp3)
MP3_FILE=""
if [ -f "$EPISODES_DIR/${DATE}-podcast.mp3" ]; then
    MP3_FILE="$EPISODES_DIR/${DATE}-podcast.mp3"
elif [ -f "$EPISODES_DIR/${DATE}-podcast-v2.mp3" ]; then
    MP3_FILE="$EPISODES_DIR/${DATE}-podcast-v2.mp3"
else
    log_error "No podcast file found for date $DATE"
fi

log_info "Found episode file: $(basename "$MP3_FILE")"

# Extract metadata using ffprobe
log_info "Extracting audio metadata..."
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$MP3_FILE" 2>/dev/null || echo "0")
DURATION_MIN=$(echo "$DURATION / 60" | bc)
FILE_SIZE=$(du -h "$MP3_FILE" | cut -f1)

log_info "Duration: ${DURATION_MIN} minutes, Size: ${FILE_SIZE}"

# Check if release already exists
log_info "Checking if release $DATE already exists..."
if gh release view "$DATE" --repo "$REPO" &> /dev/null; then
    log_warn "Release $DATE already exists. Deleting and recreating..."
    gh release delete "$DATE" --repo "$REPO" --yes
fi

# Create GitHub Release
log_info "Creating GitHub Release for $DATE..."
RELEASE_NOTES="Paper Weights podcast episode for $DATE

Duration: ${DURATION_MIN} minutes
File size: ${FILE_SIZE}

Generated: $(date '+%Y-%m-%d %H:%M:%S %Z')"

gh release create "$DATE" \
    --repo "$REPO" \
    --title "Episode $DATE" \
    --notes "$RELEASE_NOTES" \
    "$MP3_FILE"

log_info "✓ Episode uploaded to GitHub Releases"

# Upload cover art to 'assets' release if it doesn't exist
if ! gh release view "assets" --repo "$REPO" &> /dev/null; then
    log_info "Creating 'assets' release for cover art..."
    gh release create "assets" \
        --repo "$REPO" \
        --title "Podcast Assets" \
        --notes "Static assets for podcast (cover art, etc.)" \
        "$PROJECT_DIR/branding/cover-art.png"
    log_info "✓ Cover art uploaded"
else
    log_info "Assets release already exists (cover art should be available)"
fi

# Generate/update RSS feed
log_info "Generating RSS feed..."
python3 "$SCRIPTS_DIR/generate_rss.py"

# Upload RSS feed to GitHub repo (main branch)
log_info "Uploading RSS feed to GitHub..."
cd "$PROJECT_DIR"

# Initialize git if needed
if [ ! -d ".git" ]; then
    git init
    git remote add origin "https://github.com/$REPO.git"
fi

# Commit and push feed.xml
cp feed.xml /tmp/feed.xml.backup
git fetch origin main || git fetch origin master || true
git checkout -B rss-feed
cp /tmp/feed.xml.backup feed.xml
git add feed.xml
git commit -m "Update RSS feed - episode $DATE" || true
git push -f origin rss-feed:main

log_info "✓ RSS feed updated"

# Show final URLs
echo ""
log_info "========================================="
log_info "Episode published successfully!"
log_info "========================================="
echo ""
echo "Episode URL:"
echo "  https://github.com/$REPO/releases/download/$DATE/$(basename "$MP3_FILE")"
echo ""
echo "RSS Feed URL:"
echo "  https://raw.githubusercontent.com/$REPO/main/feed.xml"
echo ""
log_info "Next step: Test the RSS feed in a podcast app, then configure Spotify for Podcasters to import from the RSS URL."
