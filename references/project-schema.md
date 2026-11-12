# project.json reference

```jsonc
{
  "title": "Veera x Iron Man",                 // free text
  "song":   {"start": 65.0, "duration": 38.0},  // window in the song (seconds); edit time = song time - start
  "output": {"aspect": "16:9", "fps": 30, "crf": 14, "name": "VEERA_IronMan.mp4"},
            // aspect: 16:9 | 9:16 | 1:1 | 4:5 | 21:9
  "style":  {"grade": "teal-orange", "impact_font": "anton", "lead_font": "playfair-italic",
             "lead_color": "white", "zoom": 1.0, "shake": 1.0, "flash": 1.0, "chroma": 1.0,
             "grain": 1.0, "grid": 1.0, "text_size": 1.0, "text_y": 0.52, "letterbox": false,
             "crop_focus": [0.5, 0.5], "flash_color": "#FFFFFF", "hit_flash_color": "#E61E28"},
  "hud":    {"enabled": false, "title": "VEERA", "sub": "", "br": "", "accent": "#FFC83C"},
  "colors": {"pink": {"glow": "#FF2BD6", "core1": "#FFE6FA", "core2": "#FF6FE0"}},   // optional extra colours
  "sections": [[0.0, 6.44, "groove"], [6.44, 7.85, "break"], [7.85, 14.92, "drop"], [36.66, 38.0, "outro"]],
  "hits":   [8.32, 15.87, 23.42],                 // bass slams: forced cut + shake + colour flash
  "cues": [
    {"lead": "veezha", "lead_t": 6.35, "word": "VEERA", "t": 7.85, "end": 11.45, "color": "gold", "grid": true}
  ],
  "min_bright": 0.035,                            // auto-scan only: skip shots darker than this
  "seed": 7                                       // groove randomness (stutters / 2-beat ramps)
}
```

## sections (edit time, contiguous, cover 0 → duration)
| mode | cut pattern |
|---|---|
| `intro` | 1-2 long slow-mo shots (build-up) |
| `drop` | hard cut on every beat |
| `groove` | mix of 2-beat speed ramps, 1-beat cuts, half-beat stutters |
| `break` | one slow-mo shot (music stops, lead word) |
| `black` | black screen (breath before the biggest hit) |
| `outro` | one slow-mo hold + fade |

## cues
| key | meaning |
|---|---|
| `word` | big slam word (UPPERCASE looks best) |
| `t` / `end` | slam time / disappear time (edit seconds) |
| `lead` / `lead_t` | optional small italic word and when it fades in (before `t`) |
| `color` | gold, red, blue, cyan, white, or a custom colour from `colors` |
| `grid` | echo-grid behind this word |

Two cues must not overlap (`end` of one ≤ `t` of the next).

## beats.json (written by analyze_song.py)
`{"start", "duration", "bpm", "beats": [...], "beat_strength": [...], "bass_hits": [...]}` - `start` must equal `song.start`, otherwise the engine recomputes beats with librosa.

## picks.json (optional; without it the engine auto-scans)
```json
[{"slot": 0, "file": "clip name.mp4", "t0": 12.0, "t1": 14.5, "peak": 13.1, "note": "eyes light up", "ramp": "slow"}]
```
`file` = exact file name in `raw/`; `t0..t1` = usable window inside ONE camera shot; `peak` = frame that lands on the cut; `ramp` (optional) overrides `slow | ramp | normal`; `"file": null` = black.
