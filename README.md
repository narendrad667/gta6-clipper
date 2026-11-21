# GTA6 Clipper — Funny/Action Shorts Autopilot

Free GitHub Actions workflow. Zero Muse tokens after setup.

## What it does (2x daily: 10:00 + 22:00 IST)
1. Research: yt-dlp search for GTA 6 funny/action videos (no API key, no quota).
2. Action scoring: motion (scene changes) + audio peaks + funny keywords.
   Talking-to-viewers segments are REJECTED (near-zero motion = reject).
3. Clip: best 42s window -> 9:16 Short, 2-line hook (first 3s), burned captions.
4. Upload (only when dry_run=false): private + publishAt schedule on narendradhakadai.
   Max 3 clips/run, 6/day (YouTube quota: 1600 units/upload, 10000/day/project).

## Safety defaults
- Workflow ships in DRY-RUN: schedule builds clips as artifacts, uploads nothing.
- Upload needs secrets YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN minted
  for the narendradhakadai channel in a SEPARATE Google project (Production mode),
  otherwise quota is shared with the What If autopilot (6/day total).

## Test manually
Actions -> GTA6 Funny Action Clips -> Run workflow -> dry_run=true, source_id=<video id>.
Download the gta6-clips artifact and check short_*.mp4 + frame_hook.jpg.

## Copyright note
Clips are other creators' gameplay. Rockstar allows own gameplay for non-commercial
use; YouTube reused-content rules still apply. No monetization guarantee.
