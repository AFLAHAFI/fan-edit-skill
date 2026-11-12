#!/usr/bin/env python3
r"""
font_previews.py - render every font in fonts/fonts.json in the real edit style (glow, lead-in, echo grid).

    python font_previews.py bg1.jpg bg2.jpg ...      backgrounds = any frames you like (screenshots from your clips)
    python font_previews.py --frames "D:\edits\spiderman\raw\clip.mp4" 12.5 40 88   grab frames from a video

Writes docs/fonts/<font-id>.jpg (960x540) and docs/fonts/_board.jpg (all fonts on one image).
"""
import argparse, json, os, subprocess, sys
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import massedit as M

SAMPLES = {  # impact word, lead word
    "impact": [("VEERA", "theeyaai"), ("AMAZING", "the"), ("ASURAA", "avan"), ("POWER", "with great"), ("OMKAARA", "veezha")],
}
COLS = ["gold", "red", "blue", "white", "cyan"]

def frames_from_video(path, times, out_dir):
    res = []
    for i, t in enumerate(times):
        p = os.path.join(out_dir, f"_bg{i}.jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", path, "-frames:v", "1", p])
        res.append(p)
    return res

def background(path, W, H):
    im = cv2.imread(path)
    im = cv2.resize(im, (W, H), interpolation=cv2.INTER_CUBIC)
    im = cv2.GaussianBlur(im, (0, 0), 1.2)
    lut, vig = M.make_grade(W, H)
    im = M.grade(im, lut, vig)
    return (im.astype(np.float32) * 0.62).astype(np.uint8)   # darken so the type is the hero

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bgs", nargs="*")
    ap.add_argument("--frames", nargs="+", help="video then times")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "docs", "fonts"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    bgs = a.bgs or (frames_from_video(a.frames[0], [float(x) for x in a.frames[1:]], a.out) if a.frames else [])
    if not bgs: sys.exit("give background images or --frames video t1 t2 ...")
    W, H = 960, 540
    s = H / 1080.0
    fonts = json.load(open(os.path.join(HERE, "..", "fonts", "fonts.json"), encoding="utf-8"))
    leads = [f for f in fonts if f["role"] == "lead"]
    mono = M.font_spec("share-tech-mono")
    M.STYLE["grade"] = "phonk-night"
    tiles = []
    for i, f in enumerate(fonts):
        bg = background(bgs[i % len(bgs)], W, H)
        col = COLS[i % len(COLS)]
        spec = M.font_spec(f["id"])
        if f["role"] == "impact":
            word, lead = SAMPLES["impact"][i % 5]
            lspec = M.font_spec(f.get("pairs_with", "playfair-italic"))
            M.FONT_IMPACT = spec
            grid = M.make_echo_grid(word, col, W, H)
            bg = np.clip(bg.astype(np.float32) + grid * 0.22, 0, 255).astype(np.uint8)
            big = M.Sprite(word, spec, int(300 * s), col, tracking=int(10 * s))
            fit = min(1.0, (W * 0.84) / big.w)
            M.blit(bg, big, W / 2, H * 0.55, fit, 1.0, glow=1.2, rgb_split=3, shadow=0.65)
            sm = M.Sprite(lead, lspec, int(96 * s), "white", tracking=int(4 * s))
            left = W / 2 - big.text_w * fit / 2
            M.blit(bg, sm, left + sm.text_w * 0.85 / 2 + 6, H * 0.55 - big.size * fit * 0.62 - 18, 0.85, 1.0, glow=0.6, shadow=0.5)
        elif f["role"] == "lead":
            pair = M.font_spec(f.get("pairs_with", "anton"))
            sm = M.Sprite("theeyaai eriyum", spec, int(150 * s), "white", tracking=int(4 * s))
            M.blit(bg, sm, W / 2, H * 0.42, min(1.0, W * 0.8 / sm.w), 1.0, glow=0.9, shadow=0.5)
            big = M.Sprite("OMKAARA", pair, int(220 * s), col, tracking=int(8 * s))
            M.blit(bg, big, W / 2, H * 0.66, min(1.0, W * 0.7 / big.w), 1.0, glow=1.1, shadow=0.6)
        else:
            sm = M.Sprite("00:00:12:08   REC", spec, int(110 * s), "cyan")
            M.blit(bg, sm, W / 2, H * 0.5, min(1.0, W * 0.8 / sm.w), 1.0, glow=0.8, shadow=0.5)
        # label strip
        cv2.rectangle(bg, (0, H - 46), (W, H), (0, 0, 0), -1)
        lab = M.Sprite(f"{f['id']}  |  {f['role']}  |  {f['mood']}", mono, 26, "white")
        M.blit(bg, lab, lab.w * 0.5 + 4, H - 23, 1.0, 1.0, glow=0.0)
        out = os.path.join(a.out, f"{f['id']}.jpg")
        cv2.imwrite(out, bg, [cv2.IMWRITE_JPEG_QUALITY, 86])
        tiles.append(cv2.resize(bg, (480, 270), interpolation=cv2.INTER_AREA))
        print("[fonts]", out)
    while len(tiles) % 4: tiles.append(np.zeros_like(tiles[0]))
    rows = [np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]
    cv2.imwrite(os.path.join(a.out, "_board.jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])
    print("[fonts] board ->", os.path.join(a.out, "_board.jpg"))

if __name__ == "__main__":
    main()
