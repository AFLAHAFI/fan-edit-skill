#!/usr/bin/env python3
r"""
massedit.py - beat-synced cinematic "mass" fan-edit renderer (part of the mass-fan-edit skill)
================================================================================================
Project folder layout (pass it with --project, default = current folder):
    project.json   all creative settings (song window, cues, sections, style, fonts, aspect)
    beats.json     beat map  (scripts/analyze_song.py writes it)
    picks.json     hand-picked shots per slot (optional; without it the script auto-scans)
    raw/           source video clips (.mp4/.mkv)   ("raw video/" also accepted)
    song/          the song (.mp3/.wav)

Run:
    python massedit.py --project "D:\edits\spiderman" --preview     fast draft (half size)
    python massedit.py --project "D:\edits\spiderman"               final render
    python massedit.py --project ... --dump-plan                     print slot list (for picking shots)
Requires: ffmpeg on PATH, pip install numpy opencv-python pillow
"""
import os, sys, json, glob, math, subprocess, argparse, random, shutil, time
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
HERE_PROJECT = os.getcwd()

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
AUDIO_START = 0.0         # overridden by project.json song.start
DURATION    = 38.0        # final length
FPS         = 30
W, H        = 1920, 1080
OUT_NAME    = "MassEdit_1080p.mp4"
CRF         = 14          # x264 quality (lower = higher bitrate)
MAXRATE     = "40M"
SEED        = 7

# Lyric cues (edit-timeline seconds). lead = small italic serif lead-in,
# word = massive glowing impact word. color: gold | red | cyan
CUES = []          # filled from project.json
LEAD_COLOR = "white"
EXTRA_HITS = []    # bass slams (project.json "hits")
HUD_TITLE  = ""
HUD_SUB    = ""
HUD_BR     = ""
HUD_ACCENT = (40, 30, 235)           # crimson (BGR)
MIN_BRIGHT = 0.035                   # keep dark night shots in auto-scan
HUD_ENABLED = False                  # no viewfinder / timecode / beat bar (clean reel look)
SECTIONS = [  # (start, end, mode) in edit time
    (0.0,   4.881, "intro"),     # quiet break: spidey-sense slow-mo
    (4.881, 15.84, "drop"),      # drop: hard cut every beat
    (15.84, 26.80, "groove"),    # 2-beat speed ramps + half-beat stutters
    (26.80, 37.52, "drop"),      # final hard cuts
    (37.52, 38.0,  "outro"),     # hard stop + fade
]

COLORS = {  # BGR for glow, core top, core bottom
    "gold": dict(glow=(10, 140, 255), core1=(200, 245, 255), core2=(20, 170, 255)),
    "white": dict(glow=(255, 200, 150), core1=(255, 255, 255), core2=(235, 235, 245)),
    "blue": dict(glow=(255, 120, 10), core1=(255, 245, 220), core2=(255, 170, 40)),
    "red":  dict(glow=(30, 10, 230),  core1=(200, 210, 255), core2=(40, 20, 220)),
    "cyan": dict(glow=(255, 220, 30), core1=(255, 255, 235), core2=(255, 225, 60)),
}

STYLE = dict(grade="teal-orange", impact_font="anton", lead_font="playfair-italic", mono_font="share-tech-mono",
             text_y=0.52, text_size=1.0, shake=1.0, zoom=1.0, flash=1.0, chroma=1.0, grain=1.0, grid=1.0,
             letterbox=False, crop_focus=[0.5, 0.5], flash_color="#FFFFFF", hit_flash_color="#E61E28")
ASPECTS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350), "21:9": (2560, 1080)}

def _hex_bgr(h):
    h = h.lstrip("#"); return (int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16))

def load_project(root):
    """Override the defaults above with project.json."""
    global AUDIO_START, DURATION, FPS, W, H, OUT_NAME, CRF, CUES, SECTIONS, LEAD_COLOR, EXTRA_HITS
    global HUD_TITLE, HUD_SUB, HUD_BR, HUD_ENABLED, MIN_BRIGHT, SEED
    p = os.path.join(root, "project.json")
    if not os.path.exists(p):
        sys.exit(f"project.json not found in {root}")
    j = json.load(open(p, encoding="utf-8"))
    sg = j.get("song", {}); AUDIO_START = float(sg.get("start", AUDIO_START)); DURATION = float(sg.get("duration", DURATION))
    o = j.get("output", {})
    W, H = ASPECTS.get(o.get("aspect", "16:9"), (1920, 1080))
    FPS = int(o.get("fps", FPS)); CRF = int(o.get("crf", CRF)); OUT_NAME = o.get("name", OUT_NAME)
    STYLE.update(j.get("style", {}))
    LEAD_COLOR = STYLE.get("lead_color", LEAD_COLOR)
    hud = j.get("hud", {}); HUD_ENABLED = bool(hud.get("enabled", False))
    HUD_TITLE = hud.get("title", HUD_TITLE); HUD_SUB = hud.get("sub", ""); HUD_BR = hud.get("br", "")
    global HUD_ACCENT
    if hud.get("accent"): HUD_ACCENT = _hex_bgr(hud["accent"])
    for name, c in j.get("colors", {}).items():
        COLORS[name] = dict(glow=_hex_bgr(c["glow"]), core1=_hex_bgr(c["core1"]), core2=_hex_bgr(c["core2"]))
    CUES = j.get("cues", CUES)
    for c in CUES:
        c.setdefault("lead", None); c.setdefault("lead_t", None); c.setdefault("grid", False); c.setdefault("color", "white")
    SECTIONS = [tuple(x) for x in j.get("sections", SECTIONS)]
    EXTRA_HITS = [float(x) for x in j.get("hits", EXTRA_HITS)]
    MIN_BRIGHT = float(j.get("min_bright", MIN_BRIGHT)); SEED = int(j.get("seed", SEED))
    return j

FONT_DB = {}
def font_spec(fid):
    """font id (fonts/fonts.json) or file name -> 'path|weight'"""
    if not FONT_DB:
        for d in [os.path.join(HERE, "fonts"), os.path.join(HERE, "..", "fonts")]:
            fj = os.path.join(d, "fonts.json")
            if os.path.exists(fj):
                for e in json.load(open(fj, encoding="utf-8")):
                    FONT_DB[e["id"]] = (os.path.join(d, e["file"]), e.get("wght"))
                break
    if fid in FONT_DB:
        path, w = FONT_DB[fid]
        return f"{path}|{w or ''}"
    p = find_font([fid])
    return f"{p}|" if p else None

def load_font(spec, size):
    path, _, w = spec.partition("|")
    f = ImageFont.truetype(path, size)
    if w:
        try: f.set_variation_by_axes([float(w)])
        except Exception: pass
    return f

# ----------------------------------------------------------------------------
# utilities
# ----------------------------------------------------------------------------
def log(*a):
    print("[massedit]", *a, flush=True)

def ffmpeg_bin(name="ffmpeg"):
    p = shutil.which(name)
    if not p:
        sys.exit(f"{name} not found on PATH. Install FFmpeg (https://www.gyan.dev/ffmpeg/builds/) and add its bin folder to PATH.")
    return p

