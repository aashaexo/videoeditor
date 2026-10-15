#!/usr/bin/env python3
"""Word-level transcript. Usage: transcribe.py in.mp4 words.json [--fix "cloud code=Claude Code" ...]"""
import json, re, subprocess, sys, argparse
import numpy as np
from faster_whisper import WhisperModel

p = argparse.ArgumentParser()
p.add_argument("src"); p.add_argument("out")
p.add_argument("--model", default="small")
p.add_argument("--fix", action="append", default=[], help='"wrong=Right", applied to joined text')
a = p.parse_args()

raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.src, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                     capture_output=True, check=True).stdout
audio = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
segs, _ = WhisperModel(a.model, device="cpu", compute_type="int8").transcribe(audio, word_timestamps=True)
words = [{"start": round(w.start, 2), "end": round(w.end, 2), "text": w.word.strip()} for s in segs for w in s.words]

merged = []
for w in words:
    if merged and (re.match(r"^(%|\.\d+|,\d{3})", w["text"]) and re.search(r"\d$", merged[-1]["text"]) or w["text"].startswith("-")):
        merged[-1]["text"] += w["text"]; merged[-1]["end"] = w["end"]
    else:
        merged.append(w)
words = merged

def norm(t): return re.sub(r"('s)?[.,!?;:]*$", "", t.lower())

for f in a.fix:
    wrong, right = [x.strip() for x in f.split("=", 1)]
    wl, n = wrong.lower().split(), len(wrong.split())
    i = 0
    while i <= len(words) - n:
        if [norm(w["text"]) for w in words[i:i+n]] == wl:
            tail = words[i+n-1]["text"][len(wl[-1]):]
            merged = {"start": words[i]["start"], "end": words[i+n-1]["end"], "text": right + tail}
            words[i:i+n] = [merged]
        i += 1

json.dump(words, open(a.out, "w"), indent=1)
print(f"{len(words)} words, {words[-1]['end']:.1f}s, {len(words)/words[-1]['end']*60:.0f} wpm")
print(" ".join(w["text"] for w in words))
