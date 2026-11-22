"""Research trending GTA 6 funny/action videos via yt-dlp search (no API key, no quota).

Rules: GTA 6 only, recent, long enough to clip, high views preferred.
Excludes walkthrough/full-game/ending/cutscene/leak/story-spoiler titles.
Output: sources.json with up to 5 videos.
"""
import json, os, subprocess, sys

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

QUERIES = [
    "GTA 6 funny moments gameplay",
    "GTA 6 police chase gameplay",
    "GTA VI funny fails gameplay",
]
EXCLUDE = ["full game", "walkthrough", "ending", "cutscene", "leak", "story mode full",
           "no commentary full", "100%", "all missions", "movie"]
MIN_DUR, MAX_DUR = 240, 4 * 3600  # 4 min .. 4 h

def search(query, n=12):
    cmd = ["yt-dlp", "--socket-timeout", "30"] + yt_extra() + ["--flat-playlist",
           "--print", "%(id)s\t%(duration)s\t%(view_count)s\t%(upload_date)s\t%(channel)s\t%(title)s",
           f"ytsearch{n}:{query}"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    rows = []
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        vid, dur, views, date, chan, title = parts[0], parts[1], parts[2], parts[3], parts[4], "\t".join(parts[5:])
        try:
            dur = int(float(dur)) if dur not in ("NA", "None", "") else 0
            views = int(float(views)) if views not in ("NA", "None", "") else 0
        except ValueError:
            continue
        rows.append({"id": vid, "duration": dur, "views": views,
                     "upload_date": date, "channel": chan, "title": title,
                     "url": f"https://www.youtube.com/watch?v={vid}"})
    return rows

def main(out="sources.json", limit=5):
    seen, pool = set(), []
    for q in QUERIES:
        try:
            for v in search(q):
                if v["id"] in seen:
                    continue
                seen.add(v["id"])
                t = v["title"].lower()
                if any(x in t for x in EXCLUDE):
                    continue
                if not (MIN_DUR <= v["duration"] <= MAX_DUR):
                    continue
                pool.append(v)
        except Exception as e:
            print(f"search failed ({q}): {e}", file=sys.stderr)
    pool.sort(key=lambda v: v["views"], reverse=True)
    picks = pool[:limit]
    with open(out, "w") as f:
        json.dump(picks, f, indent=1)
    print(f"Wrote {len(picks)} sources to {out}")
    for v in picks:
        print(f" - {v['views']:>9} views | {v['duration']//60}m | {v['channel']} | {v['title'][:80]}")
    return picks

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "sources.json")
