#!/usr/bin/env python3
r"""
verify_picks.py - one image per 30 slots: start / peak / end frame of every picked shot.
Look for a slot whose three frames show DIFFERENT shots -> its window crosses a hidden cut: tighten t0/t1.

    python verify_picks.py "D:\edits\spiderman"          uses proxy/ if present, else raw/
Writes sheets/verify_NN.jpg.  Only needs ffmpeg.
"""
import glob, json, os, subprocess, sys

def main():
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    picks = json.load(open(os.path.join(root, "picks.json"), encoding="utf-8"))
    vids = sorted(sum([glob.glob(os.path.join(root, d, e)) for d in ("raw", "raw video") for e in ("*.mp4", "*.mkv", "*.mov")], []))
    names = [os.path.basename(v).lower() for v in vids]
    tmp = os.path.join(root, "sheets", "_v"); os.makedirs(tmp, exist_ok=True)
    for f in glob.glob(os.path.join(tmp, "*.png")): os.remove(f)
    k = 0
    for e in picks:
        if not e.get("file"): continue
        vi = names.index(e["file"].lower())
        src = os.path.join(root, "proxy", f"v{vi + 1}.mp4")
        if not os.path.exists(src): src = vids[vi]
        for j, t in enumerate([e["t0"] + 0.05, e["peak"], e["t1"] - 0.08]):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1", "-vf",
                            f"scale=213:120:force_original_aspect_ratio=decrease,pad=213:120:(ow-iw)/2:(oh-ih)/2,"
                            f"drawtext=text='{e['slot']} {t:.1f}':x=3:y=3:fontsize=13:fontcolor=yellow:box=1:boxcolor=black",
                            os.path.join(tmp, f"{k:04d}.png")])
            k += 1
    n = 0
    for i in range(0, k, 90):
        out = os.path.join(root, "sheets", f"verify_{n + 1:02d}.jpg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-start_number", str(i), "-i", os.path.join(tmp, "%04d.png"),
                        "-frames:v", "1", "-vf", "tile=9x10", "-q:v", "4", out])
        n += 1
    print(f"[verify] {k // 3} slots -> {n} sheet(s) in sheets/verify_*.jpg")

if __name__ == "__main__":
    main()
