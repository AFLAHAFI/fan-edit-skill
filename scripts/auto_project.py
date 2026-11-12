#!/usr/bin/env python3
r"""
auto_project.py - write a ready project.json from analyze_song.py output (no Claude needed).

    python auto_project.py "D:\edits\myedit" --preset phonk-night --aspect 9:16 --words "AMAZING,SPIDER-MAN,POWER"

Needs project.suggest.json + beats.json (run analyze_song.py first).
Words: one per cue slot (drop + strongest bass hits). Prefix a small lead word with "/":  "the/AMAZING,with great/POWER"
No --words: uses the song title (from the file name) on the first and last cue.
"""
import argparse, glob, json, os, re

PRESETS = {
    "mass-hero":         dict(grade="teal-orange", impact_font="anton", lead_font="playfair-italic", zoom=1.2, shake=1.0,
                              flash=1.0, hit_flash_color="#FFB020", _colors=["gold", "red", "cyan"]),
    "phonk-night":       dict(grade="phonk-night", impact_font="russo-one", lead_font="instrument-serif", shake=1.2,
                              chroma=1.3, hit_flash_color="#E61E28", _colors=["white", "red", "blue"]),
    "cinematic-trailer": dict(grade="cold-steel", impact_font="bebas-neue", lead_font="cormorant-italic", zoom=0.6,
                              shake=0.4, flash=0.6, letterbox=True, grid=0.0, _colors=["white", "gold"]),
    "emotional":         dict(grade="warm-gold", impact_font="permanent-marker", lead_font="cormorant-italic", zoom=0.4,
                              shake=0.2, flash=0.3, chroma=0.0, grid=0.0, grain=0.6, _colors=["white", "gold"]),
    "anime-hype":        dict(grade="clean", impact_font="unbounded-black", lead_font="instrument-serif", zoom=1.3,
                              shake=1.3, chroma=1.5, grid=1.2, _colors=["blue", "white", "red"]),
    "villain-glitch":    dict(grade="cold-steel", impact_font="rubik-glitch", lead_font="cormorant-italic", chroma=2.0,
                              shake=1.2, hit_flash_color="#C00010", _colors=["red", "white"]),
    "retro-synthwave":   dict(grade="vhs-retro", impact_font="monoton", lead_font="dm-serif-italic", grain=1.8,
                              chroma=1.2, zoom=0.7, _colors=["cyan", "red", "white"]),
}
LEVELS = {"minimal": dict(zoom=0.4, shake=0.3, flash=0.0, chroma=0.0), "medium": dict(zoom=0.8, shake=0.8, flash=0.7, chroma=0.8),
          "heavy": dict(zoom=1.2, shake=1.2, flash=1.0, chroma=1.3)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--preset", default="mass-hero", choices=list(PRESETS))
    ap.add_argument("--aspect", default="16:9")
    ap.add_argument("--words", default="")
    ap.add_argument("--level", default="", choices=["", "minimal", "medium", "heavy"])
    ap.add_argument("--name", default="")
    a = ap.parse_args()
    root = os.path.abspath(a.project)
    sug = json.load(open(os.path.join(root, "project.suggest.json"), encoding="utf-8"))
    style = dict(PRESETS[a.preset]); cols = style.pop("_colors")
    if a.level: style.update(LEVELS[a.level])
    slots = sug.get("cue_slots", [])
    if a.words.strip():
        words = [w.strip() for w in a.words.split(",") if w.strip()]
    else:
        songs = glob.glob(os.path.join(root, "song", "*.*"))
        t = os.path.splitext(os.path.basename(songs[0]))[0] if songs else "EDIT"
        t = re.sub(r"\(.*?\)|\[.*?\]", "", t).split("-")[-1].strip().split()
        title = (t[0] if t else "EDIT").upper()
        words = [title] if len(slots) < 2 else [title] + [""] * (len(slots) - 2) + [title]
    cues = []
    for i, (sl, w) in enumerate(zip(slots, words)):
        if not w: continue
        lead, _, big = w.rpartition("/")
        nxt = slots[i + 1]["t"] if i + 1 < len(slots) else sug["song"]["duration"]
        c = dict(word=big.upper(), t=sl["t"], end=round(min(nxt - 0.05, sl["t"] + 2.2, sug["song"]["duration"]), 3),
                 color=cols[i % len(cols)], grid=(i % 2 == 0 and style.get("grid", 1.0) > 0))
        if lead:
            c["lead"] = lead; c["lead_t"] = round(max(0.0, sl["t"] - 1.4), 3)
        cues.append(c)
    name = a.name or f"{os.path.basename(root)}_{a.preset}_{a.aspect.replace(':', 'x')}.mp4"
    proj = dict(title=os.path.basename(root), song=sug["song"],
                output=dict(aspect=a.aspect, fps=30, crf=14, name=name),
                style=style, hud=dict(enabled=False), sections=sug["sections"], hits=sug.get("hits", []), cues=cues)
    p = os.path.join(root, "project.json")
    if os.path.exists(p):
        os.replace(p, p + ".bak")
    json.dump(proj, open(p, "w", encoding="utf-8"), indent=1)
    print(f"[auto] project.json written: preset {a.preset}, {a.aspect}, {len(cues)} words -> {name}")

if __name__ == "__main__":
    main()
