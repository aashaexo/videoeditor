#!/usr/bin/env python3
"""Jump-cut dead air. Usage: cut_silence.py in.mp4 out.mp4 [--db -35] [--min 0.25] [--pad 0.06]"""
import argparse, re, subprocess
p = argparse.ArgumentParser()
p.add_argument("src"); p.add_argument("out")
p.add_argument("--db", type=float, default=-35); p.add_argument("--min", type=float, default=0.25)
p.add_argument("--pad", type=float, default=0.06)
a = p.parse_args()
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.src],
                           capture_output=True, text=True).stdout)
log = subprocess.run(["ffmpeg", "-i", a.src, "-af", f"silencedetect=n={a.db}dB:d={a.min}", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)] + [dur]
keep, t = [], 0.0
for s, e in zip(starts, ends):
    if s + a.pad > t: keep.append((t, min(dur, s + a.pad)))
    t = max(0, e - a.pad)
if t < dur: keep.append((t, dur))
keep = [(s, e) for s, e in keep if e - s > 0.05]
expr = "+".join(f"between(t,{s:.3f},{e:.3f})" for s, e in keep)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.src,
    "-vf", f"select='{expr}',setpts=N/FRAME_RATE/TB", "-af", f"aselect='{expr}',asetpts=N/SR/TB",
    "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-c:a", "aac", "-b:a", "192k", a.out], check=True)
new = sum(e - s for s, e in keep)
print(f"{len(keep)} pieces, {dur:.1f}s -> {new:.1f}s (cut {dur-new:.1f}s)")
