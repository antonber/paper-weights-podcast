# Podcast Publishing Guide

This guide explains how to publish episodes to the automated RSS feed system.

## Quick Start

To publish today's episode:
```bash
cd ~/projects/arxiv-podcast
./scripts/publish_episode.sh $(date +%Y-%m-%d)
```

To publish a specific date:
```bash
./scripts/publish_episode.sh 2026-02-11
```

## What Happens When You Publish

1. **Upload to GitHub Releases**
   - Script finds the MP3 file for the given date
   - Extracts duration and file size using `ffprobe`
   - Creates a GitHub Release tagged with the date
   - Uploads the MP3 as a release asset
   - If this is the first episode, also uploads cover art to an "assets" release

2. **Generate RSS Feed**
   - Scans all episodes in `episodes/` directory
   - Extracts metadata (duration, file size) from each MP3
   - Parses episode scripts to extract titles and descriptions
   - Generates a valid RSS 2.0 feed with iTunes tags
   - Saves to `feed.xml`

3. **Deploy RSS Feed**
   - Commits `feed.xml` to GitHub
   - Pushes to `main` branch of `antonber/paper-weights-podcast`
   - RSS feed becomes available at: `https://raw.githubusercontent.com/antonber/paper-weights-podcast/main/feed.xml`

## Episode URLs

After publishing, each episode is available at:
```
https://github.com/antonber/paper-weights-podcast/releases/download/YYYY-MM-DD/YYYY-MM-DD-podcast.mp3
```

## RSS Feed Structure

The generated feed includes:
- **Podcast metadata**: Title, description, category, language
- **Cover art**: Hosted on GitHub Releases
- **Episode items**: Each with title, description, enclosure URL, duration, pub date

### Episode Title Format
`Paper Weights — [Date] — [First Paper Title]`

Example: `Paper Weights — February 11, 2026 — Effective Reasoning Chains Reduce Intrinsic Dimensionality`

### Episode Descriptions
Auto-extracted from script files, listing all papers covered in bullet format.

## Testing the Pipeline

### Test 1: Publish a Single Episode
```bash
# Publish Feb 11 episode
./scripts/publish_episode.sh 2026-02-11
```

Expected output:
- ✓ Episode uploaded to GitHub Releases
- ✓ Cover art uploaded (first run only)
- ✓ RSS feed updated
- URLs printed at the end

### Test 2: Validate RSS Feed
```bash
# Download and inspect
curl https://raw.githubusercontent.com/antonber/paper-weights-podcast/main/feed.xml | head -100
```

Or use an online validator:
- [Cast Feed Validator](https://castfeedvalidator.com/)
- [Podbase RSS Validator](https://podba.se/validate/)

### Test 3: Test in a Podcast App

**Apple Podcasts (iOS):**
1. Open Apple Podcasts
2. Library → Edit → Add a Show by URL
3. Paste: `https://raw.githubusercontent.com/antonber/paper-weights-podcast/main/feed.xml`

**Overcast (iOS):**
1. Settings → Add URL
2. Paste RSS feed URL

**Pocket Casts:**
1. Discover → Search by URL
2. Enter RSS feed URL

### Test 4: Manually Regenerate RSS Feed
```bash
# If you need to regenerate without publishing
python3 scripts/generate_rss.py
```

## Spotify for Podcasters Integration

**⚠️ DO NOT do this yet — wait until testing is complete!**

Once the RSS feed is validated and tested in podcast apps:

1. Log in to [Spotify for Podcasters](https://podcasters.spotify.com)
2. Go to your podcast settings
3. Distribution → RSS Feed
4. Click "Import from RSS"
5. Enter: `https://raw.githubusercontent.com/antonber/paper-weights-podcast/main/feed.xml`
6. Spotify will validate and import all episodes
7. Future episodes will be automatically pulled when the RSS feed updates

**Important:** Once switched to RSS, Spotify will no longer accept manual uploads for this podcast.

## Troubleshooting

### "Release already exists"
The script will automatically delete and recreate the release. This is safe.

### "No podcast file found"
Check that the MP3 file exists at `episodes/YYYY-MM-DD-podcast.mp3`

### "ffprobe: command not found"
Install ffmpeg: `brew install ffmpeg`

### "gh: command not found"
Install GitHub CLI: `brew install gh`
Then authenticate: `gh auth login`

### RSS feed not updating
GitHub's raw CDN can take 5-10 minutes to update. Wait a bit and try again.

## Manual Operations

### Upload cover art only
```bash
gh release create assets \
  --repo antonber/paper-weights-podcast \
  --title "Podcast Assets" \
  --notes "Static assets for podcast" \
  ~/projects/arxiv-podcast/branding/cover-art.png
```

### Delete a release
```bash
gh release delete 2026-02-11 --repo antonber/paper-weights-podcast --yes
```

### View all releases
```bash
gh release list --repo antonber/paper-weights-podcast
```

## Automation Ideas

### Cron Integration (Future)
Add to daily podcast generation cron:
```bash
# After episode generation completes
cd ~/projects/arxiv-podcast
./scripts/publish_episode.sh $(date +%Y-%m-%d)
```

### GitHub Actions (Future)
Could set up a GitHub Action to auto-publish on push to episodes directory.

## File Checklist

Before publishing, ensure these files exist:
- ✓ `episodes/YYYY-MM-DD-podcast.mp3` - The episode audio
- ✓ `episodes/YYYY-MM-DD-script.md` - The episode script (for metadata extraction)
- ✓ `branding/cover-art.png` - Podcast cover art
- ✓ `scripts/publish_episode.sh` - Publishing script
- ✓ `scripts/generate_rss.py` - RSS generator

## RSS Feed URL

**Final RSS feed URL for Spotify/Apple/etc:**
```
https://raw.githubusercontent.com/antonber/paper-weights-podcast/main/feed.xml
```

Keep this URL handy — it's what you'll give to podcast platforms.
