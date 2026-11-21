"""Score 40s windows for FUNNY/ACTION only. Talking-to-viewers windows are rejected.

Score = motion (scene changes) + audio peaks (crash/scream/laugh) + funny keywords
        - talking penalty (viewer-chat phrases + low motion + continuous speech).
A window with near-zero motion is rejected even if the streamer talks a lot.
This is the fix for the rejected test clip (streamer standing and chatting).
"""
import json, re, subprocess

FUNNY = ["haha", "lol", "oh my god", "omg", "what the", "bro", "police", "chase",
         "crash", "wow", "let's go", "oh no", "arre", "bhai", "takkar", "bhag"]
TALKING = ["comment", "subscribe", "hello guys", "welcome back", "food is here",
           "headphones", "people are not coming", "i am telling you", "you guys comment",
           "like and subscribe", "follow me", "my daily life"]
WIN, STEP = 42, 14  # window seconds, slide seconds

def scene_times(video):
    """Timestamps with strong scene/motion change."""
    cmd = ["ffmpeg", "-i", video, "-vf", "select='gt(scene,0.28)',metadata=print",
           "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    times = [float(x) for x in re.findall(r"pts_time:([0-9.]+)", r.stderr)]
    return times

def audio_peaks(wav, dur):
    """Max volume per 10s chunk -> list of (t, max_db)."""
    peaks = []
    t = 0
    while t < dur:
        r = subprocess.run(["ffmpeg", "-ss", str(t), "-t", "10", "-i", wav,
                            "-af", "volumedetect", "-f", "null", "-"],
                           capture_output=True, text=True, timeout=120)
        m = re.search(r"max_volume:\s*(-?[0-9.]+) dB", r.stderr)
        peaks.append((t, float(m.group(1)) if m else -60.0))
        t += 10
    return peaks

def transcribe(wav):
    from faster_whisper import WhisperModel
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segs, info = model.transcribe(wav, beam_size=5, vad_filter=True)
    out = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
           for s in segs]
    print(f"transcript: lang={info.language} segments={len(out)}")
    return out

def score_windows(video, wav, transcript, duration):
    scenes = scene_times(video)
    peaks = dict(audio_peaks(wav, duration))
    print(f"scene-changes={len(scenes)} audio-chunks={len(peaks)}")
    results = []
    t = 0
    while t + WIN <= duration:
        end = t + WIN
        motion = sum(1 for s in scenes if t <= s < end)
        chunk_peaks = [v for (ct, v) in peaks.items() if t <= ct < end]
        peak = max(chunk_peaks) if chunk_peaks else -60.0
        texts = [s["text"].lower() for s in transcript if s["end"] > t and s["start"] < end]
        joined = " ".join(texts)
        funny = sum(joined.count(k) for k in FUNNY)
        talking = sum(joined.count(k) for k in TALKING)
        speech_secs = sum(min(s["end"], end) - max(s["start"], t)
                          for s in transcript if s["end"] > t and s["start"] < end)
        # REJECT: static talking (almost no motion) — the rejected-test-clip pattern.
        rejected = motion <= 1
        score = motion * 3 + max(0.0, peak + 30) * 0.4 + funny * 2 - talking * 5
        if speech_secs > WIN * 0.8 and motion <= 3:
            score -= 8  # non-stop talking with little action
        results.append({"start": t, "end": end, "motion": motion, "peak_db": peak,
                        "funny": funny, "talking": talking, "speech_secs": round(speech_secs, 1),
                        "score": round(score, 1), "rejected": rejected})
        t += STEP
    results.sort(key=lambda r: r["score"], reverse=True)
    return results

def best_window(video, wav, transcript, duration):
    ranked = score_windows(video, wav, transcript, duration)
    for r in ranked[:6]:
        print(f" window {r['start']}-{r['end']} score={r['score']} motion={r['motion']} "
              f"peak={r['peak_db']} funny={r['funny']} talking={r['talking']} rejected={r['rejected']}")
    for r in ranked:
        if not r["rejected"]:
            return r, ranked
    return None, ranked

if __name__ == "__main__":
    import sys
    video, wav = sys.argv[1], sys.argv[2]
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", video], capture_output=True, text=True).stdout)
    tr = transcribe(wav)
    json.dump(tr, open("transcript.json", "w"), indent=1)
    best, ranked = best_window(video, wav, tr, dur)
    print("BEST:", best)
    json.dump(ranked, open("scores.json", "w"), indent=1)
