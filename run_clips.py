"""Orchestrator: research -> action-score -> clip -> (upload | dry-run artifacts).

Usage:
  python run_clips.py --dry-run --max-clips 3
  python run_clips.py --source-id dUYIMa2ifWM --dry-run --max-clips 1   (local test)
Schedule slots (IST): run at 10:00 -> publish 12:00/15:00/18:00; run at 22:00 -> next day 07:00/09:00/11:00.
"""
import argparse, datetime, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import research, action_score, clip as clipmod

def sh(cmd, **kw):
    print("+", " ".join(cmd)); subprocess.run(cmd, check=True, **kw)

def yt_extra():
    """Bot-check bypass for datacenter IPs: try mobile/TV player clients first.
    Optional cookies: set YT_COOKIES_FILE to a Netscape cookies.txt path."""
    args = ["--extractor-args", "youtube:player_client=mweb,web,web_safari,android,ios,tv"]
    pot = os.environ.get("YT_POT_BASE_URL", "")
    if pot:
        args += ["--extractor-args", f"youtubepot-bgutilhttp:base_url={pot}"]
    cf = os.environ.get("YT_COOKIES_FILE", "")
    if cf and os.path.exists(cf):
        args += ["--cookies", cf]
    return args

def duration_of(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(r.stdout.strip())

def process_source(src, workdir, idx):
    os.makedirs(workdir, exist_ok=True)
    os.chdir(workdir)
    url = src["url"]
    # 1) low-res full video for scoring (360p keeps it small/fast)
    sh(["yt-dlp", "--socket-timeout", "30"] + yt_extra() + ["-f",
        "bestvideo[height<=360]+bestaudio/best[height<=360]/best",
        "--merge-output-format", "mp4", "--force-overwrite", "-o", "score.mp4", url], timeout=1200)
    sh(["ffmpeg", "-y", "-i", "score.mp4", "-ar", "16000", "-ac", "1", "score.wav"], timeout=600)
    dur = duration_of("score.mp4")
    transcript = action_score.transcribe("score.wav")
    json.dump(transcript, open("transcript.json", "w"), indent=1)
    best, ranked = action_score.best_window("score.mp4", "score.wav", transcript, dur)
    json.dump(ranked, open("scores.json", "w"), indent=1)
    if best is None:
        print(f"[{src['id']}] no action window (all talking/static) — skipped")
        return None
    print(f"[{src['id']}] BEST {best['start']}-{best['end']} score={best['score']}")
    # 2) 720p segment + Short edit
    clipmod.download_segment(url, best["start"], best["end"], "segment.mp4")
    hook1, hook2 = clipmod.hook_from_window(transcript, best["start"], best["end"])
    out = f"short_{idx}.mp4"
    clipmod.make_short("segment.mp4", transcript, best["start"], best["end"], hook1, hook2, out)
    meta = {"source": src, "window": best, "hook": [hook1, hook2], "file": out}
    json.dump(meta, open("result.json", "w"), indent=1)
    return meta

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="build only, never upload")
    ap.add_argument("--max-clips", type=int, default=3)
    ap.add_argument("--source-id", default=None, help="test a single video id")
    args = ap.parse_args()
    base = os.path.dirname(os.path.abspath(__file__))
    if args.source_id:
        sources = [{"id": args.source_id, "url": f"https://www.youtube.com/watch?v={args.source_id}",
                    "title": "manual test", "channel": "manual", "views": 0, "duration": 0}]
    else:
        sources = research.main(os.path.join(base, "sources.json"), limit=5)
    made, failed, skipped = [], 0, 0
    for i, src in enumerate(sources):
        if len(made) >= args.max_clips:
            break
        try:
            meta = process_source(src, os.path.join(base, f"work_{i}"), i)
            if meta:
                made.append(meta)
            else:
                skipped += 1
        except Exception as e:
            failed += 1
            print(f"source {src['id']} failed: {e}", file=sys.stderr)
        os.chdir(base)
    print(f"Built {len(made)} clips (dry_run={args.dry_run}) failed={failed} skipped={skipped}")
    # Honest failure: every attempted source errored (e.g. YouTube bot-check),
    # or an explicit single-video test built nothing. All-rejected (skipped) stays OK.
    if not made and (failed > 0 and skipped == 0 or args.source_id):
        print("ERROR: no clips built and downloads failed — see log above.", file=sys.stderr)
        sys.exit(1)
    if args.dry_run:
        print("DRY RUN: no upload. Clips are in work_*/short_*.mp4 (workflow artifacts).")
        return
    # Upload with staggered schedule (UTC publishAt). Morning run -> same day, night run -> next morning.
    import upload as up
    now = datetime.datetime.now(datetime.timezone.utc)
    for j, meta in enumerate(made):
        slot = now + datetime.timedelta(hours=2 + j * 3)
        publish_at = slot.strftime("%Y-%m-%dT%H:%M:%SZ")
        path = os.path.join(base, f"work_{j}", meta["file"])
        title = f"{meta['hook'][0]} #shorts #gta6"
        desc = (f"GTA 6 funny/action moment. Source: {meta['source']['url']}\n"
                f"#gta6 #gtavi #shorts #gaming #funny")
        vid, url = up.upload_short(path, title, desc, ["gta6", "gtavi", "shorts", "gaming"], publish_at)
        print(f"Uploaded {url} publishAt={publish_at}")

if __name__ == "__main__":
    main()