def probe(path):
    out = subprocess.run([ffmpeg_bin("ffprobe"), "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "stream=width,height,r_frame_rate:format=duration",
                          "-of", "json", path], capture_output=True, text=True).stdout
    j = json.loads(out)
    st = j["streams"][0]
    num, den = st["r_frame_rate"].split("/")
    return dict(w=int(st["width"]), h=int(st["height"]),
                fps=float(num) / float(den or 1), dur=float(j["format"]["duration"]))

def find_font(cands):
    dirs = [os.path.join(HERE, "fonts"), os.path.join(HERE, "..", "fonts"), r"C:\Windows\Fonts",
            os.path.expanduser(r"~\AppData\Local\Microsoft\Windows\Fonts"),
            "/usr/share/fonts", "/Library/Fonts"]
    for c in cands:
        for d in dirs:
            p = os.path.join(d, c)
            if os.path.exists(p):
                return p
        for d in dirs:
            hits = glob.glob(os.path.join(d, "**", c), recursive=True) if os.path.isdir(d) else []
            if hits:
                return hits[0]
    return None

FONT_IMPACT = None
FONT_SERIF_IT = None
FONT_MONO = None

def ease_out(x):  # cubic
    x = min(max(x, 0.0), 1.0); return 1 - (1 - x) ** 3

def ease_in(x):
    x = min(max(x, 0.0), 1.0); return x ** 3

def clamp(x, a, b):
    return a if x < a else b if x > b else x

# ----------------------------------------------------------------------------
# 1. AUDIO
# ----------------------------------------------------------------------------
def load_beats(song):
    bj = os.path.join(HERE_PROJECT, "beats.json")
    if os.path.exists(bj):
        j = json.load(open(bj))
        if abs(j.get("start", -1) - AUDIO_START) < 1e-3:
            log(f"beat map: beats.json ({len(j['beats'])} beats, {j['bpm']:.1f} BPM)")
            return j
    log("computing beat map with librosa ...")
    import librosa
    off, hop = 4.0, 256
    y, sr = librosa.load(song, sr=22050, offset=AUDIO_START - off, duration=DURATION + 2 * off)
    oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    tempo, bf = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=hop, start_bpm=129, tightness=200)
    bt = librosa.frames_to_time(bf, sr=sr, hop_length=hop) - off
    S = np.abs(librosa.stft(y, hop_length=hop, n_fft=2048)); f = librosa.fft_frequencies(sr=sr, n_fft=2048)
    low = librosa.amplitude_to_db(S[(f > 30) & (f < 140)], ref=np.max)
    benv = np.r_[0, np.maximum(0, np.diff(low, axis=1)).mean(0)]
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    beats = [float(t) for t in bt if 0 <= t < DURATION]
    bs, rr = [], []
    for t in beats:
        i = int((t + off) * sr / hop)
        bs.append(benv[max(0, i - 3):i + 4].max()); rr.append(rms[i:i + 20].mean())
    bs = np.array(bs) / max(bs); rr = np.array(rr) / max(rr)
    j = dict(start=AUDIO_START, duration=DURATION, bpm=float(np.atleast_1d(tempo)[0]),
             beats=[round(t, 3) for t in beats], beat_strength=[round(float(v), 3) for v in 0.6 * bs + 0.4 * rr])
    json.dump(j, open(bj, "w"))
    return j

def cut_audio(song, out_wav):
    subprocess.run([ffmpeg_bin(), "-v", "error", "-y", "-ss", f"{AUDIO_START}", "-t", f"{DURATION}", "-i", song,
                    "-af", f"afade=t=in:st=0:d=0.25,afade=t=out:st={DURATION-1.4}:d=1.4",
                    "-ar", "48000", "-ac", "2", out_wav], check=True)

# ----------------------------------------------------------------------------
# 2. SCAN
# ----------------------------------------------------------------------------
SCAN_FPS = 6
SW, SH = 256, 144

def scan_video(path, cache):
    st = os.stat(path)
    key = f"{os.path.basename(path)}|{st.st_size}|{int(st.st_mtime)}|v3"
    if key in cache:
        log(f"scan cache hit: {os.path.basename(path)}")
        return cache[key]
    info = probe(path)
    log(f"scanning {os.path.basename(path)}  ({info['dur']/60:.1f} min, {info['w']}x{info['h']}) ...")
    cmd = [ffmpeg_bin(), "-v", "error", "-i", path, "-an", "-sn",
           "-vf", f"fps={SCAN_FPS},scale={SW}:{SH}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=SW * SH * 3 * 8)
    face = None
    for cp in [os.path.join(HERE, "haarcascade_frontalface_default.xml"),
               os.path.join(HERE, "..", "assets", "haarcascade_frontalface_default.xml"),
               os.path.join(getattr(getattr(cv2, "data", None), "haarcascades", ""), "haarcascade_frontalface_default.xml")]:
        if os.path.exists(cp):
            face = cv2.CascadeClassifier(cp)
            if face.empty(): face = None
            else: break
    if face is None: log("   (face detector unavailable - close-up detection off)")
    fs = SW * SH * 3
    feats, rowmeans = [], []
    prev_g, prev_h = None, None
    i, t0 = 0, time.time()
    while True:
        buf = p.stdout.read(fs)
        if len(buf) < fs: break
        fr = np.frombuffer(buf, np.uint8).reshape(SH, SW, 3)
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        rowmeans.append(g.mean(1))
        hsv = cv2.cvtColor(fr, cv2.COLOR_BGR2HSV)
        hh, ss, vv = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        hist = cv2.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256]); cv2.normalize(hist, hist)
        cut = 0.0; mot = 0.0
        if prev_g is not None:
            cut = 1.0 - cv2.compareHist(prev_h, hist, cv2.HISTCMP_CORREL)
            mot = float(cv2.absdiff(g, prev_g).mean()) / 255.0
        bright = float(vv.mean()) / 255.0
        hot = float((vv > 235).mean())
        cyan = float(((hh > 82) & (hh < 112) & (ss > 60) & (vv > 170)).mean() + 0.5 * ((vv > 245) & (ss < 60) & (hh > 80) & (hh < 115)).mean())
        warm = float((((hh < 12) | (hh > 168)) & (ss > 120) & (vv > 70)).mean() + 0.8 * ((hh >= 12) & (hh < 30) & (ss > 110) & (vv > 120)).mean())
        fsz = 0.0
        if face is not None and i % 3 == 0:
            fc = face.detectMultiScale(g, 1.15, 4, minSize=(22, 22))
            if len(fc): fsz = float(max(w * h for (_, _, w, h) in fc)) / (SW * SH)
        feats.append([i / SCAN_FPS, cut, mot, bright, float(g.std()) / 128.0, hot, cyan, warm, fsz])
        prev_g, prev_h = g, hist
        i += 1
        if i % (SCAN_FPS * 120) == 0:
            el = time.time() - t0
            log(f"   {i/SCAN_FPS/60:5.1f} min scanned  ({i/SCAN_FPS/max(el,1e-3):.0f}x realtime)")
    p.wait()
    rm = np.array(rowmeans)
    # letterbox detect: rows that stay dark in 97% of frames
    dark_rows = (np.percentile(rm, 97, axis=0) < 22)
    top = 0
    while top < SH // 3 and dark_rows[top]: top += 1
    bot = 0
    while bot < SH // 3 and dark_rows[SH - 1 - bot]: bot += 1
    res = dict(path=path, info=info, feats=feats,
               crop_top=top / SH, crop_bot=bot / SH)
    log(f"   done: {len(feats)} samples, letterbox top {top/SH:.1%} bottom {bot/SH:.1%}")
    cache[key] = res
    return res

