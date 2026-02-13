# Quick Start: Publishing Episodes

## Publish Today's Episode
```bash
cd ~/projects/arxiv-podcast
./scripts/publish_episode.sh $(date +%Y-%m-%d)
```

## Publish Specific Date
```bash
./scripts/publish_episode.sh 2026-02-11
```

## What Gets Published

✅ **Episode uploaded to:** `https://github.com/antonber/paper-weights-podcast/releases`  
✅ **RSS feed updated at:** `https://raw.githubusercontent.com/antonber/paper-weights-podcast/main/feed.xml`

## RSS Feed URL (for Spotify, Apple, etc.)
```
https://raw.githubusercontent.com/antonber/paper-weights-podcast/main/feed.xml
```

## Test in Podcast App

**Apple Podcasts:**
Library → Edit → Add a Show by URL → Paste RSS URL

**Overcast:**
Settings → Add URL → Paste RSS URL

**Pocket Casts:**
Discover → Search by URL → Enter RSS URL

## After Testing: Add to Spotify

1. Go to [Spotify for Podcasters](https://podcasters.spotify.com)
2. Settings → Distribution → RSS Feed
3. Import from RSS: `https://raw.githubusercontent.com/antonber/paper-weights-podcast/main/feed.xml`
4. Done! Future episodes auto-sync when RSS updates

## Files Involved

- `scripts/publish_episode.sh` - Main publishing script
- `scripts/generate_rss.py` - RSS feed generator
- `episodes/*.mp3` - Episode audio files
- `episodes/*.md` - Episode scripts (for metadata)
- `branding/cover-art.png` - Podcast artwork
- `feed.xml` - Generated RSS feed (auto-created)

## Troubleshooting

**Episode not found?**  
Check file exists: `ls episodes/YYYY-MM-DD-podcast.mp3`

**RSS not updating?**  
GitHub CDN takes 5-10 minutes to refresh. Be patient.

**Need to republish?**  
Script auto-deletes old release and recreates it. Safe to re-run.

---

📖 **Full guide:** See `PUBLISHING_GUIDE.md` for detailed documentation
