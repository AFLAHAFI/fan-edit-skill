#!/usr/bin/env python3
r"""
make_sheets.py - turn long source videos into a few small contact sheets Claude can read cheaply.

    python make_sheets.py "D:\edits\spiderman"            sheets + cuts + report for every file in raw/
    python make_sheets.py "D:\edits\spiderman" --proxy    also write small proxies (640 px, 12 fps, no audio)

Output (inside the project folder):
    sheets/<name>_NN.jpg   6x5 thumbnails per sheet, timestamp burned in  (1 thumb per --step seconds)
    video_report.txt       per file: size, fps, duration, ORIENTATION, letterbox, scene-cut list
    proxy/<name>.mp4       (with --proxy) small copies under 20 MB, for verify_picks.py / uploading
Only needs ffmpeg + ffprobe on PATH (no Python packages).
"""
import argparse, glob, json, os, re, subprocess, sys

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def probe(p):
    j = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate:stream_tags=rotate:stream_side_data=rotation:format=duration",
                        "-of", "json", p]).stdout)
    st = j["streams"][0]
    w, h = int(st["width"]), int(st["height"])
    rot = 0
    try: rot = int(st.get("tags", {}).get("rotate", 0))
    except Exception: pass
    for sd in st.get("side_data_list", []) or []:
        if "rotation" in sd: rot = int(sd["rotation"])
    if abs(rot) in (90, 270): w, h = h, w
    n, d = st["r_frame_rate"].split("/")
    return dict(w=w, h=h, fps=round(float(n) / float(d or 1), 3), dur=float(j["format"]["duration"]))

def orientation(w, h):
    r = w / h
    if r > 1.9: return "landscape-scope (2.39:1 style)"
    if r > 1.2: return "landscape (16:9)"
    if r > 0.9: return "square (1:1)"
    if r > 0.7: return "portrait (4:5)"
    return "portrait (9:16 reel/short)"

def letterbox(p, dur):
    out = run(["ffmpeg", "-v", "info", "-ss", f"{dur * 0.3:.1f}", "-i", p, "-t", "20", "-vf", "fps=1,cropdetect=24:2:0",
               "-f", "null", "-"]).stderr
    m = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", out)
    return m[-1] if m else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--step", type=float, default=None, help="seconds per thumbnail (auto: 1-3 s)")
    ap.add_argument("--proxy", action="store_true")
    ap.add_argument("--cut", type=float, default=0.12, help="scene-cut sensitivity (lower = more cuts)")
    a = ap.parse_args()
    root = os.path.abspath(a.project)
    vids = sorted(sum([glob.glob(os.path.join(root, d, e)) for d in ("raw", "raw video") for e in ("*.mp4", "*.mkv", "*.mov")], []))
    if not vids: sys.exit("no videos in raw/")
    os.makedirs(os.path.join(root, "sheets"), exist_ok=True)
    rep = []
    for vi, v in enumerate(vids):
        info = probe(v); base = f"v{vi + 1}"
        ori = orientation(info["w"], info["h"])
        step = a.step or (1.0 if info["dur"] < 240 else 2.0 if info["dur"] < 600 else 3.0)
        port = info["h"] > info["w"]
        tw, th, cols, rows = (180, 320, 10, 3) if port else (320, 180, 6, 5)
        font = ""
        for fp in [os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts", "ShareTechMono-Regular.ttf"),
                   r"C:\Windows\Fonts\consola.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]:
            if os.path.exists(fp):
                font = "fontfile='" + fp.replace("\\", "/").replace(":", "\\:") + "':"; break
        vf = (f"fps=1/{step},scale={tw}:{th}:force_original_aspect_ratio=decrease,pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2,"
              f"drawtext={font}text='{base} %{{pts\\:hms}}':x=3:y=3:fontsize=15:fontcolor=yellow:box=1:boxcolor=black@0.6,"
              f"tile={cols}x{rows}")
        print(f"[sheets] {os.path.basename(v)}  {info['w']}x{info['h']} {ori}  {info['dur']:.0f}s  step {step}s")
        run(["ffmpeg", "-v", "error", "-y", "-i", v, "-an", "-vf", vf, "-q:v", "5",
             os.path.join(root, "sheets", f"{base}_%02d.jpg")])
        sc = run(["ffmpeg", "-i", v, "-an", "-vf", f"scale=320:-2,select='gt(scene,{a.cut})',showinfo", "-f", "null", "-"]).stderr
        cuts = [round(float(x), 2) for x in re.findall(r"pts_time:([0-9.]+)", sc)]
        lb = letterbox(v, info["dur"])
        if a.proxy:
            os.makedirs(os.path.join(root, "proxy"), exist_ok=True)
            run(["ffmpeg", "-v", "error", "-y", "-i", v, "-an", "-vf", f"scale={'360:-2' if port else '640:-2'},fps=12",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "30", os.path.join(root, "proxy", f"{base}.mp4")])
        rep.append(f"{base} = {os.path.basename(v)}\n  {info['w']}x{info['h']}  {ori}  {info['fps']} fps  {info['dur']:.1f}s"
                   f"\n  letterbox(cropdetect)={lb}\n  scene cuts ({len(cuts)}): {' '.join(map(str, cuts))}")
    txt = "\n".join(rep)
    open(os.path.join(root, "video_report.txt"), "w", encoding="utf-8").write(txt)
    print(txt)
    print(f"[sheets] {len(glob.glob(os.path.join(root, 'sheets', '*.jpg')))} sheets in sheets/")

if __name__ == "__main__":
    main()
