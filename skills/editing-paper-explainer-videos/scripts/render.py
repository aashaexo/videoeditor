#!/usr/bin/env python3
"""Render a short-form edit from plan.json. Usage: render.py plan.json out.mp4 [--preview]"""
import json, subprocess, sys, os, re

FONT_SANS, FONT_SERIF, FONT_DISPLAY = "Inter", "Instrument Serif", "Playfair Display"

def hex2ass(h, a=0):
    h = h.lstrip("#"); return f"&H{a:02X}{h[4:6]}{h[2:4]}{h[0:2]}".upper()

def ts(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def norm(t): return re.sub(r"[^\w%$.]", "", t.lower()).strip(".")

def chunk(words, max_words=2, max_chars=14):
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or len(" ".join(x["text"] for x in cur + [w])) > max_chars
                    or w["start"] - cur[-1]["end"] > 0.3):
            out.append(cur); cur = []
        cur.append(w)
        if re.search(r"[.,!?;:]$", w["text"]): out.append(cur); cur = []
    if cur: out.append(cur)
    return out

def seg_at(segs, t):
    for s in segs:
        if s["start"] <= t < s["end"]: return s
    return segs[-1]

def phrases(words, max_words=5):
    out, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["start"] - cur[-1]["end"] > 0.3):
            out.append(cur); cur = []
        cur.append(w)
        if re.search(r"[.,!?;:]$", w["text"]): out.append(cur); cur = []
    if cur: out.append(cur)
    return out

def stack_events(plan, words, W, H, segs):
    st = plan.get("style", {})
    emph = {norm(x) for x in plan.get("emphasis", [])}
    accent = hex2ass(st.get("accent", "#7ED3A6"))
    base = int(W * st.get("stack_scale", 0.10))
    ev, side = [], 0
    for ph in phrases(words, st.get("max_words", 5)):
        seg = seg_at(segs, ph[0]["start"])
        if seg.get("layout", "face") != "face" or seg.get("captions") is False: continue
        end = ph[-1]["end"] + 0.35
        anchor = seg.get("stack_anchor") or ("tl" if side % 2 == 0 else "br")
        side += 1
        tl = anchor == "tl"
        x0, y0 = (int(W * 0.08), int(H * 0.19)) if tl else (int(W * 0.93), int(H * 0.60))
        y = y0
        for i, w in enumerate(ph):
            t = w["text"].strip(",.;:!?")
            big = norm(w["text"]) in emph
            short = len(t) <= 3
            size = int(base * (1.15 if big else 0.72 if short else 1.0))
            indent = int(W * (0.0, 0.10, 0.18, 0.06, 0.14)[i % 5])
            col = accent if big else "&H00FFFFFF"
            ital = r"\i1" if big else r"\i0"
            x = x0 + indent if tl else x0 - indent
            fx = (rf"{{\an{7 if tl else 9}\pos({x},{y})\fs{size}{ital}\c{col}\shad2\4a&H70&"
                  rf"\fad(60,120)\fscx80\fscy80\t(0,110,\fscx100\fscy100)}}")
            ev.append(f"Dialogue: 1,{ts(w['start'])},{ts(end)},Stack,,0,0,0,,{fx}{t}")
            y += int(size * 0.92)
    return ev

