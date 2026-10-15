#!/usr/bin/env python3
"""Render paper-style motion-graphic scenes to mp4 via headless Chromium.
Usage: scenes.py scenes.json outdir/   (writes outdir/<id>.mp4 per scene)
Scene types: title, chips, card, prompt, steps, map. Wrap words in *stars* for the mint italic accent."""
import json, os, re, subprocess, sys, html
from playwright.sync_api import sync_playwright

W, H, FPS = 1080, 1920, 24
GREEN, GREEN2, CREAM, MINT, CORAL, BG = "#2f5f45", "#1b3a2a", "#f1efe8", "#7ed3a6", "#e9785e", "#e8e5e0"

def rich(t):
    t = html.escape(t)
    return re.sub(r"\*(.+?)\*", rf'<em style="color:{MINT}">\1</em>', t)

CSS = f"""
*{{margin:0;box-sizing:border-box}}
body{{width:{W}px;height:{H}px;overflow:hidden;background:{BG};font-family:Lora,serif}}
.grid{{position:absolute;inset:-200px;background-image:linear-gradient(rgba(0,0,0,.045) 2px,transparent 2px),
 linear-gradient(90deg,rgba(0,0,0,.045) 2px,transparent 2px);background-size:56px 56px}}
.stage{{position:absolute;inset:0;animation:push var(--dur) linear both}}
@keyframes push{{from{{transform:scale(1)}}to{{transform:scale(1.07)}}}}
.dof{{position:absolute;inset:0;pointer-events:none;backdrop-filter:blur(7px);
 -webkit-mask-image:radial-gradient(ellipse 62% 48% at 50% 50%,transparent 60%,#000 100%)}}
.card{{position:absolute;left:50%;border-radius:34px;background:linear-gradient(165deg,{GREEN},{GREEN2});
 box-shadow:0 40px 80px rgba(20,30,25,.28),0 8px 20px rgba(20,30,25,.18),inset 0 2px 0 rgba(255,255,255,.08)}}
.chip{{position:absolute;display:flex;align-items:center;gap:22px;padding:26px 40px 26px 30px;border-radius:24px;
 background:linear-gradient(165deg,{GREEN},{GREEN2});color:{CREAM};font-style:italic;font-weight:600;font-size:52px;
 box-shadow:0 26px 50px rgba(20,30,25,.28);white-space:nowrap}}
.ico{{width:46px;height:56px;border-radius:8px;background:{CREAM};position:relative;flex:none}}
.ico:after{{content:"";position:absolute;left:10px;right:10px;top:20px;height:16px;
 background:repeating-linear-gradient({GREEN} 0 4px,transparent 4px 8px)}}
.label{{display:inline-block;padding:18px 34px;border-radius:18px;background:#0f1f17;color:{CREAM};
 font-style:italic;font-weight:600;font-size:50px}}
.line{{height:10px;border-radius:5px;background:rgba(241,239,232,.85);margin:26px 0}}
.title{{position:absolute;left:80px;right:80px;top:42%;text-align:center;font-family:Fraunces,serif;font-weight:800;
 font-size:120px;line-height:1.05;color:#1d2a22;letter-spacing:-2px}}
.title em{{font-style:italic}}
.ray{{position:absolute;width:26px;height:150px;border-radius:13px;transform-origin:50% 0;
 background:linear-gradient({CORAL},rgba(233,120,94,0))}}
svg path{{fill:none;stroke:#555;stroke-width:4;stroke-dasharray:4 12;stroke-linecap:round}}
@keyframes pop{{0%{{transform:var(--base) scale(.4);opacity:0}}70%{{transform:var(--base) scale(1.06);opacity:1}}100%{{transform:var(--base) scale(1);opacity:1}}}}
@keyframes grow{{from{{clip-path:inset(0 0 100% 0 round 34px)}}to{{clip-path:inset(0 0 0 0 round 34px)}}}}
@keyframes draw{{from{{stroke-dashoffset:var(--len)}}to{{stroke-dashoffset:0}}}}
@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes rays{{0%{{opacity:0;transform:rotate(var(--r)) scaleY(.2)}}100%{{opacity:1;transform:rotate(var(--r)) scaleY(1)}}}}
"""

