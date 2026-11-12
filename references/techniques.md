# Editing craft for mass / phonk / lyric edits

## 1. Music first
- **Window**: 35-40 s for reels, up to 60 s for YouTube. Start 2-5 s before a drop so the edit opens with tension. End on a hard stop (silence), a held vocal, or a drop-out.
- **Drop** = sudden energy + bass jump. **Break** = energy dip (music stops / filter sweep). Breaks are where slow-mo + lead words live; drops are where hard cuts live.
- **Beat grid**: cut on the grid that matches the feel. 120-130 BPM → cut every beat (≈0.47 s) in drops, every 2 beats in grooves. Half-time phonk (~88 BPM) → every beat = 0.68 s; add half-beat stutters.
- **Bass hits / 808s** often sit off the beat grid. `hits` forces a hard cut + shake + colour flash exactly there. Put the biggest word on the biggest hit.
- Never cut during a held word unless the music cuts too.

## 2. Lyric sync (no speech-to-text needed)
1. Get the lyrics from the user (they paste them). Find the hook line (the title word, repeated).
2. The chorus is the part that **repeats**: run `analyze_song.py --vocals` (Spleeter) for the vocal map, or look at the energy map for the same pattern appearing 2-3 times.
3. Inside the chorus, line starts follow musical stops or pitch jumps; held notes = long words (`VEERAAA`, `ASURAAA`).
4. Put the **lead word** (small italic) on the line start, the **slam word** on its stressed syllable. Show the word 0.05-0.1 s *before* the syllable for a punchy feel, never after.
5. Ask the user to confirm 1-2 times by ear ("does OMKAARA hit at 0:12.9?"). Shift a cue with `t` and `end`.
6. Phonk / instrumental: there are no words - slam title words on drops and 808 hits.

## 3. Shot choice (what makes goosebumps)
Ranked: (1) transformation / suit-up / mask on, (2) eyes or helmet lighting up, (3) landing / impact / explosion, (4) flight / swing / fall, (5) hero walk with fire behind, (6) blast / punch, (7) close-up stare, (8) wide city hero shot.
- **Story arc**: calm/identity (intro) → transformation (build) → action burst (drop) → stare/menace (break) → biggest hit (peak) → iconic hold (outro).
- **Peak frame** = the exact moment of impact; it lands on the cut. Slow-mo slots: peak in the middle; ramp slots: peak at 45 % (after the fast-in).
- Alternate scale: close → wide → close. Alternate direction of motion between adjacent cuts for energy, or keep it for flow.
- Avoid: talking-head dialogue, blurry transitions, logos/subtitles burned in, shots shorter in the source than the slot needs.
- Do not repeat a shot unless it is the hero shot used again at the end.

## 4. Movement and impact (engine does these; you tune them)
- **Zoom punch** at every cut (`zoom`), stronger on heavy beats. **Zoom-through transition**: last 3 frames zoom in on strong beats.
- **Camera shake** on bass hits and word slams, decays in 0.4 s (`shake`).
- **Speed ramps**: `ramp` slots = fast-in (2.1x) → slow-mo (0.38x) across the impact → kick-out (1.6x). `slow` slots = 0.42x with frame blending.
- **Flash frames**: white on word slams, colour on bass hits (`flash`, `hit_flash_color`).
- **RGB split** on heavy cut starts and on word entry (`chroma`).
- **Stutter**: groove sections randomly split a beat in two (half-beat repeat).

## 5. Kinetic typography
- **Pairing**: small italic serif lead-in (`theeyaai`, `the`, `avan`) docks above-left of the big slam word.
- **Slam**: 1.7x → 0.95x overshoot → 1.0 in 0.22 s, then slow grow; RGB split for 0.18 s; glow pulses on every beat; exit = scale up + fade in 0.16 s.
- **Echo grid** (`"grid": true`): outlined copies of the word tile the screen and flicker on beats - use on 2-4 biggest words only.
- 4-7 words per 38 s edit. One word on screen at a time. Lead + word together max 2 s.
- Colour logic: hero colour for the hero word (gold for Iron Man, crimson for Spider-Man), blue/cyan for "power/sense" words, white for neutral.

## 6. Orientation
- Read `video_report.txt` → orientation of every source.
- **Landscape source → 16:9 output**: letterbox bars are auto-cropped and the picture fills the frame.
- **Landscape → 9:16 reel**: centre crop keeps 31 % of the width; prefer shots where the subject is central or set `crop_focus`. Wide city shots lose most - use close-ups and vertical motion (falls, climbs).
- **Portrait source → 16:9**: heavy crop; avoid, or use 9:16 output.
- **Scope (2.39:1) source**: bars detected and removed; very wide shots get cut on the sides in 9:16.

## 7. Grade and polish
- Crush blacks a little, keep skin and hero colours alive. Vignette pulls the eye to centre text.
- Night footage: never stack a dark grade on a dark shot - pick `phonk-night` or `clean`.
- Fade in 0.25 s, fade out 0.6 s (automatic). Audio fades in/out too.
- Export: H.264 high, CRF 14 (≈40 Mbps 1080p) → Instagram/YouTube keep quality.
