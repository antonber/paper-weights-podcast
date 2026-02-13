# Paper Weights: Daily AI Research Briefing

## Overview
AI-generated daily podcast that breaks down the most important AI research papers from arXiv. Two hosts discuss each paper through a VC/startup lens — one explains the science, one asks "where's the money?"

## Branding
- **Name:** Paper Weights: Daily AI Research Briefing
- **Description:** Every morning, two hosts break down the AI papers that actually matter — one explains the science, one asks where the money is. Hundreds of papers filtered down to the dozen or so that could become products, disrupt markets, or change how you build. 15 minutes. No filler.
- **Cover Art:** `branding/cover-art.png` (Option 2 — navy blue, balance scale with papers vs gold weights)
- **All options:** `branding/001-*.png`, `branding/002-*.png`, `branding/003-*.png`

## Hosts / Voices
- **Alex** (Host A — Technical Researcher): Chris voice (iP95p4xoKVk53GoZ742B) — Charming, Down-to-Earth
- **Maya** (Host B — VC Brain): Laura voice (FGY2WhTYpPnrIDTdsKH5) — Enthusiast, Quirky Attitude
- **Model:** eleven_v3 (ElevenLabs latest, most expressive)
- **ElevenLabs Plan:** Creator ($22/mo, 100K characters — covers daily episodes)

## Pipeline
1. **arXiv Digest** (existing cron, 8 AM CT) → selects top 15-20 papers from hundreds
2. **Fetch Full Abstracts** → arXiv API for top 7-10 papers (more depth than digest summaries)
3. **Generate Script** → LLM writes two-host discussion with VC lens
4. **TTS Generation** → ElevenLabs v3 with Chris + Laura voices, ~36 dialogue segments
5. **Concatenation** → ffmpeg joins segments with 400ms silence gaps
6. **Publishing** → `publish_episode.sh` uploads to GitHub Releases + updates RSS feed
7. **Distribution** → Spotify for Podcasters polls RSS feed → auto-distributes to all platforms

## File Structure
```
~/projects/arxiv-podcast/
├── README.md                    # This file
├── feed.xml                     # Generated RSS feed (auto-created)
├── branding/
│   ├── cover-art.png           # Selected thumbnail (Option 2)
│   ├── 001-*.png               # Thumbnail option 1
│   ├── 002-*.png               # Thumbnail option 2
│   ├── 003-*.png               # Thumbnail option 3
│   └── index.html              # Gallery
├── episodes/
│   ├── YYYY-MM-DD-script.md    # Episode scripts
│   └── YYYY-MM-DD-podcast.mp3  # Generated episodes
└── scripts/
    ├── generate_episode.sh     # Main episode generation script
    ├── generate_podcast.py     # Podcast script generator
    ├── parse_and_tts.py        # TTS synthesis
    ├── add_chapters.py         # Chapter marker tool
    ├── publish_episode.sh      # 📤 Upload to GitHub + update RSS
    └── generate_rss.py         # RSS feed generator
```

## Script Format
Scripts use markdown with speaker labels:
```
**Alex**: Technical explanation of the paper...
**Maya**: VC/startup angle and commercial implications...
```

## Technical Details
- **sag CLI flags:** `-v <voice_id> -o <output.mp3> --model-id eleven_v3 "text"`
- **DO NOT use `--model`** — the correct flag is `--model-id`
- **Segment chunking:** Max 2500 chars per TTS call, split at sentence boundaries
- **Silence gaps:** 400ms between speakers (ffmpeg anullsrc)
- **Concatenation:** ffmpeg -f concat
- **Output format:** MP3 44100Hz 128kbps
- **Typical episode:** ~36 segments, ~12-13 minutes, ~9-10 MB

## Voices Tested (for reference)
All tested on eleven_v3. Anton's rankings:
- ✅ **Chris + Laura** (selected)
- Matilda — "broken" on v3
- Daniel + Alice — used in pilot v1, decent but less natural
- Eric + Jessica — tested, not selected
- Roger + Matilda — tested, not selected
- Sarah, Bella, Lily, River — tested as Laura alternatives, not selected

## Distribution: Automated RSS + GitHub Hosting

**Solution:** RSS feed hosted on GitHub, episodes on GitHub Releases (free, reliable, unlimited bandwidth).

### Architecture
1. **MP3 Hosting:** GitHub Releases on [`paper-weights-podcast`](https://github.com/antonber/paper-weights-podcast) repo
   - Each episode is a release tagged with date (e.g., `2026-02-09`)
   - Cover art stored in `assets` release
   - Free, no bandwidth limits, stable URLs

2. **RSS Feed:** Generated RSS 2.0 feed with iTunes tags
   - Hosted at: `https://raw.githubusercontent.com/antonber/paper-weights-podcast/main/feed.xml`
   - Auto-generated from episodes directory
   - Includes all required podcast metadata (duration, file size, episode descriptions)

3. **Publishing Script:** `scripts/publish_episode.sh YYYY-MM-DD`
   - Uploads MP3 to GitHub Releases
   - Extracts metadata (duration, file size) via ffprobe
   - Regenerates RSS feed with new episode
   - Pushes updated feed to GitHub

### Usage

**Publish a new episode:**
```bash
cd ~/projects/arxiv-podcast
./scripts/publish_episode.sh 2026-02-11
```

**Manually regenerate RSS feed:**
```bash
python3 scripts/generate_rss.py
```

**RSS Feed URL for Spotify/Apple:**
```
https://raw.githubusercontent.com/antonber/paper-weights-podcast/main/feed.xml
```

### Episode Metadata
- **Title format:** `Paper Weights — [Date] — [Lead Paper Topic]`
- **Descriptions:** Auto-extracted from script files (lists papers covered)
- **Pub date:** 9:00 AM CST on episode date
- **Category:** Technology
- **Explicit:** No
- **Language:** English

### Spotify Integration
**Once RSS feed is tested and validated:**
1. Go to [Spotify for Podcasters](https://podcasters.spotify.com)
2. Settings → Distribution → RSS Feed
3. Import from RSS: `https://raw.githubusercontent.com/antonber/paper-weights-podcast/main/feed.xml`
4. Spotify will pull episodes from RSS automatically

**DO NOT switch yet** — test the RSS feed in a podcast app first to confirm it works.

## Cron Integration (TODO)
Add podcast generation step after arXiv digest:
1. arXiv digest runs at 8 AM CT (existing)
2. Podcast generator runs at ~8:30 AM CT (new)
3. Upload to host / send via Telegram

## Character Usage
- Each episode: ~12,000 characters
- ElevenLabs Creator plan: 100,000 chars/month
- Capacity: ~8 episodes/month comfortably (with buffer for voice tests)
- If daily (30 eps/month = 360K chars): would need Scale plan ($99/mo, 500K chars)

**IMPORTANT NOTE:** Creator plan (100K chars) may NOT be enough for daily episodes. 
Need to check: does eleven_v3 count characters differently? May need Scale plan for true daily cadence.
