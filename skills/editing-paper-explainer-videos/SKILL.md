---
name: editing-paper-explainer-videos
description: Edit a talking-head clip into a calm vertical explainer in the "paper motion-graphics" style (warm grid background, green 3D cards, typing text, dotted links, stacked serif kinetic captions on face shots). Use when aasha asks for this explainer/Claude-setup style, or for a face-first edit with a few animated graphics.
---

# Paper motion-graphics explainer (reference style B)

Built from a reference reel: 46.8s, 1080x1920, 24fps, ~190 wpm, explains a 4-part setup (Agents.md, Context.md, Memory.md, Skills.md) and ends on a recap. The look is soft, tactile and premium, not hype.

aasha's default: keep b-roll light. Unless told otherwise, the face is on screen most of the time and graphics come in only for the 3-5 key ideas.

## The style formula

Structure:
1. Hook 0-4s: a question with a number ("Why would you subscribe to Claude only to use 10% of its brain?") over a playful mascot/visual, then "Here's a setup that makes it worth it."
2. Steps 1..N, each in 2-3 short beats: name it ("Start by creating the agents.md file"), relate it ("what you'd give a new employee"), show what's inside.
3. Recap and close: all the pieces connected in one diagram, then one punchline on face ("turn a four-hour task into a single instruction"). No hard sell.

Pacing:
- Slower than hype edits: ~190 wpm, natural 0.3-0.6s breaths kept (only cut gaps >0.6s, `cut_silence.py --min 0.6 --pad 0.15`).
- One scene per idea, 3-6s each, cuts land on sentence boundaries. Inside a scene, something moves every ~0.5s (a chip pops, a label types, a line draws).
- Constant slow camera push (about 7% zoom over each scene). Soft depth-of-field blur at the frame edges.

Look (motion graphics, `scenes.py`):
- Background: warm off-white #e8e5e0 with a faint 56px grid.
- Objects: deep forest-green cards with a gradient (#2f5f45 to #1b3a2a), big rounded corners, heavy soft drop shadows, so they read as thick paper/clay.
- Text inside graphics: Lora italic semibold in cream #f1efe8. Key phrase in mint italic #7ed3a6 ("Stop *signing emails* with cheers").
- Accent: coral #e9785e, used for the mascot, rays under the prompt bar and "active" highlights.
- Recurring motifs: file chips (icon + "Agents.md") that type their names; a tall card that unrolls and fills with labeled sections; a prompt bar (with "Sonnet 4.6") that types a request, coral rays and dotted lines linking to the files it uses; a step card for workflows (Identify > Analyze > Break down > Summarize).
- Graphics carry the text, so b-roll scenes get no captions.

Face shots:
- Used as breathers between sections and for the punchline (in the reference only ~6s total; for aasha use the face much more).
- Captions are stacked kinetic serif words (Fraunces Black, white, soft shadow). Words build up one at a time in a staggered staircase, 2-5 per phrase, and the phrase clears before the next. Short words ("a", "you", "can") are smaller; keywords are bigger, italic, mint green.
- Alternate the caption cluster between top-left (above the head) and bottom-right (beside the mic) so it never covers the face.

Audio: voice plus a quiet ambient music bed (about -24 dB under voice, ducked) and soft UI sounds (pops, clicks, typing) on graphic events. Final -14 LUFS / -1.5 dBTP.

## Workflow

Tools: ffmpeg (with libass), Python 3, `pip install faster-whisper numpy playwright && python3 -m playwright install chromium`. Fonts into ~/.fonts, then `fc-cache -f`: Fraunces (Regular + Italic variable), Lora (Regular + Italic variable), Inter. Raw files are on github.com/google/fonts under ofl/<name>/.

The scripts are in `scripts/` next to this file.

1. Inspect: `ffprobe`, a 1fps contact sheet, `-af ebur128`. Make sure it's a raw talking-head take. If it's already an edited video, say so before going further (you can't swap b-roll for face that isn't there).
2. Tighten: `python3 scripts/cut_silence.py raw.mp4 tight.mp4 --min 0.6 --pad 0.15`.
3. Transcribe: `python3 scripts/transcribe.py tight.mp4 words.json --fix "cloud=Claude"`, then check product and file names.
4. Pick the 3-5 ideas that deserve a graphic, and write `scenes.json` (one scene per idea, duration = the length of that sentence chunk in words.json). Render: `python3 scripts/scenes.py scenes.json scenes/` (about 10s of render time per second of output).
5. Write `plan.json`: `"style": {"caption_mode": "stack", "max_words": 4}`, face segments everywhere else, b-roll segments pointing at `scenes/<id>.mp4` with `"fit": "cover", "ken_burns": 0`. List keywords in `emphasis`.
6. Preview: `python3 scripts/render.py plan.json preview.mp4 --preview`. Check frames, show aasha, then do the final render without `--preview`.

### scenes.json

```json
[
 {"id": "hook",   "type": "title",  "text": "10% of its *brain*", "duration": 2.5},
 {"id": "files",  "type": "chips",  "items": ["Agents.md", "Context.md", "Memory.md", "Skills.md"], "duration": 3},
 {"id": "agents", "type": "card",   "title": "Agents.md", "sections": ["What you do", "How you sound", "How you work"], "duration": 4},
 {"id": "memory", "type": "prompt", "text": "Stop *signing emails* with 'cheers'", "links": ["Agents.md", "Memory.md"], "duration": 4},
 {"id": "skills", "type": "steps",  "title": "research a competitor", "steps": ["Identify", "Analyze", "Break down", "Summarize"], "duration": 4},
 {"id": "recap",  "type": "map",    "text": "Apply *everything* we've set up.", "items": ["Agents.md", "Memory.md", "Context.md", "Skills.md"], "duration": 3.5}
]
```
Types: `title` (big Fraunces line), `chips` (file chips pop in and type), `card` (card unrolls with typed section labels), `prompt` (prompt bar types, rays, dotted links to chips), `steps` (workflow card), `map` (prompt plus every chip linked). `*word*` marks the mint italic accent. To get a new motif, add a branch in `scene_html()` using the same CSS classes, so the look stays consistent.

### plan.json (example, face-first)

```json
{
  "size": [1080, 1920], "fps": 24,
  "aroll": "tight.mp4", "words": "words.json",
  "emphasis": ["brain", "context", "turn", "task"],
  "style": {"caption_mode": "stack", "max_words": 4, "accent": "#7ED3A6"},
  "segments": [
    {"start": 0,   "end": 2.5, "layout": "broll", "broll": "scenes/hook.mp4", "fit": "cover", "ken_burns": 0},
    {"start": 2.5, "end": 9.0, "layout": "face"},
    {"start": 9.0, "end": 13.0,"layout": "broll", "broll": "scenes/agents.mp4", "fit": "cover", "ken_burns": 0},
    {"start": 13.0,"end": 20.0,"layout": "face", "zoom": 1.08}
  ],
  "music": "assets/ambient.mp3", "music_db": -24
}
```
Segment options are the same as in the `editing-short-form-videos` skill. Here `stack_anchor` ("tl" or "br") pins a face segment's caption cluster to one side. Style options: `stack_scale` (word size, default 0.10 of the width) and `accent`.

## Checks before delivering
- Contact sheet: the face is visible most of the time (aasha's preference), each graphic matches the sentence it covers, and captions never cover the eyes or mouth.
- Typed text has finished before a scene cuts (keep each scene at least as long as its last animation + 0.5s).
- -14 LUFS, captions in sync, names spelled right, no emojis, no em dashes in on-screen text.
