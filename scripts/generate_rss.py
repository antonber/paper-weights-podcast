#!/usr/bin/env python3
"""
Generate RSS 2.0 podcast feed for Paper Weights podcast.
Reads episode metadata from episodes directory and generates valid RSS feed.
Extracts rich titles and descriptions from episode scripts.
Includes arXiv paper links from digest files.
"""

import os
import re
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom
from extract_timestamps import extract_timestamps, get_paper_timestamps

REPO_URL = "https://github.com/antonber/paper-weights-podcast"
COVER_ART_URL = f"{REPO_URL}/releases/download/assets/cover-art.png"
DIGEST_DIR = Path.home() / "projects" / "arxiv-llm-digest" / "digests"

PODCAST_METADATA = {
    "title": "Paper Weights: Daily AI Research Briefing",
    "description": "Every morning, two hosts break down the AI papers that actually matter — one explains the science, one asks where the money is. Hundreds of papers filtered down to the dozen or so that could become products, disrupt markets, or change how you build. 15 minutes. No filler.",
    "author": "Paper Weights",
    "email": "podcast@paperweights.ai",
    "category": "Technology",
    "language": "en",
    "explicit": "no",
    "link": "https://github.com/antonber/paper-weights-podcast",
}


def get_audio_duration(mp3_path):
    """Extract duration from MP3 using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", mp3_path],
            capture_output=True, text=True, check=True
        )
        duration_seconds = float(result.stdout.strip())
        hours = int(duration_seconds // 3600)
        minutes = int((duration_seconds % 3600) // 60)
        seconds = int(duration_seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    except Exception as e:
        print(f"Warning: Could not extract duration from {mp3_path}: {e}", file=sys.stderr)
        return "00:15:00"


def get_file_size(mp3_path):
    """Get file size in bytes."""
    return os.path.getsize(mp3_path)


def load_digest_papers(date_str):
    """
    Load paper titles and arXiv links from the digest file for a given date.
    Returns list of (title, arxiv_url) tuples.
    """
    digest_file = DIGEST_DIR / f"{date_str}.md"
    if not digest_file.exists():
        return []

    try:
        content = digest_file.read_text()
    except Exception:
        return []

    papers = []
    lines = content.split('\n')

    # Pattern 1: "#### N. Title" followed by "**arXiv**: url" or "| [arXiv](url)"
    # Pattern 2: "**N. Title** — Author | [arXiv](url)"
    title_pattern = re.compile(r'^#{1,4}\s*\d+\.\s*(.+?)(?:\s*$)', re.MULTILINE)
    numbered_bold = re.compile(r'^\*\*(\d+)\.\s*(.+?)\*\*')
    arxiv_url_pattern = re.compile(r'(?:arxiv\.org/abs/[\w.]+)')

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Format: #### 1. Paper Title
        title_m = re.match(r'^#{1,4}\s*\d+\.\s*(.+)', line)
        if title_m:
            title = title_m.group(1).strip()
            # Look ahead for arXiv link in next 5 lines
            arxiv_url = None
            for j in range(i + 1, min(i + 6, len(lines))):
                url_m = re.search(r'(https?://arxiv\.org/abs/[\w.]+)', lines[j])
                if url_m:
                    arxiv_url = url_m.group(1)
                    break
            if arxiv_url:
                papers.append((title, arxiv_url))
            i += 1
            continue

        # Format: **1. Title** — Author | [arXiv](url)
        bold_m = numbered_bold.match(line)
        if bold_m:
            title = bold_m.group(2).strip().rstrip('*')
            url_m = re.search(r'(https?://arxiv\.org/abs/[\w.]+)', line)
            if url_m:
                papers.append((title, url_m.group(1)))
            else:
                # Check next few lines
                for j in range(i + 1, min(i + 4, len(lines))):
                    url_m = re.search(r'(https?://arxiv\.org/abs/[\w.]+)', lines[j])
                    if url_m:
                        papers.append((title, url_m.group(1)))
                        break
            i += 1
            continue

        i += 1

    return papers


def match_paper_to_digest(paper_name, digest_papers):
    """
    Fuzzy match a paper name from the script to a digest entry.
    Returns arxiv_url or None.
    """
    if not digest_papers:
        return None

    paper_lower = paper_name.lower().strip()

    # Direct substring match
    for title, url in digest_papers:
        title_lower = title.lower()
        if paper_lower in title_lower or title_lower in paper_lower:
            return url
        # Check significant words overlap
        paper_words = set(w for w in paper_lower.split() if len(w) > 3)
        title_words = set(w for w in title_lower.split() if len(w) > 3)
        if paper_words and title_words:
            overlap = paper_words & title_words
            if len(overlap) >= min(2, len(paper_words)):
                return url

    return None


def extract_papers_from_script(script_path):
    """
    Extract paper names from a script file.
    Returns (lead_paper, deep_dives, quick_hits)
    """
    try:
        with open(script_path, 'r') as f:
            content = f.read()
    except Exception:
        return None, [], []

    lines = content.split('\n')
    deep_dives = []
    quick_hits = []

    # --- Format 1a: ### SEGMENT: PAPER N — Title ---
    segment_pattern = re.compile(r'###\s*SEGMENT:\s*PAPER\s*\d+\s*[—–-]\s*(.+)', re.IGNORECASE)
    for line in lines:
        m = segment_pattern.match(line.strip())
        if m:
            deep_dives.append(m.group(1).strip())

    if deep_dives:
        return deep_dives[0], deep_dives, []

    # --- Format 1b: ## Paper N: Title ---
    paper_header = re.compile(r'##\s*Paper\s*\d+:\s*(.+?)(?:\s*\(\d+\s*min\))?$', re.IGNORECASE)
    for line in lines:
        m = paper_header.match(line.strip())
        if m:
            deep_dives.append(m.group(1).strip())
    if deep_dives:
        # Also check for Quick Hits section
        in_quick = False
        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith('## quick hit'):
                in_quick = True
                continue
            if in_quick and stripped.startswith('## '):
                break
            if in_quick and (stripped.startswith('**Alex**:') or stripped.startswith('**Maya**:')):
                dialogue = stripped.split(':', 1)[1].strip()
                quoted = re.findall(r'["""]([^"""]{15,80})["""]', dialogue)
                for q in quoted:
                    cap_words = sum(1 for w in q.split() if w[0].isupper())
                    if cap_words >= 2 and q not in quick_hits:
                        quick_hits.append(q)
        return deep_dives[0], deep_dives, quick_hits

    # --- Format 1c: ## Deep Dive N: Title ---
    dive_header = re.compile(r'##\s*Deep Dive\s*\d+(?:\s*\([^)]*\))?:\s*(.+)', re.IGNORECASE)
    for line in lines:
        m = dive_header.match(line.strip())
        if m:
            deep_dives.append(m.group(1).strip())

    # Quick Hits from dialogue in ## Quick Hits section
    in_quick = False
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith('## quick hit'):
            in_quick = True
            continue
        if in_quick and stripped.startswith('## '):
            break
        if in_quick and (stripped.startswith('**Alex**:') or stripped.startswith('**Maya**:')):
            dialogue = stripped.split(':', 1)[1].strip()
            quoted = re.findall(r'["""]([^"""]{15,80})["""]', dialogue)
            for q in quoted:
                lower_q = q.lower()
                if any(phrase in lower_q for phrase in [
                    "we can", "you're", "i'm", "that's", "it's", "just ",
                    "wait,", "hold on", "let me", "is this", "said it",
                    "real ", "more ", "need to", "workload", "agentic w",
                ]):
                    continue
                cap_words = sum(1 for w in q.split() if w[0].isupper())
                if cap_words >= 2 and q not in quick_hits:
                    quick_hits.append(q)

    if deep_dives:
        return deep_dives[0], deep_dives, quick_hits

    # --- Format 2: Freeform dialogue — extract quoted paper titles ---
    section = None
    paper_title_pattern = re.compile(r'["""]([^"""]{15,80})["""]')

    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith('## deep dive'):
            section = 'deep'
            continue
        elif stripped.lower().startswith('## quick hit'):
            section = 'quick'
            continue
        elif stripped.startswith('## ') and section:
            section = None
            continue

        if not section:
            continue

        if stripped.startswith('**Alex**:') or stripped.startswith('**Maya**:'):
            dialogue = stripped.split(':', 1)[1].strip()
            quoted = paper_title_pattern.findall(dialogue)
            for q in quoted:
                target = deep_dives if section == 'deep' else quick_hits
                lower_q = q.lower()
                if any(phrase in lower_q for phrase in [
                    "we can", "you're", "i'm", "that's", "it's", "just ",
                    "wait,", "hold on", "let me", "is this", "said it",
                    "real ", "more ", "need to", "workload", "agentic w",
                ]):
                    continue
                cap_words = sum(1 for w in q.split() if w[0].isupper())
                if cap_words < 2:
                    continue
                if q not in target:
                    target.append(q)

    lead = deep_dives[0] if deep_dives else None
    return lead, deep_dives, quick_hits


def extract_papers_from_digest(date_str):
    """Fallback: extract papers directly from the arXiv digest file."""
    digest_file = DIGEST_DIR / f"{date_str}.md"
    if not digest_file.exists():
        return None, [], []

    content = digest_file.read_text()
    deep_dives = []
    quick_hits = []

    for line in content.split('\n'):
        # Format: ### N. Title
        m = re.match(r'^###\s*(\d+)\.\s*(.+)', line.strip())
        if m:
            num = int(m.group(1))
            title = m.group(2).strip()
            if num <= 7:
                deep_dives.append(title)
            else:
                quick_hits.append(title)
            continue
        # Format: **N. Title** — Author | [arXiv](url)
        m = re.match(r'^\*\*(\d+)\.\s*(.+?)\*\*', line.strip())
        if m:
            num = int(m.group(1))
            title = m.group(2).strip().rstrip('*')
            if num <= 7:
                if title not in deep_dives:
                    deep_dives.append(title)
            else:
                if title not in quick_hits:
                    quick_hits.append(title)

    lead = deep_dives[0] if deep_dives else None
    return lead, deep_dives, quick_hits


def build_episode_title(script_path, date_formatted, date_str=None):
    """Build episode title — just the lead paper topic, no date or show name."""
    lead, deep_dives, quick_hits = extract_papers_from_script(script_path) if script_path else (None, [], [])

    # Fallback to digest if script parsing fails
    if not lead and date_str:
        lead, _, _ = extract_papers_from_digest(date_str)

    if lead:
        lead = lead.strip().rstrip('.')
        if len(lead) > 80:
            lead = lead[:77] + "..."
        return lead

    return "AI Research Briefing"


def build_episode_description(script_path, date_str, mp3_path=None):
    """Build a rich episode description: engaging summary paragraph + paper list with arXiv links + inline timestamps."""
    lead, deep_dives, quick_hits = extract_papers_from_script(script_path) if script_path else (None, [], [])

    # Load digest for arXiv links
    digest_papers = load_digest_papers(date_str)

    # Load paper timestamps if available
    paper_ts = {}
    if script_path and mp3_path:
        try:
            paper_ts = get_paper_timestamps(mp3_path, script_path, date_str)
        except Exception as e:
            print(f"Warning: Could not extract timestamps for {date_str}: {e}", file=sys.stderr)

    deep_dive_ts_list = paper_ts.get('__deep_dive_timestamps__', [])
    quick_hits_ts = paper_ts.get('__quick_hits__')

    parts = []

    def format_paper(name, index=None, is_quick_hit=False, is_first_quick_hit=False):
        ts = None
        if is_first_quick_hit and quick_hits_ts:
            ts = quick_hits_ts
        elif not is_quick_hit and index is not None and index < len(deep_dive_ts_list):
            ts = deep_dive_ts_list[index]
        url = match_paper_to_digest(name, digest_papers)
        prefix = f"[{ts}] " if ts else ""
        if url:
            return f"• {prefix}{name} — {url}"
        return f"• {prefix}{name}"

    # Fallback to digest if script parsing fails
    if not deep_dives:
        lead, deep_dives, quick_hits = extract_papers_from_digest(date_str)

    # Build engaging summary paragraph
    total_papers = len(deep_dives) + len(quick_hits)
    if deep_dives:
        if lead and len(deep_dives) > 1:
            other_topics = [p for p in deep_dives[1:3]]
            summary = f"Today's episode dives deep into {lead}"
            if other_topics:
                summary += f", along with {', '.join(other_topics)}"
            if quick_hits:
                summary += f". Plus {len(quick_hits)} quick hits covering the rest of what dropped on arXiv."
            else:
                summary += "."
            summary += f" Alex breaks down the technical details while Maya asks the hard questions about what actually matters for building products and making money. {total_papers} papers, zero filler."
        elif lead:
            summary = f"Today we're breaking down {lead}. Alex explains the science, Maya asks where the money is. {total_papers} papers that could change how you build."
        else:
            summary = f"Alex and Maya break down {total_papers} papers from today's arXiv drop — the ones that actually matter for building products, disrupting markets, or changing how AI works."
        parts.append(summary)
    else:
        parts.append("Alex and Maya break down the AI papers that actually matter — one explains the science, one asks where the money is. No filler.")

    parts.append("")

    # Paper listings with arXiv links and inline timestamps
    if deep_dives:
        if quick_hits:
            parts.append("Deep Dives:")
            for i, p in enumerate(deep_dives):
                parts.append(format_paper(p, index=i))
            parts.append("")
            parts.append("Quick Hits:")
            for i, p in enumerate(quick_hits):
                parts.append(format_paper(p, is_quick_hit=True, is_first_quick_hit=(i == 0)))
        else:
            parts.append("Papers discussed:")
            for i, p in enumerate(deep_dives):
                parts.append(format_paper(p, index=i))

    return "\n".join(parts)


def find_best_mp3(episodes_path, date_str):
    """Pick the best MP3 for a date (prefer -v2)."""
    v2 = episodes_path / f"{date_str}-podcast-v2.mp3"
    base = episodes_path / f"{date_str}-podcast.mp3"
    if v2.exists():
        return v2
    if base.exists():
        return base
    return None


def find_best_script(episodes_path, date_str):
    """Find the best script file for a date (prefer -v2)."""
    v2 = episodes_path / f"{date_str}-script-v2.md"
    base = episodes_path / f"{date_str}-script.md"
    if v2.exists():
        return v2
    if base.exists():
        return base
    return None


def create_rss_feed(episodes_dir, output_file):
    """Generate RSS 2.0 podcast feed."""

    rss = ET.Element("rss", version="2.0")
    rss.set("xmlns:itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
    rss.set("xmlns:content", "http://purl.org/rss/1.0/modules/content/")

    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = PODCAST_METADATA["title"]
    ET.SubElement(channel, "description").text = PODCAST_METADATA["description"]
    ET.SubElement(channel, "link").text = PODCAST_METADATA["link"]
    ET.SubElement(channel, "language").text = PODCAST_METADATA["language"]

    ET.SubElement(channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}author").text = PODCAST_METADATA["author"]
    ET.SubElement(channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}explicit").text = PODCAST_METADATA["explicit"]

    itunes_category = ET.SubElement(channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}category")
    itunes_category.set("text", PODCAST_METADATA["category"])

    itunes_image = ET.SubElement(channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}image")
    itunes_image.set("href", COVER_ART_URL)

    episodes_path = Path(episodes_dir)
    mp3_files = sorted(episodes_path.glob("*-podcast*.mp3"), reverse=True)

    seen_dates = set()
    episode_count = 0

    for mp3_file in mp3_files:
        filename = mp3_file.stem
        date_str = "-".join(filename.split("-")[:3])

        if date_str in seen_dates:
            continue

        best_mp3 = find_best_mp3(episodes_path, date_str)
        if not best_mp3:
            continue

        seen_dates.add(date_str)

        try:
            episode_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print(f"Warning: Could not parse date from {mp3_file.name}, skipping", file=sys.stderr)
            continue

        script_file = find_best_script(episodes_path, date_str)

        duration = get_audio_duration(str(best_mp3))
        file_size = get_file_size(str(best_mp3))
        date_formatted = episode_date.strftime("%B %d, %Y")

        if script_file:
            title = build_episode_title(str(script_file), date_formatted, date_str=date_str)
            description = build_episode_description(str(script_file), date_str, str(best_mp3))
        else:
            title = build_episode_title(None, date_formatted, date_str=date_str)
            description = build_episode_description(None, date_str, str(best_mp3))

        episode_url = f"{REPO_URL}/releases/download/{date_str}/{best_mp3.name}"

        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = title
        ET.SubElement(item, "description").text = description
        ET.SubElement(item, "link").text = episode_url
        ET.SubElement(item, "guid").text = episode_url
        ET.SubElement(item, "pubDate").text = episode_date.strftime("%a, %d %b %Y 09:00:00 -0600")

        enclosure = ET.SubElement(item, "enclosure")
        enclosure.set("url", episode_url)
        enclosure.set("length", str(file_size))
        enclosure.set("type", "audio/mpeg")

        ET.SubElement(item, "{http://www.itunes.com/dtds/podcast-1.0.dtd}duration").text = duration

        episode_count += 1
        print(f"Added episode: {title} ({duration}, {file_size} bytes)")

    # Pretty print XML
    xml_str = minidom.parseString(ET.tostring(rss)).toprettyxml(indent="  ")

    with open(output_file, 'w') as f:
        f.write(xml_str)

    print(f"\nRSS feed generated: {output_file}")
    print(f"Episodes included: {episode_count}")


if __name__ == "__main__":
    project_dir = Path(__file__).parent.parent
    episodes_dir = project_dir / "episodes"
    output_file = project_dir / "feed.xml"

    create_rss_feed(episodes_dir, output_file)
