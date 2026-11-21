"""Build one 9:16 Short from a scored window: hook (2 lines) + burned captions."""
import json, os, subprocess

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def ts(sec):
    m, s = divmod(int(sec), 60); h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}"

def ass_time(sec):
    h = int(sec // 3600); m = int((sec % 3600) // 60); s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def download_segment(url, start, end, out):
    cmd = ["yt-dlp", "--socket-timeout", "30",
           "--download-sections", f"*{ts(start)}-{ts(end)}",
           "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best",
           "--merge-output-format", "mp4", "--force-overwrite", "-o", out, url]
    subprocess.run(cmd, check=True, timeout=600)

def build_ass(transcript, start, end, ass_path):
    dur = end - start
    lines = []
    for s in transcript:
        if s["end"] <= start or s["start"] >= end:
            continue
        cs = max(0.0, s["start"] - start); ce = min(dur, s["end"] - start)
        txt = s["text"].replace("\n", " ").strip()
        if txt:
            lines.append(f"Dialogue: 0,{ass_time(cs)},{ass_time(ce)},Cap,,0,0,0,,{txt}")
    with open(ass_path, "w") as f:
        f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
                "[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                "Style: Cap,DejaVu Sans,52,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,4,1,2,40,40,320,1\n\n"
                "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        f.write("\n".join(lines) + "\n")
    return len(lines)

def make_short(segment, transcript, start, end, hook1, hook2, out):
    ass = os.path.abspath("clip.ass")
    n = build_ass(transcript, start, end, ass)
    print(f"captions: {n} cues")
    def esc(t):
        return t.replace(":", r"\:").replace("'", r"\'")
    vf = (f"crop=ih*9/16:ih,scale=1080:1920:flags=lanczos,setsar=1,"
          f"drawtext=fontfile={FONT}:text='{esc(hook1)}':fontsize=56:fontcolor=yellow:"
          f"borderw=3:bordercolor=black:box=1:boxcolor=black@0.55:boxborderw=14:"
          f"x=(w-text_w)/2:y=150:enable='lt(t,3)',"
          f"drawtext=fontfile={FONT}:text='{esc(hook2)}':fontsize=56:fontcolor=yellow:"
          f"borderw=3:bordercolor=black:box=1:boxcolor=black@0.55:boxborderw=14:"
          f"x=(w-text_w)/2:y=240:enable='lt(t,3)',"
          f"subtitles={ass}")
    cmd = ["ffmpeg", "-y", "-i", segment, "-vf", vf,
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-r", "30",
           "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True, timeout=900)
    # preview frames for manual check (hook + mid)
    for at, name in [(2, "frame_hook.jpg"), (20, "frame_mid.jpg")]:
        subprocess.run(["ffmpeg", "-y", "-ss", str(at), "-i", out, "-frames:v", "1", name],
                       capture_output=True, timeout=120)
    return out

def hook_from_window(transcript, start, end):
    """Simple rule-based hook (no API needed). Gemini can replace this later."""
    texts = " ".join(s["text"] for s in transcript if s["end"] > start and s["start"] < end).lower()
    if "police" in texts or "chase" in texts:
        return ("GTA 6 me Police Chase!", "Dekho kya hua!")
    if "crash" in texts or "takkar" in texts:
        return ("GTA 6 me Badi Takkar!", "Dekho kya hua!")
    if "haha" in texts or "lol" in texts:
        return ("GTA 6 Funny Moment!", "Hasna mana hai!")
    return ("GTA 6 Action Moment!", "Dekho kya hua!")
