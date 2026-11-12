# Font library

All fonts are bundled in `fonts/` (SIL Open Font License, Permanent Marker = Apache 2.0; licenses in `fonts/licenses/`). Use the **id** in `project.json` → `style.impact_font`, `style.lead_font`, `style.mono_font`.

![All fonts](../docs/fonts/_board.jpg)

## How to choose (fast rules)

1. **One impact font + one italic lead font.** Never more than 2 families in one edit.
2. **Match the genre mood first, then the word length.** 8+ letter words (METAMORPHOSIS, OMKAARA) → condensed: `big-shoulders-black`, `anton`, `bebas-neue`, `teko-bold`, `oswald-bold`.
3. **Wide fonts** (`russo-one`, `unbounded-black`, `orbitron-black`, `audiowide`, `bungee`) feel modern/tech but need short words (≤ 7 letters) or `text_size` 0.8.
4. **Lead-in word** (small italic before the slam) = elegant serif: `playfair-italic` (classic), `instrument-serif` (modern), `cormorant-italic` (romantic/thin), `dm-serif-italic` (bold, busy shots).
5. **Busy/bright shots** → heavier fonts + `shadow` is automatic; avoid `monoton` and `cormorant-italic` on bright skies.
6. **Regional mass edits** (Tamil/Malayalam/Telugu hero songs) → `anton` + `playfair-italic`, gold/red glow. **Phonk** → `russo-one` or `rubik-glitch` + `instrument-serif`, crimson/neon-blue/white.

## Genre → font quick map

| Edit type | Impact | Lead | Colours |
|---|---|---|---|
| Mass hero (Veera / Hukum style) | anton | playfair-italic | gold, red, cyan |
| Phonk night (Spider-Man, cars) | russo-one / rubik-glitch | instrument-serif | red, blue, white |
| Tech / Iron Man / sci-fi | orbitron-black | instrument-serif | cyan, gold |
| Trailer / cinematic | bebas-neue | cormorant-italic | white, gold |
| Sports / cricket / football | teko-bold | dm-serif-italic | white, red |
| Villain / war / gangster | black-ops-one | cormorant-italic | red, white |
| Anime / Gen-Z trend | unbounded-black | instrument-serif | blue, white, pink (custom colour) |
| Comic / funny | bangers | playfair-italic | gold, red |
| Synthwave / retro / night drive | monoton | dm-serif-italic | cyan, pink |
| Emotional / friendship / love | permanent-marker or bebas-neue | cormorant-italic | white, gold |
| Car / bike / racing / EDM | audiowide | instrument-serif | red, blue |

## Catalogue

### `anton` — Anton  (impact)
Mood: loud, tall, poster-mass. Best for: South-Indian mass edits, hero intros, single slam words. Pairs with: `playfair-italic`.
![anton](../docs/fonts/anton.jpg)

### `bebas-neue` — Bebas Neue  (impact)
Mood: clean cinematic caps. Best for: trailer-style titles, minimal edits, sports. Pairs with: `cormorant-italic`.
![bebas-neue](../docs/fonts/bebas-neue.jpg)

### `russo-one` — Russo One  (impact)
Mood: wide, techy, game-HUD. Best for: phonk, Spider-Man, sci-fi, car edits. Pairs with: `instrument-serif`.
![russo-one](../docs/fonts/russo-one.jpg)

### `oswald-bold` — Oswald Bold  (impact)
Mood: condensed news-headline. Best for: documentary / motivational / fact edits. Pairs with: `dm-serif-italic`. Variable weight used: 700.
![oswald-bold](../docs/fonts/oswald-bold.jpg)

### `teko-bold` — Teko Bold  (impact)
Mood: sharp, sporty, condensed. Best for: cricket/football edits, fast hype. Pairs with: `instrument-serif`. Variable weight used: 700.
![teko-bold](../docs/fonts/teko-bold.jpg)

### `bungee` — Bungee  (impact)
Mood: blocky street signage. Best for: hip-hop, street, comic energy. Pairs with: `playfair-italic`.
![bungee](../docs/fonts/bungee.jpg)

### `black-ops-one` — Black Ops One  (impact)
Mood: military stencil. Best for: war, action, villain, gangster edits. Pairs with: `cormorant-italic`.
![black-ops-one](../docs/fonts/black-ops-one.jpg)

### `orbitron-black` — Orbitron Black  (impact)
Mood: futuristic geometric. Best for: Iron Man / tech / space / AI edits. Pairs with: `instrument-serif`. Variable weight used: 900.
![orbitron-black](../docs/fonts/orbitron-black.jpg)

