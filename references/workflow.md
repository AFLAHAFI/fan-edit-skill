# Workflow, low-limit mode and troubleshooting

## A. Full mode (Claude can run code / reach the user's files)
1. `analyze_song.py` → read `song_report.txt` (≈60 lines).
2. `make_sheets.py --proxy` → read `video_report.txt` + `sheets/*.jpg` (1 image per 30 s of footage at 1 s/thumb; long clips auto use 2-3 s/thumb).
3. Write `project.json`, re-run `analyze_song.py --start <chosen>` so `beats.json` matches.
4. `massedit.py --dump-plan` → read `_work/slots.txt`.
5. Write `picks.json`. `verify_picks.py` → read `sheets/verify_*.jpg`, fix bad slots.
6. `massedit.py --preview` (half size) → spot-check 6-8 frames with ffmpeg (`-ss t -frames:v 1`), tile them into one image.
7. Final render on the user's PC (`RUN_EDIT.bat`). Check audio offset if in doubt (cross-correlate output audio with the song around `song.start`).

Typical cost: ~10-14 images + a few short text files for a 38 s edit from 4 minutes of footage.

## B. Low-limit / free-plan mode (Claude only chats)
The user's PC does all the work; Claude only reads small files and writes two JSON files.

1. User puts clips in `raw/`, song in `song/`, copies `PREP.bat` + `RUN_EDIT.bat` into the folder, edits `SKILL_DIR` inside them, runs `PREP.bat`.
2. User uploads to Claude: `song_report.txt`, `video_report.txt`, `sheets/*.jpg` (no videos, no audio), plus the PROMPT.md filled in.
3. Claude replies with **only**: `project.json` (code block) - and asks the user to run `RUN_EDIT.bat --plan` (it prints the slot list) if picks are wanted; else the engine auto-picks.
4. User pastes `_work/slots.txt`; Claude replies with `picks.json` (code block).
5. User runs `RUN_EDIT.bat`. If a shot looks wrong, user names the second (e.g. "0:12 shows wrong shot") and Claude patches only that slot.

Tips to save messages: ask all questions in the first reply (song window OK? aspect? words?), batch everything, never re-read sheets.

## C. Troubleshooting
| Symptom | Fix |
|---|---|
| Words early/late | shift that cue's `t` (+ `lead_t`, `end`); 0.1 s steps |
| Whole song offset wrong | `song.start` in project.json AND `beats.json` start must match; re-run analyze_song.py `--start` |
| A cut shows two different shots | the pick window crosses a hidden cut: shrink `t0..t1` around `peak` |
| Too dark | grade `clean` or `phonk-night`; `min_bright` up in auto mode |
| Long word too big / cut off | condensed font or `"text_size": 0.8` |
| Slow-mo looks choppy | source is low fps; use `normal` ramp for that slot, or avoid 12 fps proxies (render from originals) |
| "file not found in raw" | `picks.json` `file` must match the file name exactly (case-insensitive) |
| Old settings still rendering | file sync cached an old copy: re-copy files, check `project.json` values |
| 9:16 cuts the hero off | `"crop_focus": [0.3, 0.5]` (left) / `[0.7, 0.5]` (right) |
| ffmpeg not found | install from gyan.dev/ffmpeg/builds, add `bin` to PATH, reopen terminal |
