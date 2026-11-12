---
name: mass-fan-edit
description: Make beat-synced cinematic "mass" fan edits (hero edits, phonk edits, lyric edits) from the user's own movie clips and a song - picks the drop, syncs cuts to beats and bass hits, slams glowing kinetic text on sung words, grades and renders 16:9 or 9:16 with FFmpeg/Python. Use for "make a fan edit", "mass edit", "phonk edit", "beat sync edit", "lyric edit", "edit these clips to this song", Iron Man / Spider-Man / any hero edits, reels and shorts.
---

# Mass Fan Edit (master skill)

You are the editor. The scripts are the hands. Your job: choose the song window, the words, the shots and the look; write two small JSON files; let the user's PC render.

Read only what you need, in this order. Each file is small on purpose.

| Need | Read |
|---|---|
| Fonts (which font for which mood) | `references/fonts.md` |
| Looks, grades, colour recipes, genre presets | `references/styles.md` |
| Editing craft (cut timing, ramps, shake, lyric sync) | `references/techniques.md` |
| Every project.json field | `references/project-schema.md` |
| Low-limit / free-plan flow, troubleshooting | `references/workflow.md` |

## Golden rules (token budget)

1. Never open raw video or audio. Run the scripts; read their **text reports** and **contact sheets** only.
2. One contact sheet = 30 thumbnails = about 1 image. A 3-minute clip costs 6 images. Read sheets once, take notes of good timestamps, never re-read.
3. Write `project.json` and `picks.json` in one go each. Do not print them twice in chat.
4. Verify picks with `verify_picks.py` sheets (2 images for ~60 cuts), fix only the broken slots.
5. Status lines short. No recap of steps.
6. Files over 400 MB cannot be uploaded/staged: use `make_sheets.py --proxy` (small copies) instead.

## The pipeline

```
project/
  raw/      source clips (user's own files)
  song/     the song
  -> PREP.bat            = analyze_song.py + make_sheets.py --proxy
  -> (Claude)            reads song_report.txt, video_report.txt, sheets/*.jpg
  -> (Claude)            writes project.json  (+ beats.json already written by analyze_song.py)
  -> massedit.py --dump-plan  -> _work/slots.txt (cut grid)
  -> (Claude)            writes picks.json (one shot per slot)
  -> verify_picks.py     -> sheets/verify_*.jpg   (Claude fixes bad slots)
  -> RUN_EDIT.bat        preview + final render on the user's PC
```

Scripts live in `scripts/`. Templates (`PREP.bat`, `RUN_EDIT.bat`, example projects) in `templates/`. Copy the bats into the project folder and set `SKILL_DIR` at the top.

### Step 1 - Song
`python scripts/analyze_song.py "<project>/song/x.mp3" [--start S] [--dur 38] [--vocals]`
Read `song_report.txt` (energy map, drops, breaks, BPM, candidate windows, bass hits).
- Pick the window: start 2-5 s **before** a drop, end on a hard stop or a phrase end. Default length 35-40 s.
- Lyric edits: the hook/chorus must be inside the window. If the user gives lyrics + rough times, trust them. Without speech tools, find the chorus by repetition (the melody that comes back) - see `techniques.md` "Lyric sync".
- Re-run with `--start` once you decide, so `beats.json` matches.
- Tempo: half-time phonk reads ~88 BPM; cut on that grid, slam text on bass hits (they can sit off-grid).

### Step 2 - Footage
`python scripts/make_sheets.py "<project>" --proxy`
Read `video_report.txt` first: **orientation** (landscape / portrait / square / scope), fps, letterbox, scene-cut list.
- Output aspect: user's choice; default = reels 9:16 if they say reel/short/status, else 16:9. Landscape source into 9:16 output is centre-cropped; set `style.crop_focus` if the hero sits left/right.
- Read the sheets. Note per sheet the strongest moments: transformations, landings, close-up eyes, blasts, falls, flights, wide hero shots, villain moments. Tag each `vN t0-t1 peak  what`.
- Keep every pick window **inside one camera shot**: use the scene-cut list; dark scenes often hide cuts, so keep windows tight (≤ 3 s).

### Step 3 - project.json
Start from `templates/project.example.json` (lyric mass edit) or `templates/project.phonk.json` (phonk). Set:
`song.start/duration`, `output.aspect`, `style` (grade, fonts, intensities), `sections` (intro / drop / groove / break / black / outro), `hits` (bass slams), `cues` (words).
Pick fonts from `fonts.md` by mood; one impact font + one italic lead font per edit; max 2 families.

### Step 4 - Slots and picks
`python scripts/massedit.py --project "<project>" --dump-plan` then read `_work/slots.txt`.
Write `picks.json`: `[{"slot":0,"file":"<exact name in raw/>","t0":12.0,"t1":14.5,"peak":13.1,"note":"eyes"}, ...]`
- `peak` = the frame that lands on the cut/beat (impact, eye glint, landing).
- calm slots (slow-mo, ~0.42x) need ~0.5x slot length of source; ramp slots need ~1.1x; hit slots ~1x.
- Big words get the hero shot of the edit. Story: build-up -> transformation -> action -> peak -> iconic hold.
- No `{"file": null}` unless you want black.

### Step 5 - Verify and render
`python scripts/verify_picks.py "<project>"` and read `sheets/verify_*.jpg`: each row triple (start/peak/end) must be the same shot. Fix only broken slots.
Render: `RUN_EDIT.bat` (preview then final). Render on the user's PC whenever possible - it is faster and costs no tokens.

## When you cannot run code (free / low-limit users)

Give the user `templates/PREP.bat` to run locally, ask them to upload only: `song_report.txt`, `video_report.txt`, `sheets/*.jpg`. Reply with `project.json` + `picks.json` as two code blocks (nothing else long). They save them in the project folder and run `RUN_EDIT.bat`. Second round: they upload `sheets/verify_*.jpg` only if something looks wrong. Full flow in `references/workflow.md`.

## Quality bar (check before you hand over)
- Every big word lands on its sung syllable or bass hit (±0.1 s). Audio offset in output = `song.start` exactly.
- No cut window crosses a hidden scene cut. No near-black shot longer than 1 s unless intentional.
- Long words (8+ letters) use a condensed font (`big-shoulders-black`, `anton`, `bebas-neue`) or `text_size` < 1.
- 9:16: words smaller (engine scales to 0.78), keep `text_y` 0.45-0.55, faces not cropped (crop_focus).
- Rights: the user supplies their own clips/music; keep outputs for fan/personal use and credit the film + song.