def quick_scan(path):
    """Letterbox detection only (for picks.json mode): ~24 sampled frames."""
    info = probe(path)
    rows = []
    for k in range(24):
        t = info["dur"] * (k + 0.5) / 24
        out = subprocess.run([ffmpeg_bin(), "-v", "error", "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1",
                              "-vf", f"scale={SW}:{SH}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                             capture_output=True).stdout
        if len(out) == SW * SH:
            rows.append(np.frombuffer(out, np.uint8).reshape(SH, SW).mean(1))
    top = bot = 0
    if rows:
        dark = np.percentile(np.array(rows), 90, axis=0) < 22
        while top < SH // 3 and dark[top]: top += 1
        while bot < SH // 3 and dark[SH - 1 - bot]: bot += 1
    log(f"   {os.path.basename(path)}: {info['dur']:.1f}s, letterbox top {top/SH:.1%} bottom {bot/SH:.1%}")
    return dict(path=path, info=info, feats=[], crop_top=top / SH, crop_bot=bot / SH)

def find_shots(scan, vid):
    F = np.array(scan["feats"])
    if len(F) < 10: return []
    t, cut, mot = F[:, 0], F[:, 1], F[:, 2]
    # adaptive cut threshold
    thr = max(0.35, np.percentile(cut, 97))
    bounds = [0] + [i for i in range(1, len(F)) if cut[i] > thr and mot[i] > 0.04] + [len(F)]
    # long shots -> ~2.5 s candidate windows, each with its own peak moment
    win = int(2.5 * SCAN_FPS)
    segs = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        if b - a > 2 * win:
            k = a
            while k + win <= b:
                segs.append((k, min(b, k + win + 2))); k += win
        else:
            segs.append((a, b))
    shots = []
    for a, b in segs:
        a2, b2 = a + 1, b - 1                      # trim samples around the cut
        if (b2 - a2) / SCAN_FPS < 0.7: continue
        seg = F[a2:b2]
        m = seg[:, 2]
        bright = seg[:, 3].mean()
        if bright < MIN_BRIGHT: continue           # black / near-black
        mp90 = np.percentile(m, 90)
        flash = max(0.0, seg[:, 5].max() - np.median(seg[:, 5]))
        cyan = np.percentile(seg[:, 6], 90)
        warm = np.percentile(seg[:, 7], 75)
        face = seg[:, 8].max()
        # landing: high motion that drops sharply
        land = 0.0
        if len(m) > 6:
            k = 3
            for j in range(k, len(m) - k):
                before, after = m[j - k:j].mean(), m[j:j + k].mean()
                land = max(land, before - 1.8 * after)
        contrast = seg[:, 4].mean()
        static = 1.0 if mp90 < 0.012 else 0.0
        shot = dict(vid=vid, t0=float(t[a2]), t1=float(t[b2 - 1]) + 1.0 / SCAN_FPS,
                    motion=float(mp90), flash=float(flash), cyan=float(cyan), warm=float(warm),
                    face=float(face), land=float(land), contrast=float(contrast), bright=float(bright),
                    static=static)
        # peak moment (max of motion + flash + cyan)
        pk = m / (m.max() + 1e-6) + 2 * seg[:, 5] + 3 * seg[:, 6]
        shot["peak"] = float(seg[int(np.argmax(pk)), 0])
        shots.append(shot)
    return shots

def score_shots(shots):
    if not shots: return
    def nz(k):
        v = np.array([s[k] for s in shots]); hi = np.percentile(v, 95) + 1e-6
        return np.clip(v / hi, 0, 1.2)
    M, FL, C, WA, FA, LA, CO = (nz(k) for k in ("motion", "flash", "cyan", "warm", "face", "land", "contrast"))
    for i, s in enumerate(shots):
        s["blast"] = float(0.55 * C[i] + 0.45 * FL[i])
        s["action"] = float(0.6 * M[i] + 0.4 * LA[i])
        s["closeup"] = float(FA[i])
        s["suit"] = float(WA[i])
        s["score"] = float(1.0 * M[i] + 1.1 * C[i] + 0.8 * FL[i] + 0.7 * WA[i] + 0.6 * FA[i] + 0.8 * LA[i]
                           + 0.3 * CO[i] - 1.2 * s["static"])
        s["calm_score"] = float(1.2 * FA[i] + 0.9 * WA[i] + 0.6 * C[i] + 0.4 * CO[i] - 0.3 * M[i])
        tags = []
        if C[i] > 0.6 or FL[i] > 0.7: tags.append("blast")
        if WA[i] > 0.6: tags.append("suit")
        if FA[i] > 0.5: tags.append("closeup")
        if LA[i] > 0.6: tags.append("landing")
        if M[i] > 0.7: tags.append("action")
        s["tags"] = tags

# ----------------------------------------------------------------------------
# 3. PLAN
# ----------------------------------------------------------------------------
def build_slots(beats, strength):
    B = np.array(beats); Sg = np.array(strength)
    def bstr(t):
        if len(B) == 0: return 0.5
        i = int(np.argmin(abs(B - t))); return float(Sg[i]) if abs(B[i] - t) < 0.08 else 0.4
    slots = []
    rng = random.Random(SEED)
    for (a, b, mode) in SECTIONS:
        inner = [t for t in B if a + 0.05 < t < b - 0.05]
        if mode in ("intro",):
            pts = [a] + [t for t in inner if t > a + 0.8][:1] + [b]
            for x, y in zip(pts[:-1], pts[1:]):
                slots.append(dict(t0=x, t1=y, kind="calm", ramp="slow", hit=bstr(x)))
        elif mode in ("break", "outro"):
            slots.append(dict(t0=a, t1=b, kind="calm", ramp="slow", hit=bstr(a)))
        elif mode == "black":
            slots.append(dict(t0=a, t1=b, kind="black", ramp="none", hit=0.0))
        else:
            pts = [a] + inner + [b]
            i = 0
            while i < len(pts) - 1:
                x = pts[i]
                if mode == "drop":
                    step = 1
                else:  # groove: mix of 2-beat ramps, 1-beat cuts and half-beat stutters
                    r = rng.random()
                    step = 2 if r < 0.35 else 1
                    if r > 0.88 and i + 1 < len(pts):
                        mid = (pts[i] + pts[i + 1]) / 2
                        slots.append(dict(t0=x, t1=mid, kind="hit", ramp="normal", hit=bstr(x), stutter=True))
                        slots.append(dict(t0=mid, t1=pts[i + 1], kind="hit", ramp="normal", hit=0.55, stutter=True))
                        i += 1; continue
                j = min(i + step, len(pts) - 1)
                y = pts[j]
                slots.append(dict(t0=x, t1=y, kind="hit", ramp="ramp" if y - x > 0.8 else "normal", hit=bstr(x)))
                i = j
    # force a hard cut on every 808 / drop hit (they sit off the hi-hat grid)
    for h in EXTRA_HITS:
        for i, sl in enumerate(slots):
            if sl["t0"] + 0.15 < h < sl["t1"] - 0.15:
                a = dict(sl); b = dict(sl)
                a["t1"] = h; b["t0"] = h; b["hit"] = 1.0
                b["ramp"] = "normal" if b["kind"] == "hit" else b["ramp"]
                slots[i:i + 1] = [a, b]
                break
    # merge slivers (< 0.2 s) into the previous slot
    out = []
    for sl in slots:
        if out and sl["t1"] - sl["t0"] < 0.2 and sl["kind"] == out[-1]["kind"]:
            out[-1]["t1"] = sl["t1"]
        else:
            out.append(sl)
    return out

def assign(slots, shots, picks=None):
    if picks:
        for s, p in zip(slots, picks):
            s.update(p)
        return slots
    used = []
    def near(sh):
        return sum(1 for u in used if u["vid"] == sh["vid"] and abs(u["peak"] - sh["peak"]) < 4.0)
    def take(cands, keyf):
        if not cands: return None
        best = min(cands, key=lambda x: (near(x), -keyf(x)))   # unused first, then best score
        used.append(best); return best
    order = sorted(range(len(slots)), key=lambda i: (slots[i]["kind"] != "calm", -slots[i]["hit"]))
    lastvid = None
    for i in order:
        s = slots[i]
        if s["kind"] == "black": continue
        if s["kind"] == "calm":
            sh = take(shots, lambda x: x["calm_score"])
        else:
            heavy = s["hit"] > 0.62
            if heavy:
                sh = take(shots, lambda x: x["score"] + 0.8 * x["blast"] + 0.6 * x["action"])
            else:
                sh = take(shots, lambda x: x["score"] + 0.15 * (x["vid"] != lastvid))
        if sh is None: continue
        lastvid = sh["vid"]
        s["shot"] = sh
    return slots

def source_window(s, slot_len):
    """Returns (src_start, mapping fn u->src offset) for slot."""
    sh = s["shot"]
    ramp = s["ramp"]
    if ramp == "slow":
        speed = lambda u: 0.42
    elif ramp == "ramp":     # fast in, slam to slow-mo at the impact, then kick out
        speed = lambda u: 2.1 if u < 0.3 else (0.38 if u < 0.85 else 1.6)
    else:
        speed = lambda u: 1.0 if not s.get("stutter") else 1.25
    n = 64
    us = np.linspace(0, 1, n + 1)
    sp = np.array([speed(u) for u in us])
    disp = np.concatenate([[0], np.cumsum((sp[1:] + sp[:-1]) / 2 * (slot_len / n))])
    span = disp[-1]
    shot_len = sh["t1"] - sh["t0"] - 0.1
    k = 1.0
    if span > shot_len:
        k = shot_len / span; disp *= k; span = shot_len
    # put the peak at the slow part (u ~ 0.45) or at the middle
    u_peak = 0.45 if ramp == "ramp" else 0.5
    st = sh["peak"] - np.interp(u_peak, us, disp)
    st = clamp(st, sh["t0"] + 0.05, sh["t1"] - 0.05 - span)
    return st, us, disp

# ----------------------------------------------------------------------------
# 4. RENDER helpers
# ----------------------------------------------------------------------------
class ClipReader:
    """Sequential reader of a source span, scaled+cropped to output size, fps=30 timeline."""
    def __init__(self, scan, st, span, ow, oh):
        info = scan["info"]
        ct, cb = scan["crop_top"], scan["crop_bot"]
        ch = info["h"] * (1 - ct - cb)
        ch = int(ch) // 2 * 2
        cy = int(info["h"] * ct) // 2 * 2
        vf = (f"crop={info['w']}:{ch}:0:{cy},"
              f"scale={ow}:{oh}:force_original_aspect_ratio=increase:flags=bicubic,"
              f"crop={ow}:{oh}:(iw-{ow})*{STYLE['crop_focus'][0]}:(ih-{oh})*{STYLE['crop_focus'][1]},fps={FPS}")
        self.st = st
        self.ow, self.oh = ow, oh
        cmd = [ffmpeg_bin(), "-v", "fatal", "-ss", f"{max(0, st):.3f}", "-i", scan["path"], "-t", f"{span + 0.4:.3f}",
               "-an", "-sn", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=ow * oh * 3 * 4)
        self.frames = []   # (index, frame)
        self.idx = -1
        self.last = None
    def _read(self):
        fs = self.ow * self.oh * 3
        buf = self.p.stdout.read(fs)
        if len(buf) < fs: return None
        self.idx += 1
        return np.frombuffer(buf, np.uint8).reshape(self.oh, self.ow, 3).copy()
    def get(self, src_off):
        """frame at source offset (sec) from st, blended between neighbours."""
        f = src_off * FPS
        i0 = int(math.floor(f)); w = f - i0
        while len(self.frames) == 0 or self.frames[-1][0] < i0 + 1:
            fr = self._read()
            if fr is None: break
            self.frames.append((self.idx, fr))
            if len(self.frames) > 3: self.frames.pop(0)
        if not self.frames:
            return self.last if self.last is not None else np.zeros((self.oh, self.ow, 3), np.uint8)
        d = {k: v for k, v in self.frames}
        a = d.get(i0, self.frames[-1][1] if i0 > self.frames[-1][0] else self.frames[0][1])
        b = d.get(i0 + 1, a)
        if w < 0.15 or b is a: out = a
        elif w > 0.85: out = b
        else: out = cv2.addWeighted(a, 1 - w, b, w, 0)
        self.last = out
        return out
    def close(self):
        try:
            self.p.stdout.close(); self.p.kill(); self.p.wait()
        except Exception: pass

GRADES = {   # (lift, gamma, gain, contrast) per channel B,G,R + shadow/highlight tints + sat + vignette
    "teal-orange": dict(b=(0.03, 1.00, 1.04, 1.16, 0.05, -0.03), g=(0.03, 1.00, 1.04, 1.16, 0.025, -0.005),
                        r=(0.03, 0.98, 1.08, 1.16, -0.03, 0.05), sat=1.12, vig=0.50),
    "phonk-night": dict(b=(0.02, 0.92, 1.10, 1.15, 0.05, -0.02), g=(0.02, 0.95, 1.06, 1.15, 0.0, -0.02),
                        r=(0.02, 0.90, 1.12, 1.15, -0.02, 0.04), sat=1.18, vig=0.55),
    "warm-gold":   dict(b=(0.02, 1.00, 0.96, 1.12, 0.0, -0.06), g=(0.02, 0.95, 1.06, 1.12, 0.0, 0.01),
                        r=(0.02, 0.90, 1.12, 1.12, 0.02, 0.06), sat=1.10, vig=0.45),
    "cold-steel":  dict(b=(0.02, 0.90, 1.12, 1.15, 0.06, 0.02), g=(0.02, 0.95, 1.06, 1.15, 0.03, 0.0),
                        r=(0.02, 1.00, 1.00, 1.15, -0.02, -0.02), sat=0.85, vig=0.50),
    "bw-punch":    dict(b=(0.02, 0.92, 1.10, 1.30, 0, 0), g=(0.02, 0.92, 1.10, 1.30, 0, 0),
                        r=(0.02, 0.92, 1.10, 1.30, 0, 0), sat=0.0, vig=0.55),
    "vhs-retro":   dict(b=(-0.06, 1.00, 0.92, 0.95, 0.03, -0.04), g=(-0.05, 1.00, 0.96, 0.95, 0.02, 0.0),
                        r=(-0.04, 0.97, 1.02, 0.95, 0.0, 0.03), sat=0.90, vig=0.35),
    "clean":       dict(b=(0.0, 1.0, 1.0, 1.05, 0, 0), g=(0.0, 1.0, 1.0, 1.05, 0, 0),
                        r=(0.0, 1.0, 1.0, 1.05, 0, 0), sat=1.05, vig=0.25),
}

def make_grade(ow, oh):
    x = np.arange(256) / 255.0
    def curve(x, lift, gamma, gain, contrast):
        y = np.clip((x - lift) / (1 - lift), 0, 1) ** gamma * gain
        y = 0.5 + (y - 0.5) * contrast
        y = np.where(y < 0.5, 2 * y * y, 1 - 2 * (1 - y) ** 2) * 0.55 + y * 0.45  # S-curve
        return np.clip(y, 0, 1)
    gp = GRADES.get(STYLE["grade"], GRADES["teal-orange"])
    sh = (1 - x) ** 2
    hl = x ** 2
    ch = []
    for k in ("b", "g", "r"):
        lift, gam, gain, con, ts, th = gp[k]
        ch.append(curve(x, lift, gam, gain, con) + ts * sh + th * hl)
    lut = np.stack(ch, -1)
    lut = (np.clip(lut, 0, 1) * 255).astype(np.uint8).reshape(256, 1, 3)
    yy, xx = np.mgrid[0:oh, 0:ow].astype(np.float32)
    d = np.sqrt(((xx - ow / 2) / (ow / 2)) ** 2 + ((yy - oh / 2) / (oh / 2)) ** 2)
    vig = np.clip(1.0 - gp["vig"] * np.clip(d - 0.45, 0, 1) ** 1.6, 0, 1)
    vig3 = (np.dstack([vig] * 3) * 255).astype(np.uint8)
    return lut, vig3

def grade(fr, lut, vig3, sat=None):
    sat = GRADES.get(STYLE["grade"], GRADES["teal-orange"])["sat"] if sat is None else sat
    fr = cv2.LUT(fr, lut)
    if sat != 1.0:
        gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        gray3 = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        fr = cv2.addWeighted(fr, sat, gray3, 1 - sat, 0)
    return cv2.multiply(fr, vig3, scale=1 / 255.0)

class Sprite:
    """Pre-rendered glowing word: core (BGRA) + additive glow (BGR)."""
    def __init__(self, text, font_path, size, color, italic_serif=False, tracking=0, outline_only=False):
        font = load_font(font_path, size)
        pad = int(size * 0.6)
        # measure with tracking
        widths = [font.getbbox(ch)[2] - font.getbbox(ch)[0] if ch != " " else size * 0.3 for ch in text]
        asc, desc = font.getmetrics()
        tw = int(sum(font.getlength(ch) for ch in text) + tracking * (len(text) - 1)) + 2
        th = asc + desc
        Wt, Ht = tw + 2 * pad, th + 2 * pad
        mask = Image.new("L", (Wt, Ht), 0)
        d = ImageDraw.Draw(mask)
        x = pad
        for ch in text:
            if outline_only:
                d.text((x, pad), ch, font=font, fill=0, stroke_width=max(2, size // 40), stroke_fill=255)
            else:
                d.text((x, pad), ch, font=font, fill=255)
            x += font.getlength(ch) + tracking
        m = np.array(mask).astype(np.float32) / 255.0
        c = COLORS[color]
        if outline_only:
            core = np.zeros((Ht, Wt, 3), np.float32)
            core[:] = np.array(c["core2"], np.float32)
        else:
            grad = np.linspace(0, 1, Ht, dtype=np.float32)[:, None, None]
            core = np.array(c["core1"], np.float32) * (1 - grad) + np.array(c["core2"], np.float32) * grad
            core = np.broadcast_to(core, (Ht, Wt, 3)).copy()
        self.core = core * m[..., None]              # premultiplied
        self.alpha = m
        g1 = cv2.GaussianBlur(m, (0, 0), size * 0.06)
        g2 = cv2.GaussianBlur(m, (0, 0), size * 0.22)
        glow = np.clip(1.2 * g1 + 0.9 * g2, 0, 1)
        self.glow = glow[..., None] * np.array(c["glow"], np.float32)
        self.shadow = np.clip(cv2.GaussianBlur(m, (0, 0), size * 0.12) * 1.6, 0, 1)
        self.w, self.h = Wt, Ht
        self.size = size
        self.text_w = tw

def blit(dst, spr, cx, cy, scale=1.0, alpha=1.0, glow=1.0, rgb_split=0, shadow=0.0):
    if alpha <= 0.01 or scale <= 0.02: return
    sw, sh = max(2, int(spr.w * scale)), max(2, int(spr.h * scale))
    core = cv2.resize(spr.core, (sw, sh), interpolation=cv2.INTER_LINEAR)
    a = cv2.resize(spr.alpha, (sw, sh), interpolation=cv2.INTER_LINEAR)
    gl = cv2.resize(spr.glow, (sw, sh), interpolation=cv2.INTER_LINEAR)
    sd = cv2.resize(spr.shadow, (sw, sh), interpolation=cv2.INTER_LINEAR) if shadow > 0 else None
    x0, y0 = int(cx - sw / 2), int(cy - sh / 2)
    X0, Y0 = max(0, x0), max(0, y0)
    X1, Y1 = min(dst.shape[1], x0 + sw), min(dst.shape[0], y0 + sh)
    if X1 <= X0 or Y1 <= Y0: return
    sx0, sy0 = X0 - x0, Y0 - y0
    sl = (slice(sy0, sy0 + Y1 - Y0), slice(sx0, sx0 + X1 - X0))
    reg = dst[Y0:Y1, X0:X1].astype(np.float32)
    if sd is not None:
        reg *= (1 - shadow * alpha * sd[sl])[..., None]               # dark backing for legibility
    reg += gl[sl] * (glow * alpha)                                   # additive glow
    if rgb_split:
        c = core[sl]; aa = a[sl]
        sh_ = int(rgb_split)
        ghost = np.zeros_like(c)
        ghost[:, sh_:, 2] = c[:, :-sh_, 2] if sh_ < c.shape[1] else 0
        ghost[:, :-sh_, 0] = c[:, sh_:, 0] if sh_ < c.shape[1] else 0
        reg += ghost * 0.8 * alpha
    reg = reg * (1 - a[sl][..., None] * alpha) + core[sl] * alpha
    dst[Y0:Y1, X0:X1] = np.clip(reg, 0, 255).astype(np.uint8)

def make_echo_grid(word, color, ow, oh):
    """Full-frame tiled outline copies of the word (BGRA float)."""
    size = int(oh * 0.13)
    spr = Sprite(word, FONT_IMPACT, size, color, outline_only=True, tracking=int(size * 0.04))
    layer = np.zeros((oh, ow, 3), np.float32)
    rows = 6
    for r in range(rows):
        y = int((r + 0.5) * oh / rows)
        off = (r % 2) * spr.w * 0.5
        x = -spr.w + off
        while x < ow + spr.w:
            tmp = np.zeros((oh, ow, 3), np.uint8)
            blit(tmp, spr, x, y, 1.0, 1.0, glow=0.35)
            layer = np.maximum(layer, tmp.astype(np.float32))
            x += spr.w * 0.95
    return layer

def draw_hud(fr, t, beats, beat_strength, scale):
    ow, oh = fr.shape[1], fr.shape[0]
    s = scale
    m = int(46 * s); L = int(70 * s); th = max(1, int(2 * s))
    col = (235, 235, 235)
    # viewfinder corner brackets
    for (x, y, dx, dy) in [(m, m, 1, 1), (ow - m, m, -1, 1), (m, oh - m, 1, -1), (ow - m, oh - m, -1, -1)]:
        cv2.line(fr, (x, y), (x + dx * L, y), col, th, cv2.LINE_AA)
        cv2.line(fr, (x, y), (x, y + dy * L), col, th, cv2.LINE_AA)
    # centre crosshair (tiny)
    cx, cy = ow // 2, oh // 2; c = int(10 * s)
    cv2.line(fr, (cx - c, cy), (cx + c, cy), (200, 200, 200), 1, cv2.LINE_AA)
    cv2.line(fr, (cx, cy - c), (cx, cy + c), (200, 200, 200), 1, cv2.LINE_AA)
    # beat pulse
    bi = int(np.searchsorted(beats, t, side="right")) - 1
    since = t - beats[bi] if bi >= 0 else 9
    pulse = max(0.0, 1 - since / 0.25)
    return bi, pulse

class HudText:
    def __init__(self, scale):
        self.s = scale
        self.f_title = load_font(FONT_IMPACT, int(40 * scale))
        self.f_mono = load_font(FONT_MONO, int(30 * scale))
        self.f_small = load_font(FONT_MONO, int(18 * scale))
    def text(self, fr, xy, txt, font, color=(235, 235, 235), anchor="la"):
        # render text into small patch with PIL and composite (keeps it cheap)
        bb = font.getbbox(txt, anchor=anchor)
        w, h = bb[2] - bb[0] + 4, bb[3] - bb[1] + 4
        img = Image.new("L", (w, h), 0)
        ImageDraw.Draw(img).text((-bb[0] + 2, -bb[1] + 2), txt, font=font, fill=255, anchor=anchor)
        a = np.array(img).astype(np.float32)[..., None] / 255.0
        x, y = int(xy[0] + bb[0] - 2), int(xy[1] + bb[1] - 2)
        X0, Y0 = max(0, x), max(0, y); X1, Y1 = min(fr.shape[1], x + w), min(fr.shape[0], y + h)
        if X1 <= X0 or Y1 <= Y0: return
        a = a[Y0 - y:Y1 - y, X0 - x:X1 - x]
        reg = fr[Y0:Y1, X0:X1].astype(np.float32)
        fr[Y0:Y1, X0:X1] = (reg * (1 - a) + np.array(color, np.float32) * a).astype(np.uint8)

# ----------------------------------------------------------------------------
# main render
# ----------------------------------------------------------------------------
def render(slots, scans, beatmap, wav, out_path, ow, oh, quick=False):
    beats = np.array(beatmap["beats"]); bstr = np.array(beatmap["beat_strength"])
    s = min(ow, oh) / 1080.0
    TS = float(STYLE["text_size"]) * (0.78 if oh > ow else 1.0)   # portrait: smaller words
    lut, vig3 = make_grade(ow, oh)
    rng = np.random.default_rng(SEED)
    grain = [rng.normal(0, 7 * float(STYLE["grain"]) + 1e-3, (oh // 2, ow // 2)).astype(np.float32) for _ in range(6)]
    grain = [cv2.resize(g, (ow, oh)) for g in grain]
    grain = [(cv2.merge([np.clip(g, 0, 255).astype(np.uint8)] * 3), cv2.merge([np.clip(-g, 0, 255).astype(np.uint8)] * 3))
             for g in grain]
    hud = HudText(s)

    # sprites
    log("building typography sprites ...")
    big, small, grids = {}, {}, {}
    for c in CUES:
        key = (c["word"], c["color"])
        if key not in big:
            big[key] = Sprite(c["word"], FONT_IMPACT, int(300 * s * TS), c["color"], tracking=int(10 * s))
            if c["grid"]: grids[key] = make_echo_grid(c["word"], c["color"], ow, oh)
        if c["lead"] and c["lead"] not in small:
            small[c["lead"]] = Sprite(c["lead"], FONT_SERIF_IT, int(96 * s * TS), LEAD_COLOR,
                                      tracking=int(4 * s))
    title_spr = None

    # heavy hits -> shake + flash
    heavy = [(float(t), float(v)) for t, v in zip(beats, bstr) if v > 0.62]
    for c in CUES: heavy.append((c["t"], 1.0))
    for h in EXTRA_HITS: heavy.append((float(h), 1.0))
    heavy.sort()

    enc = [ffmpeg_bin(), "-v", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{ow}x{oh}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "veryfast" if quick else "slow", "-crf", str(CRF if not quick else 20),
           "-maxrate", MAXRATE, "-bufsize", "80M", "-profile:v", "high", "-pix_fmt", "yuv420p",
           "-x264-params", "keyint=30:min-keyint=1", "-c:a", "aac", "-b:a", "320k",
           "-movflags", "+faststart", "-shortest", out_path]
    encp = subprocess.Popen(enc, stdin=subprocess.PIPE)

    N = int(round(DURATION * FPS))
    si = 0; reader = None; cur = None
    t_start = time.time()
    black = np.zeros((oh, ow, 3), np.uint8)
    for n in range(N):
        t = n / FPS
        # advance slot
        while si < len(slots) and t >= slots[si]["t1"] - 1e-6: si += 1
        slot = slots[min(si, len(slots) - 1)]
        if slot is not cur:
            if reader: reader.close(); reader = None
            cur = slot
            if slot.get("shot") is not None and slot["kind"] != "black":
                L = slot["t1"] - slot["t0"]
                st, us, disp = source_window(slot, L)
                slot["_st"], slot["_us"], slot["_disp"] = st, us, disp
                reader = ClipReader(scans[slot["shot"]["vid"]], st, disp[-1], ow, oh)
        L = cur["t1"] - cur["t0"]; u = (t - cur["t0"]) / max(L, 1e-6); lt = t - cur["t0"]
        if reader:
            off = float(np.interp(u, cur["_us"], cur["_disp"]))
            fr = reader.get(off)
        else:
            fr = black.copy()

        # --- camera: zoom punch, push-in, shake
        hit = cur["hit"]
        z = 1.035
        if cur["kind"] == "hit":
            z += 0.16 * float(STYLE["zoom"]) * (1 - ease_out(lt / 0.22)) * (0.6 + 0.6 * hit)
            # zoom-out-of-shot into next cut (zoom transition) on last 3 frames
            rem = cur["t1"] - t
            if rem < 3.0 / FPS and hit > 0.5: z += 0.12 * (1 - rem / (3.0 / FPS))
        else:
            z += 0.07 * u + 0.08 * (1 - ease_out(lt / 0.4))
        # shake from nearest previous heavy hit
        dx = dy = rot = 0.0
        for (ht, hv) in heavy:
            if ht <= t < ht + 0.4:
                dec = (1 - (t - ht) / 0.4) ** 2
                amp = 22 * s * hv * dec * float(STYLE["shake"])
                ph = n * 1.7
                dx += amp * math.sin(ph * 2.3) ; dy += amp * math.cos(ph * 3.1) * 0.7
                rot += 0.7 * hv * dec * math.sin(ph * 1.9)
        M = cv2.getRotationMatrix2D((ow / 2, oh / 2), rot, z)
        M[0, 2] += dx; M[1, 2] += dy
        fr = cv2.warpAffine(fr, M, (ow, oh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

        # --- grade
        fr = grade(fr, lut, vig3)

        # chromatic aberration on cut start of heavy hits
        if cur["kind"] == "hit" and lt < 0.12 and hit > 0.6:
            k = int(10 * s * float(STYLE["chroma"]) * (1 - lt / 0.12)) + 1
            fr[:, k:, 2] = fr[:, :-k, 2]; fr[:, :-k, 0] = fr[:, k:, 0]

        # --- text (echo grid behind words)
        for c in CUES:
            key = (c["word"], c["color"])
            if c["grid"] and c["t"] <= t < c["end"]:
                bi = int(np.searchsorted(beats, t, side="right")) - 1
                since = t - beats[bi] if bi >= 0 else 1
                flick = max(0.0, 1 - since / 0.18)
                a = (0.06 + 0.42 * flick) * float(STYLE["grid"])
                fade = min(1.0, (c["end"] - t) / 0.25)
                g = grids[key]
                # drift grid horizontally per beat
                shift = int(((bi % 4) - 1.5) * 18 * s)
                gg = np.roll(g, shift, axis=1)
                fr = np.clip(fr.astype(np.float32) + gg * (a * fade), 0, 255).astype(np.uint8)
        for c in CUES:
            key = (c["word"], c["color"])
            cxm, cym = ow / 2, oh * float(STYLE["text_y"])
            # lead-in (small italic serif)
            if c["lead"] and c["lead_t"] <= t < c["end"]:
                spr = small[c["lead"]]
                lt2 = t - c["lead_t"]
                a = ease_out(lt2 / 0.45) * min(1.0, (c["end"] - t) / 0.25)
                yoff = 30 * s * (1 - ease_out(lt2 / 0.6))
                if t < c["t"]:
                    blit(fr, spr, cxm, cym + yoff, 1.0 + 0.06 * lt2, a, glow=0.8, shadow=0.5)
                else:  # docks above the big word, left aligned to it
                    b = big[key]; fit = min(1.0, (ow * 0.86) / b.w)
                    left = cxm - b.text_w * fit / 2
                    lx = left + spr.text_w * 0.85 / 2 + 10 * s
                    ly = cym + 20 * s - b.size * fit * 0.62 - 40 * s
                    blit(fr, spr, lx, ly, 0.85, a, glow=0.6, shadow=0.5)
            # big impact word
            if c["t"] <= t < c["end"]:
                spr = big[key]
                lt2 = t - c["t"]
                if lt2 < 0.12:     # slam: big -> overshoot
                    sc = 1.7 - 0.75 * ease_out(lt2 / 0.12)
                elif lt2 < 0.22:
                    sc = 0.95 + 0.05 * ease_out((lt2 - 0.12) / 0.1)
                else:
                    sc = 1.0 + 0.035 * (lt2 - 0.22)
                ex = c["end"] - t
                a = 1.0
                if ex < 0.16:
                    a = ex / 0.16; sc *= 1 + 0.25 * (1 - a)
                # glow pulses on beats
                bi = int(np.searchsorted(beats, t, side="right")) - 1
                since = t - beats[bi] if bi >= 0 else 1
                gl = 0.9 + 0.7 * max(0, 1 - since / 0.2)
                split = int(14 * s * max(0, 1 - lt2 / 0.18)) + (int(4 * s) if since < 0.06 else 0)
                fit = min(1.0, (ow * 0.86) / spr.w)
                blit(fr, spr, cxm, cym + 20 * s, sc * fit, a, glow=gl, rgb_split=split, shadow=0.65)

        # flash frames on lyric slams + section drops
        for c in CUES:
            if c["t"] <= t < c["t"] + 0.1:
                fa = 0.55 * float(STYLE["flash"]) * (1 - (t - c["t"]) / 0.1)
                fr = cv2.addWeighted(fr, 1 - fa, np.full_like(fr, _hex_bgr(STYLE["flash_color"])), fa, 0)
        for h in EXTRA_HITS:
            if h <= t < h + 0.08 and not any(abs(h - c["t"]) < 0.05 for c in CUES):
                fa = 0.45 * float(STYLE["flash"]) * (1 - (t - h) / 0.08)
                fr = cv2.addWeighted(fr, 1 - fa, np.full_like(fr, _hex_bgr(STYLE["hit_flash_color"])), fa, 0)

        # grain
        gp, gn = grain[n % len(grain)]
        fr = cv2.subtract(cv2.add(fr, gp), gn)

        if STYLE.get("letterbox"):
            bh = int(oh * 0.12) if ow > oh else 0
            if bh: fr[:bh] = 0; fr[oh - bh:] = 0
        # --- HUD
        bi, pulse = draw_hud(fr, t, beats, bstr, s) if HUD_ENABLED else (0, 0)
        if HUD_ENABLED:
            m = int(46 * s)
            hud.text(fr, (m + int(16 * s), m + int(14 * s)), HUD_TITLE, hud.f_title, HUD_ACCENT)
            hud.text(fr, (m + int(18 * s), m + int(64 * s)), HUD_SUB, hud.f_small, (200, 230, 240))
            fN = n % FPS; sec = int(t)
            tc = f"00:{sec // 60:02d}:{sec % 60:02d}:{fN:02d}"
            tw = hud.f_mono.getlength(tc)
            # REC dot blinking with beats
            rc = (40, 40, 255) if (bi % 2 == 0) else (40, 40, 140)
            cv2.circle(fr, (int(ow - m - 16 * s - tw - 26 * s), int(m + 32 * s)), int(8 * s), rc, -1, cv2.LINE_AA)
            hud.text(fr, (ow - m - int(16 * s) - tw, m + int(14 * s)), tc, hud.f_mono, (235, 235, 235))
            hud.text(fr, (ow - m - int(16 * s) - hud.f_small.getlength(f"{beatmap['bpm']:.0f} BPM  ·  1080p  ·  {FPS}FPS"),
                          m + int(56 * s)), f"{beatmap['bpm']:.0f} BPM  ·  1080p  ·  {FPS}FPS", hud.f_small, (170, 200, 210))
            # beat-progress bar
            bx0, bx1 = m + int(10 * s), ow - m - int(10 * s); by = oh - m - int(8 * s)
            cv2.line(fr, (bx0, by), (bx1, by), (90, 90, 90), max(1, int(2 * s)), cv2.LINE_AA)
            px = int(bx0 + (bx1 - bx0) * (t / DURATION))
            for k, bt in enumerate(beats):
                x = int(bx0 + (bx1 - bx0) * (bt / DURATION))
                hgt = int((6 + 10 * bstr[k]) * s)
                col = (40, 30, 235) if bt <= t else (110, 110, 110)
                cv2.line(fr, (x, by - hgt), (x, by), col, max(1, int(2 * s)), cv2.LINE_AA)
            cv2.line(fr, (bx0, by), (px, by), (40, 30, 235), max(2, int(4 * s)), cv2.LINE_AA)
            rad = int((7 + 9 * pulse) * s)
            cv2.circle(fr, (px, by), rad, (255, 150, 30), -1, cv2.LINE_AA)
            hud.text(fr, (bx0, by - int(40 * s)), f"BEAT {max(bi + 1, 0):03d}/{len(beats):03d}", hud.f_small, (200, 220, 230))
            hud.text(fr, (bx1 - hud.f_small.getlength(HUD_BR), by - int(40 * s)), HUD_BR, hud.f_small, (255, 200, 120))

        # outro fade to black
        if t > DURATION - 0.6:
            k = (DURATION - t) / 0.6
            fr = (fr.astype(np.float32) * k).astype(np.uint8)
        if t < 0.25:
            fr = (fr.astype(np.float32) * (t / 0.25)).astype(np.uint8)

        encp.stdin.write(fr.tobytes())
        if n % FPS == 0:
            el = time.time() - t_start
            log(f"render {t:5.1f}/{DURATION:.0f}s   ({(n+1)/max(el,1e-3):.1f} fps)")
    if reader: reader.close()
    encp.stdin.close(); encp.wait()
    log(f"done -> {out_path}")

# ----------------------------------------------------------------------------
def main():
    global FONT_IMPACT, FONT_SERIF_IT, FONT_MONO
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=os.getcwd(), help="project folder (project.json, raw/, song/)")
    ap.add_argument("--preview", action="store_true", help="fast half-size draft")
    ap.add_argument("--rescan", action="store_true")
    ap.add_argument("--dump-plan", action="store_true", help="write plan.json and stop")
    a = ap.parse_args()
    root = os.path.abspath(a.project)
    load_project(root)
    vids = []
    for d in ("raw", "raw video"):
        vids += glob.glob(os.path.join(root, d, "*.mp4")) + glob.glob(os.path.join(root, d, "*.mkv")) + glob.glob(os.path.join(root, d, "*.mov"))
    vids = sorted(vids)
    songs = sorted(glob.glob(os.path.join(root, "song", "*.mp3")) + glob.glob(os.path.join(root, "song", "*.wav")) + glob.glob(os.path.join(root, "song", "*.m4a")))
    if not vids or not songs:
        sys.exit("Need 'raw/*.mp4' and 'song/*.mp3' in the project folder.")
    FONT_IMPACT = font_spec(STYLE["impact_font"]) or font_spec("Anton-Regular.ttf") or f"{find_font(['impact.ttf','DejaVuSans-Bold.ttf'])}|"
    FONT_SERIF_IT = font_spec(STYLE["lead_font"]) or font_spec("PlayfairDisplay-Italic.ttf") or f"{find_font(['georgiai.ttf','DejaVuSerif-Italic.ttf'])}|"
    FONT_MONO = font_spec(STYLE["mono_font"]) or f"{find_font(['ShareTechMono-Regular.ttf','consola.ttf','DejaVuSansMono.ttf'])}|"
    log("fonts:", FONT_IMPACT, "|", FONT_SERIF_IT)
    log(f"output {W}x{H} @ {FPS}fps, song {AUDIO_START:.2f}s + {DURATION:.1f}s, grade {STYLE['grade']}")

    work = os.path.join(root, "_work"); os.makedirs(work, exist_ok=True)
    global HERE_PROJECT
    HERE_PROJECT = root
    beatmap = load_beats(songs[0])
    wav = os.path.join(work, "song_cut.wav"); cut_audio(songs[0], wav)

    slots = build_slots(beatmap["beats"], beatmap["beat_strength"])
    picks_p = os.path.join(root, "picks.json")
    if os.path.exists(picks_p):
        # hand-picked shots: no full scan needed
        log("using hand picks from picks.json (skipping full scan)")
        picks = json.load(open(picks_p))
        names = [os.path.basename(v).lower() for v in vids]
        scans = [quick_scan(v) for v in vids]
        for e in picks:
            i = e["slot"]
            if i >= len(slots): continue
            if not e.get("file"):
                slots[i]["shot"] = None; continue
            fn = e["file"].lower()
            if fn not in names:
                sys.exit(f"picks.json: file not found in 'raw': {e['file']}")
            slots[i]["shot"] = dict(vid=names.index(fn), t0=float(e["t0"]), t1=float(e["t1"]),
                                    peak=float(e["peak"]), tags=[e.get("note", "")])
            if e.get("ramp"): slots[i]["ramp"] = e["ramp"]
    else:
        cache_p = os.path.join(work, "scan_cache.json")
        cache = {} if a.rescan or not os.path.exists(cache_p) else json.load(open(cache_p))
        scans = []
        for v in vids:
            scans.append(scan_video(v, cache))
            json.dump(cache, open(cache_p, "w"))
        shots = []
        for vi, sc in enumerate(scans):
            sh = find_shots(sc, vi); log(f"{os.path.basename(sc['path'])}: {len(sh)} usable shots"); shots += sh
        score_shots(shots)
        slots = assign(slots, shots, None)
    plan = [dict(t0=round(s["t0"], 3), t1=round(s["t1"], 3), kind=s["kind"], ramp=s["ramp"], hit=round(s["hit"], 2),
                 stutter=s.get("stutter", False),
                 shot=None if s.get("shot") is None else dict(vid=s["shot"]["vid"], t0=round(s["shot"]["t0"], 2),
                                                               t1=round(s["shot"]["t1"], 2), peak=round(s["shot"]["peak"], 2),
                                                               tags=s["shot"].get("tags", [])))
            for s in slots]
    json.dump(plan, open(os.path.join(work, "plan.json"), "w"), indent=1)
    log(f"plan: {len(slots)} cuts  ->  _work/plan.json + _work/slots.txt")
    with open(os.path.join(work, "slots.txt"), "w", encoding="utf-8") as fh:
        fh.write("slot  t0-t1(edit s)  len  kind  ramp  hit   (calm=slow-mo shot, hit=beat cut; ramp needs ~1 s of source)\n")
        for i, p in enumerate(plan):
            fh.write(f"{i:3d}  {p['t0']:6.2f}-{p['t1']:6.2f}  {p['t1']-p['t0']:4.2f}  {p['kind']:5s} {p['ramp']:6s} {p['hit']:.2f}\n")
    for p in plan:
        sh = p["shot"]
        desc = "BLACK" if sh is None else f"{os.path.basename(vids[sh['vid']])[:28]:28s} @ {sh['peak']:8.2f}s  {','.join(sh['tags'])}"
        log(f"  {p['t0']:6.2f}-{p['t1']:6.2f}  {p['kind']:5s} {p['ramp']:6s}  {desc}")
    if a.dump_plan: return
    ow, oh = (W // 2 // 2 * 2, H // 2 // 2 * 2) if a.preview else (W, H)
    out = os.path.join(root, OUT_NAME if not a.preview else OUT_NAME.replace(".mp4", "_PREVIEW.mp4"))
    render(slots, scans, beatmap, wav, out, ow, oh, quick=a.preview)

if __name__ == "__main__":
    main()