### `monoton` — Monoton  (impact)
Mood: neon retro lines. Best for: synthwave, 80s, night-drive, VHS look. Pairs with: `dm-serif-italic`.
![monoton](../docs/fonts/monoton.jpg)

### `archivo-black` — Archivo Black  (impact)
Mood: heavy modern grotesk. Best for: clean brand-style edits, quotes. Pairs with: `instrument-serif`.
![archivo-black](../docs/fonts/archivo-black.jpg)

### `big-shoulders-black` — Big Shoulders Black  (impact)
Mood: ultra-condensed industrial. Best for: long words that must stay huge (METAMORPHOSIS, OMKAARA). Pairs with: `playfair-italic`. Variable weight used: 900.
![big-shoulders-black](../docs/fonts/big-shoulders-black.jpg)

### `unbounded-black` — Unbounded Black  (impact)
Mood: wide, round, Gen-Z. Best for: anime, music-video, trendy reels. Pairs with: `instrument-serif`. Variable weight used: 900.
![unbounded-black](../docs/fonts/unbounded-black.jpg)

### `bangers` — Bangers  (impact)
Mood: comic-book shout. Best for: superhero comic, funny, kids. Pairs with: `playfair-italic`.
![bangers](../docs/fonts/bangers.jpg)

### `audiowide` — Audiowide  (impact)
Mood: racing / electronic. Best for: car, bike, EDM, gaming. Pairs with: `instrument-serif`.
![audiowide](../docs/fonts/audiowide.jpg)

### `rubik-glitch` — Rubik Glitch  (impact)
Mood: broken digital glitch. Best for: hacker, villain, horror, dark phonk. Pairs with: `cormorant-italic`.
![rubik-glitch](../docs/fonts/rubik-glitch.jpg)

### `permanent-marker` — Permanent Marker  (impact)
Mood: hand-written marker. Best for: emotional, friendship, vlog-style edits. Pairs with: `dm-serif-italic`.
![permanent-marker](../docs/fonts/permanent-marker.jpg)

### `rajdhani-bold` — Rajdhani Bold  (impact)
Mood: squared tech, Indian-made. Best for: light tech text, subtitles, sub-labels. Pairs with: `instrument-serif`.
![rajdhani-bold](../docs/fonts/rajdhani-bold.jpg)

### `playfair-italic` — Playfair Display Italic  (lead)
Mood: classic elegant serif. Best for: small lead-in words before a slam. Pairs with: `anton`.
![playfair-italic](../docs/fonts/playfair-italic.jpg)

### `instrument-serif` — Instrument Serif Italic  (lead)
Mood: modern editorial italic. Best for: lead-ins in modern / phonk edits. Pairs with: `russo-one`.
![instrument-serif](../docs/fonts/instrument-serif.jpg)

### `cormorant-italic` — Cormorant Garamond Italic  (lead)
Mood: thin, luxurious, poetic. Best for: emotional / romantic lead-ins. Pairs with: `bebas-neue`. Variable weight used: 600.
![cormorant-italic](../docs/fonts/cormorant-italic.jpg)

### `dm-serif-italic` — DM Serif Display Italic  (lead)
Mood: bold high-contrast italic. Best for: lead-ins that must read on busy shots. Pairs with: `oswald-bold`.
![dm-serif-italic](../docs/fonts/dm-serif-italic.jpg)

### `share-tech-mono` — Share Tech Mono  (mono)
Mood: HUD / terminal. Best for: timecode, HUD labels, small captions. Pairs with: `orbitron-black`.
![share-tech-mono](../docs/fonts/share-tech-mono.jpg)

## Colours (`cue.color`)

Built in: `gold`, `red` (crimson), `blue` (neon blue), `cyan` (arc-reactor), `white`. Add your own in `project.json` → `colors`:
```json
"colors": {"pink": {"glow": "#FF2BD6", "core1": "#FFE6FA", "core2": "#FF6FE0"}}
```
`glow` = outer light, `core1` = top of the letters, `core2` = bottom (vertical gradient).

## Add a new font

1. Drop the `.ttf` (OFL/free licence only) into `fonts/` and its licence into `fonts/licenses/`.
2. Add an entry to `fonts/fonts.json` (`id`, `file`, `role`, optional `wght` for variable fonts, `mood`, `best_for`, `pairs_with`).
3. `python scripts/font_previews.py --frames <clip.mp4> 12 40 88` regenerates the previews.