def build_ass(plan, words, W, H):
    emph = {norm(x) for x in plan.get("emphasis", [])}
    st = plan.get("style", {})
    sans_size, serif_size = int(W * st.get("sans_scale", 0.062)), int(W * st.get("serif_scale", 0.085))
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sans,{FONT_SANS},{sans_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,-1,0,1,0,3,5,40,40,0,1
Style: Serif,{FONT_DISPLAY},{serif_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H50000000,-1,-1,0,0,100,100,-2,0,1,0,4,5,40,40,0,1
Style: Title,{FONT_DISPLAY},{int(serif_size*1.15)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H50000000,-1,-1,0,0,100,100,-2,0,1,0,4,5,40,40,0,1
Style: Soft,{FONT_SERIF},{int(serif_size*1.05)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H50000000,0,-1,0,0,100,100,-1,0,1,0,4,5,40,40,0,1
Style: Stack,Fraunces,{int(W*0.085)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H70000000,-1,0,0,0,100,100,-1,0,1,0,2,7,40,40,0,1
Style: TitleSans,{FONT_SANS},{int(sans_size*1.6)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H50000000,-1,0,0,0,100,100,-3,0,1,0,0,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    segs = plan["segments"]
    if st.get("caption_mode") == "stack":
        return hdr + "\n".join(stack_events(plan, words, W, H, segs) + title_events(plan, W, H, serif_size)) + "\n"
    groups = chunk(words, st.get("max_words", 2), st.get("max_chars", 14))
    for gi, g in enumerate(groups):
        start = g[0]["start"]
        end = groups[gi + 1][0]["start"] if gi + 1 < len(groups) else g[-1]["end"] + 0.4
        end = min(end, g[-1]["end"] + 0.6)
        seg = seg_at(segs, start)
        if seg.get("captions") is False: continue
        if any(t["start"] - 0.05 <= start < t["end"] for t in plan.get("titles", [])): continue
        dark = seg.get("theme", "dark") == "dark"
        is_emph = any(norm(w["text"]) in emph for w in g) or seg.get("caption_style") == "serif"
        style = ("Soft" if lay == "face" else "Serif") if is_emph else "Sans"
        lay = seg.get("layout", "face")
        y = seg.get("caption_y", {"split": 0.455, "broll": 0.80, "face": 0.80}[lay])
        col = "&H00FFFFFF" if (dark or lay == "face") else "&H00111111"
        shadow = r"\shad3\4a&H60&" if (dark or lay == "face") else r"\shad0"
        text = " ".join(w["text"] for w in g).rstrip(",.;:")
        if style == "Serif": text = text.upper() if seg.get("serif_upper", lay == "broll") else text
        # word pop: scale 85 -> 100 in 90ms, quick fade
        fx = rf"{{\pos({W//2},{int(H*y)})\c{col}{shadow}\fad(40,0)\fscx85\fscy85\t(0,90,\fscx100\fscy100)}}"
        ev.append(f"Dialogue: 1,{ts(start)},{ts(end)},{style},,0,0,0,,{fx}{text}")
    return hdr + "\n".join(ev + title_events(plan, W, H, serif_size)) + "\n"

def title_events(plan, W, H, serif_size):
    ev = []
    for t in plan.get("titles", []):
        y = int(H * t.get("y", 0.70)); style = "TitleSans" if t.get("font") == "sans" else "Title"
        col = hex2ass(t.get("color", "#FFFFFF"))
        lines = t["text"].split("\\N")
        lead = t.get("lead", 0.25)
        for li, line in enumerate(lines):
            s0 = t["start"] + li * lead
            ly = y + li * int(serif_size * 1.15)
            fx = rf"{{\pos({W//2},{ly})\c{col}\fad(60,80)\fscx70\fscy70\t(0,120,\fscx100\fscy100)}}"
            ev.append(f"Dialogue: 2,{ts(s0)},{ts(t['end'])},{style},,0,0,0,,{fx}{line}")
    return ev

def main():
    plan_path, out = sys.argv[1], sys.argv[2]
    preview = "--preview" in sys.argv
    base = os.path.dirname(os.path.abspath(plan_path))
    P = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
    plan = json.load(open(plan_path))
    W, H = plan.get("size", [1080, 1920])
    if preview: W, H = W // 2, H // 2
    fps = plan.get("fps", 30)
    words = json.load(open(P(plan["words"])))
    segs = plan["segments"]
    ass = os.path.join(base, ".captions.ass"); open(ass, "w").write(build_ass(plan, words, W, H))

    tmp = os.path.join(base, ".segs"); os.makedirs(tmp, exist_ok=True)
    face_y = plan.get("face_y", 0.42)
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", "-an"]
    parts = []
    for i, s in enumerate(segs):
        d = s["end"] - s["start"]
        lay = s.get("layout", "face")
        ins = ["-ss", f"{s['start']:.3f}", "-t", f"{d:.3f}", "-i", P(plan["aroll"])]
        a = f"[0:v]setpts=PTS-STARTPTS,fps={fps}"
        fc = []
        if lay == "face":
            z = s.get("zoom", 1.0); zw, zh = int(W * z / 2) * 2, int(H * z / 2) * 2
            fc.append(f"{a},scale={zw}:{zh}:force_original_aspect_ratio=increase,crop={W}:{H}:(iw-{W})/2:(ih-{H})*{face_y}[v]")
        else:
            src = P(s["broll"]); img = src.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
            ins += (["-loop", "1", "-framerate", str(fps), "-t", f"{d:.3f}", "-i", src] if img
                    else ["-stream_loop", "-1", "-ss", str(s.get("broll_in", 0)), "-t", f"{d:.3f}", "-i", src])
            bg = s.get("bg", "#0d0f14" if s.get("theme", "dark") == "dark" else "#f3f2ee")
            bh = H if lay == "broll" else H // 2
            cover = s.get("fit") == "cover"
            bw = W if cover else int(W * s.get("broll_scale", 0.88 if lay == "broll" else 0.82))
            bhh = bh if cover else int(bh * 0.62)
            kb = s.get("ken_burns", 0.04)
            fc.append(f"color=c={bg}:s={W}x{bh}:r={fps}:d={d:.3f}[bg]")
            fc.append(f"[1:v]fps={fps},setpts=PTS-STARTPTS,scale={bw}:{bhh}:force_original_aspect_ratio={'increase' if cover else 'decrease'},"
                      f"scale='trunc(iw*(1+{kb}*t/{d:.3f})/2)*2':'trunc(ih*(1+{kb}*t/{d:.3f})/2)*2':eval=frame,setsar=1[b]")
            by = s.get("broll_y", 0.5 if cover else (0.40 if lay == "broll" else 0.46))
            fc.append(f"[bg][b]overlay=(W-w)/2:{int(bh*by)}-h/2:shortest=1:eof_action=endall[top]")
            if lay == "broll":
                fc.append("[top]null[v]")
            else:
                fy = s.get("face_y", 0.5)
                fc.append(f"{a},scale={W}:-2,crop={W}:{H//2}:0:'max(0,min(ih-{H//2},ih*{fy}-{H//4}))'[f]")
                fc.append("[top][f]vstack=shortest=1[v]")
        out_i = os.path.join(tmp, f"{i:03d}.mp4"); parts.append(out_i)
        subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(fc), "-map", "[v]",
                        "-frames:v", str(round(d * fps)), "-r", str(fps), *enc, out_i], check=True)
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    inputs = ["-i", P(plan["aroll"]), "-f", "concat", "-safe", "0", "-i", lst]
    fc, n = [f"[1:v]format=yuv420p,ass='{ass}'[vout]"], 2

    total = segs[-1]["end"]
    a_chain = f"[0:a]atrim=0:{total},asetpts=PTS-STARTPTS,highpass=f=80,acompressor=threshold=-18dB:ratio=3:attack=5:release=80"
    mixes = []
    if plan.get("music"):
        inputs += ["-stream_loop", "-1", "-i", P(plan["music"])]
        fc.append(f"{a_chain},asplit[voice][key]")
        fc.append(f"[{n}:a]atrim=0:{total},volume={plan.get('music_db', -22)}dB,afade=t=out:st={total-1.5}:d=1.5[mus]")
        fc.append("[mus][key]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[duck]")
        mixes += ["[voice]", "[duck]"]; n += 1
    else:
        fc.append(f"{a_chain}[voice]"); mixes.append("[voice]")
    for k, fx in enumerate(plan.get("sfx", [])):
        inputs += ["-i", P(fx["file"])]
        ms = int(fx["t"] * 1000)
        fc.append(f"[{n}:a]volume={fx.get('db', -10)}dB,adelay={ms}|{ms}[s{k}]"); mixes.append(f"[s{k}]"); n += 1
    fc.append("".join(mixes) + f"amix=inputs={len(mixes)}:normalize=0:duration=first,"
              "loudnorm=I=-14:TP=-1.5:LRA=7,aresample=48000,aformat=channel_layouts=stereo[aout]")

    cmd = ["ffmpeg", "-v", "error", "-stats", "-y", *inputs, "-filter_complex", ";".join(fc),
           "-map", "[vout]", "-map", "[aout]", "-r", str(fps), "-c:v", "libx264",
           "-preset", "veryfast" if preview else "medium", "-crf", "23" if preview else "18",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{total:.3f}", out]
    subprocess.run(cmd, check=True)
    print("wrote", out)

if __name__ == "__main__":
    main()