def anim(name, at, dur=0.45, ease="cubic-bezier(.2,.8,.2,1)"):
    return f"animation:{name} {dur}s {ease} {at}s both;"

def chip(text, x, y, at, typed=True, size=1.0):
    base = f"translate(-50%,-50%) scale({size})"
    t = f'<span class="type" data-at="{at+0.25}" data-text="{html.escape(text)}"></span>' if typed else html.escape(text)
    return f'<div class="chip" style="left:{x}px;top:{y}px;--base:{base};transform:{base};{anim("pop", at)}"><div class="ico"></div>{t}</div>'

def scene_html(s):
    d = s["duration"]; body = []
    k = s["type"]
    if k == "title":
        body.append(f'<div class="title" style="{anim("pop", 0.1, 0.6)}--base:translate(0,0)">{rich(s["text"])}</div>')
    elif k == "chips":
        items = s["items"]; n = len(items)
        for i, it in enumerate(items):
            x = W/2 + (-150 if i % 2 == 0 else 150); y = H/2 - (n-1)*110 + i*220
            body.append(chip(it, x, y, 0.15 + i*0.35))
    elif k == "card":
        secs = s.get("sections", []); ch = 360 + len(secs)*300
        top = (H - ch)/2 + 60
        body.append(f'<div class="card" style="width:820px;height:{ch}px;top:{top}px;margin-left:-410px;{anim("grow", 0.5, 0.8)}padding:150px 70px 0">'
                    + "".join(f'<div class="line" style="width:{w}%;{anim("fade", 0.9+j*0.08, 0.3)}"></div>' for j, w in enumerate([92, 70, 84]))
                    + "".join(f'<div style="margin:40px 0 30px;{anim("fade", 1.0+i*0.55, 0.3)}"><span class="label"><span class="type" data-at="{1.05+i*0.55}" data-text="{html.escape(t)}"></span></span></div>'
                              + "".join(f'<div class="line" style="width:{w}%;{anim("fade", 1.2+i*0.55+j*0.06, 0.3)}"></div>' for j, w in enumerate([96, 78, 88])) for i, t in enumerate(secs))
                    + "</div>")
        body.append(chip(s["title"], W/2, top + 10, 0.1))
    elif k == "prompt":
        y = 640
        body.append(f'<div class="card" style="width:900px;height:200px;top:{y}px;margin-left:-450px;{anim("pop", 0.1)}--base:translate(0,0);padding:46px 50px;color:{CREAM};font-size:50px;font-weight:600">'
                    f'<span class="type" data-at="0.6" data-cps="22" data-text="{html.escape(s["text"])}"></span>'
                    f'<div style="position:absolute;right:40px;bottom:30px;font:28px Inter,sans-serif;opacity:.6">{html.escape(s.get("model","Sonnet 4.6"))}</div></div>')
        for i in range(7):
            r = -60 + i*20
            body.append(f'<div class="ray" style="left:{W/2-13}px;top:{y+215}px;--r:{r}deg;{anim("rays", 0.3+i*0.04, 0.5)}"></div>')
        links = s.get("links", [])
        for i, l in enumerate(links):
            x = W/2 + (-230 if i % 2 == 0 else 230) if len(links) > 1 else W/2 - 180
            ly = 1250 + (i//2)*260 + (i % 2)*120
            at = 1.6 + i*0.5
            body.append(f'<svg style="position:absolute;inset:0" width="{W}" height="{H}"><path d="M{W/2} {y+330} V{ly-120} H{x} V{ly-40}" style="--len:2000;{anim("draw", at-0.4, 0.6, "linear")}"/></svg>')
            body.append(chip(l, x, ly, at, typed=False, size=0.85))
    elif k == "steps":
        st = s["steps"]; ch = 300 + len(st)*190; top = (H-ch)/2 + 40
        body.append(f'<div class="card" style="width:760px;height:{ch}px;top:{top}px;margin-left:-380px;{anim("grow", 0.3, 0.7)}">'
                    f'<div style="position:absolute;top:60px;left:50%;transform:translateX(-50%);background:{CREAM};color:#1d2a22;padding:16px 32px;border-radius:14px;font-size:40px;font-weight:700;text-align:center;{anim("fade", 0.6, 0.3)}">'
                    f'<span class="type" data-at="0.7" data-text="{html.escape(s["title"])}"></span></div>'
                    + "".join(f'<div style="position:absolute;top:{220+i*190}px;{"left:60px" if i%2==0 else "right:60px"};{anim("pop", 1.2+i*0.5)}--base:translate(0,0)"><span class="label" style="font-size:44px">{html.escape(t)}</span></div>' for i, t in enumerate(st))
                    + "</div>")
    elif k == "map":
        items = s["items"]; cx, top = W/2, 560
        body.append(f'<div class="card" style="width:900px;height:200px;top:{top}px;margin-left:-450px;{anim("pop", 0.1)}--base:translate(0,0);padding:46px 50px;color:{CREAM};font-size:50px;font-weight:600">'
                    f'<span class="type" data-at="0.4" data-cps="24" data-text="{html.escape(s.get("text",""))}"></span></div>')
        for i, it in enumerate(items):
            x = cx + (-220 if i % 2 == 0 else 220); y = 1050 + i*190; at = 0.8 + i*0.45
            body.append(f'<svg style="position:absolute;inset:0" width="{W}" height="{H}"><path d="M{cx} {top+200} V{y-60} H{x}" style="--len:2000;{anim("draw", at-0.3, 0.5, "linear")}"/></svg>')
            body.append(chip(it, x, y, at, typed=False, size=0.8))
    return f"""<html><head><style>{CSS}</style></head><body style="--dur:{d}s">
<div class="stage"><div class="grid"></div>{''.join(body)}</div><div class="dof"></div>
<script>
function rich(t){{return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/\\*(.+?)\\*/g,'<em style="color:{MINT}">$1</em>')}}
window.seek=function(t){{
 document.getAnimations().forEach(a=>{{a.pause();a.currentTime=t*1000}});
 document.querySelectorAll('.type').forEach(e=>{{
  const full=e.dataset.text, cps=+(e.dataset.cps||16), n=Math.max(0,Math.floor((t-e.dataset.at)*cps));
  let plain=full.replace(/\\*/g,''), shown=plain.slice(0,n), out='', k=0, inEm=false;
  for(const c of full){{ if(c=='*'){{inEm=!inEm; continue}} if(k>=shown.length) break; out+=inEm?'\\u0001'+c:c; k++ }}
  e.innerHTML=out.replace(/(\\u0001.)+/g,m=>'<em style="color:{MINT}">'+m.replace(/\\u0001/g,'')+'</em>');
 }});
}};
</script></body></html>"""

def main():
    spec, outdir = json.load(open(sys.argv[1])), sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        for i, s in enumerate(spec):
            sid = s.get("id", f"scene{i:02d}")
            pg.set_content(scene_html(s)); pg.evaluate("document.fonts.ready")
            out = os.path.join(outdir, f"{sid}.mp4")
            ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
                                   "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17", "-preset", "fast", out], stdin=subprocess.PIPE)
            for f in range(round(s["duration"] * FPS)):
                pg.evaluate(f"seek({f / FPS})")
                ff.stdin.write(pg.screenshot(type="jpeg", quality=92))
            ff.stdin.close(); ff.wait()
            print("wrote", out)
        b.close()

if __name__ == "__main__":
    main()
