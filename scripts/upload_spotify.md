# Spotify Upload Automation - Browser Flow

## Prerequisites
- OpenClaw browser (profile=openclaw) logged into Spotify for Creators
- Session cookies persist between runs (no re-login needed usually)

## Flow
1. Navigate to: https://creators.spotify.com/pod/show/7wKNKAabIY3Wl55BApqSvM/episode/wizard
2. Upload MP3 via file input (selector: input[type=file])
3. Wait for "Details" page (upload processing)
4. Fill Title field
5. Fill Description field (rich text editor)
6. Click Next → Review page
7. Select "Now" radio for publish date (use evaluate: click radio with value='now')
8. Click Publish
9. Wait for "Episode published!" dialog
10. Click Done

## Title Format
"[Lead Paper Topic] — Paper Weights Feb DD, 2026"

## Description Format (HTML mode)
Toggle the HTML checkbox ON before editing description. Use the HTML textarea (not the rich text editor).
Type raw HTML — the Slate editor doesn't respond to innerHTML changes, but the HTML textarea does.

Template:
```html
<p>Every morning, two hosts break down the AI papers that actually matter — one explains the science, one asks where the money is.</p>
<p><br></p>
<p><b>Today's Deep Dives:</b></p>
<p>1. <a href="https://arxiv.org/abs/XXXX.XXXXX">Paper Title</a></p>
...
<p><br></p>
<p><b>Quick Hits:</b></p>
<p>8. <a href="https://arxiv.org/abs/XXXX.XXXXX">Paper Title</a></p>
...
```

Key: Extract paper titles and arXiv links from the digest file. Include ALL papers covered in the episode.

## Editing existing description
1. Navigate to episode details page
2. Toggle HTML checkbox (evaluate: click label containing 'HTML')
3. Select all in HTML textarea, type new HTML content
4. Click Save button (evaluate: find button with text 'Save', click it)

## Auth Note
If session expires, need email OTP login:
- Email: antonber@gmail.com
- OTP sent to email, 6-digit code
- Use click+type slowly pattern for OTP fields (see otp-input skill)

## Show ID
7wKNKAabIY3Wl55BApqSvM
