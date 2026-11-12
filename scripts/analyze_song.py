#!/usr/bin/env python3
r"""
analyze_song.py - find the best 30-40 s window of a song and build its beat map.

    python analyze_song.py "song\track.mp3"                       full report + best window + beats.json
    python analyze_song.py "song\track.mp3" --start 65 --dur 38   force a window (e.g. chorus you chose)
    python analyze_song.py "song\track.mp3" --vocals              also map vocal activity (needs spleeter)

Writes next to the project (the folder above song/):
    song_report.txt   short text report (energy map, drops, breaks, BPM, candidate windows)  <- give THIS to Claude
    beats.json        beat grid + per-beat strength + bass hits for the chosen window
    project.suggest.json   sections + cue times suggested from the music (copy into project.json)
Needs: pip install librosa numpy
"""
import argparse, json, os, sys
import numpy as np

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("song")
    ap.add_argument("--dur", type=float, default=38.0, help="edit length in seconds (default 38)")
    ap.add_argument("--start", type=float, default=None, help="force window start (seconds)")
    ap.add_argument("--vocals", action="store_true", help="vocal activity map via spleeter (optional)")
    ap.add_argument("--out", default=None, help="project folder (default: parent of song folder)")
    a = ap.parse_args()
    import librosa

    song = os.path.abspath(a.song)
    proj = a.out or os.path.dirname(os.path.dirname(song))
    y, sr = librosa.load(song, sr=22050, mono=True)
    dur = len(y) / sr
    hop = 512; fps = sr / hop
    oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    S = np.abs(librosa.stft(y, hop_length=hop)); f = librosa.fft_frequencies(sr=sr)
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    bass = S[f < 140].sum(0)
    n = min(len(rms), len(bass), len(oenv))
    rms, bass, oenv = rms[:n], bass[:n], oenv[:n]

    # ---- tempo: autocorrelation peaks (half/double-time aware)
    ac = librosa.autocorrelate(oenv, max_size=int(2 * fps))
    lags = np.arange(len(ac)) / fps
    peaks = [(ac[i], 60 / lags[i]) for i in range(1, len(ac) - 1)
             if ac[i] > ac[i - 1] and ac[i] > ac[i + 1] and 0.3 < lags[i] < 1.5]
    peaks.sort(reverse=True)
    bpm = peaks[0][1] if peaks else 120.0
    if bpm < 70: bpm *= 2
    if bpm > 180: bpm /= 2

    # ---- energy per second, drops (sudden rises) and breaks (dips)
    sec = int(dur)
    E = np.array([rms[int(t * fps):int((t + 1) * fps)].mean() for t in range(sec)])
    B = np.array([bass[int(t * fps):int((t + 1) * fps)].mean() for t in range(sec)])
    En = E / (E.max() + 1e-9); Bn = B / (B.max() + 1e-9)
    drops, breaks = [], []
    for t in range(2, sec - 2):
        if En[t] - En[t - 2:t].mean() > 0.35 and En[t:t + 2].mean() > 0.6: drops.append(t)
        if En[t] < 0.35 and En[t - 2:t].mean() > 0.6: breaks.append(t)
    drops = [d for i, d in enumerate(drops) if i == 0 or d - drops[i - 1] > 4]
    breaks = [d for i, d in enumerate(breaks) if i == 0 or d - breaks[i - 1] > 4]

    # ---- candidate windows: high energy + bass, bonus if a drop sits in the first 25 %
    W = int(a.dur)
    cands = []
    for s0 in range(0, max(1, sec - W)):
        seg = slice(s0, s0 + W)
        sc = 0.6 * En[seg].mean() + 0.4 * Bn[seg].mean()
        if any(s0 + 1 <= d <= s0 + W * 0.3 for d in drops): sc += 0.15
        if any(s0 + W * 0.3 <= b <= s0 + W * 0.85 for b in breaks): sc += 0.05   # mid break = dramatic
        if En[s0 + W - 1 if s0 + W - 1 < sec else sec - 1] < 0.25: sc += 0.03        # ends on a hard stop
        cands.append((sc, s0))
    cands.sort(reverse=True)
    picks = []
    for sc, s0 in cands:
        if all(abs(s0 - p) > 8 for _, p in picks): picks.append((sc, s0))
        if len(picks) == 3: break
    start = a.start if a.start is not None else float(picks[0][1])
    # snap the start just before a drop if one is inside the first 6 s
    if a.start is None:
        near = [d for d in drops if start <= d <= start + 6]
        if near: start = max(0.0, near[0] - 4.0)

    # ---- precise beat grid inside the window (hi-hat / onset phase)
    off = 2.0
    y2, _ = librosa.load(song, sr=22050, offset=max(0, start - off), duration=a.dur + 2 * off)
    h2 = 256
    o2 = librosa.onset.onset_strength(y=y2, sr=sr, hop_length=h2)
    tempo, bf = librosa.beat.beat_track(onset_envelope=o2, sr=sr, hop_length=h2, start_bpm=bpm, tightness=300)
    bt = librosa.frames_to_time(bf, sr=sr, hop_length=h2) - min(off, start)
    P = 60.0 / float(np.atleast_1d(tempo)[0])
    # refine phase on the high band (hats) when present
    S2 = np.abs(librosa.stft(y2, hop_length=h2)); f2 = librosa.fft_frequencies(sr=sr)
    hi = librosa.amplitude_to_db(S2[(f2 > 6000) & (f2 < 11000)], ref=np.max)
    henv = np.r_[0, np.maximum(0, np.diff(hi, axis=1)).mean(0)]
    ho = librosa.onset.onset_detect(onset_envelope=henv, sr=sr, hop_length=h2, units="time", delta=0.2, wait=6) - min(off, start)
    if len(ho) > 8 and len(bt) > 4:
        ph = np.median([(h - bt[0]) % P for h in ho if 0 <= h < a.dur])
        ph = ph if ph < P / 2 else ph - P
        if abs(ph) < 0.12: bt = bt + ph
    # regular grid over the whole window (quiet breaks have no detectable beats)
    inside = [t for t in bt if 0 <= t < a.dur]
    anchor = inside[len(inside) // 2] if inside else 0.0
    k0 = -int(anchor / P) - 1
    beats = [round(float(anchor + k * P), 3) for k in range(k0, k0 + int(a.dur / P) + 3) if 0 <= anchor + k * P < a.dur]
    rr = librosa.feature.rms(y=y2, hop_length=h2)[0]
    lo = S2[f2 < 140].sum(0)
    def at(arr, t):
        i = int((t + min(off, start)) * sr / h2); return float(arr[i:i + 15].mean()) if i < len(arr) else 0.0
    st = np.array([0.5 * at(rr, t) / rr.max() + 0.5 * at(lo, t) / lo.max() for t in beats])
    st = st / (st.max() + 1e-9)
    # bass slams (808 / kick drops): onsets in the sub band
    sub = librosa.amplitude_to_db(S2[(f2 > 30) & (f2 < 120)], ref=np.max)
    senv = np.r_[0, np.maximum(0, np.diff(sub, axis=1)).mean(0)]
    so = librosa.onset.onset_detect(onset_envelope=senv, sr=sr, hop_length=h2, units="time", delta=0.15, wait=8) - min(off, start)
    cand = [float(t) for t in so if 0.3 <= t < a.dur - 0.3]
    sv = np.array([float(senv[int((t + min(off, start)) * sr / h2)]) for t in cand]) if cand else np.array([])
    hits = []
    if len(cand):
        thr = max(np.percentile(sv, 40), 0.25 * sv.max())
        for t, v in sorted(zip(cand, sv), key=lambda x: -x[1]):
            if v >= thr and all(abs(t - h) > 1.5 for h in hits): hits.append(round(t, 3))
            if len(hits) == 10: break
        hits.sort()

    beatmap = dict(start=round(start, 3), duration=a.dur, bpm=round(60 / P, 2), beats=beats,
                   beat_strength=[round(float(v), 3) for v in st], bass_hits=hits)
    json.dump(beatmap, open(os.path.join(proj, "beats.json"), "w"))

    # ---- section + cue suggestion inside window
    wE = [(t - start, float(En[int(t)])) for t in range(int(start), min(sec, int(start + a.dur)))]
    secs, cur, t0 = [], None, 0.0
    for t, e in wE:
        mode = "drop" if e >= 0.6 else ("break" if e < 0.35 else "groove")
        if mode != cur:
            if cur is not None: secs.append([round(t0, 2), round(t, 2), cur])
            cur, t0 = mode, t
    secs.append([round(t0, 2), a.dur, cur])
    # snap boundaries to nearest beat, merge tiny ones, keep them contiguous
    def snap(x):
        pool = beats + hits
        return min(pool, key=lambda b: abs(b - x)) if pool else x
    merged = []
    for s0, s1, m in secs:
        if merged and (s1 - s0 < 1.5 or m == merged[-1][2]):
            continue
        merged.append([0.0 if not merged else round(snap(s0), 3), None, m])
    for i in range(len(merged)):
        merged[i][1] = merged[i + 1][0] if i + 1 < len(merged) else a.dur
    if merged[0][2] == "break": merged[0][2] = "intro"
    last = merged[-1]
    if last[2] != "outro" and last[1] - last[0] > 3.0:
        cut = round(a.dur - 1.0, 3); last[1] = cut; merged.append([cut, a.dur, "outro"])
    elif last[2] != "outro":
        last[2] = "outro"
    strong = sorted(range(len(beats)), key=lambda i: -st[i])
    cue_times = sorted(set([round(h, 3) for h in hits[:6]] + [beats[i] for i in strong[:6]]))
    cue_times = [c for i, c in enumerate(cue_times) if i == 0 or c - cue_times[i - 1] > 3.0][:6]
    json.dump(dict(song=dict(start=beatmap["start"], duration=a.dur), sections=merged, hits=hits,
                   cue_slots=[dict(t=c, end=round(min(a.dur, c + 2.0), 2)) for c in cue_times]),
              open(os.path.join(proj, "project.suggest.json"), "w"), indent=1)

    # ---- vocals (optional)
    vtxt = ""
    if a.vocals:
        try:
            import subprocess, tempfile
            tmp = tempfile.mkdtemp()
            subprocess.run([sys.executable, "-m", "spleeter", "separate", "-p", "spleeter:2stems", "-o", tmp, song],
                           check=True, capture_output=True)
            v, _ = librosa.load(os.path.join(tmp, os.path.splitext(os.path.basename(song))[0], "vocals.wav"), sr=16000)
            vr = librosa.feature.rms(y=v, frame_length=8000, hop_length=8000)[0]
            vd = librosa.amplitude_to_db(vr, ref=vr.max())
            vtxt = "\nVOCALS (0.5 s steps, # = singing loud)\n" + "\n".join(
                f"{i*0.5//60:.0f}:{i*0.5%60:04.1f} " + "#" * max(0, int((vd[i] + 30) / 2)) for i in range(len(vd)))
        except Exception as e:
            vtxt = f"\n(vocal map skipped: {e}. pip install spleeter in Python 3.11 to enable)"

    # ---- compact report
    def mmss(t): return f"{int(t // 60)}:{t % 60:04.1f}"
    lines = [f"SONG {os.path.basename(song)}  length {mmss(dur)}  tempo ~{60 / P:.1f} BPM (beat {P:.3f}s)",
             "ENERGY per 2 s (E=loud, B=bass):"]
    for t in range(0, sec, 2):
        lines.append(f"{mmss(t)} E{'#' * int(En[t] * 20):<20} B{'#' * int(Bn[t] * 10)}")
    lines.append("DROPS at: " + ", ".join(mmss(d) for d in drops))
    lines.append("BREAKS at: " + ", ".join(mmss(b) for b in breaks))
    lines.append("CANDIDATE WINDOWS (score, start-end):")
    for sc, s0 in picks:
        lines.append(f"  {sc:.2f}  {mmss(s0)} - {mmss(s0 + a.dur)}")
    lines.append(f"CHOSEN WINDOW {mmss(start)} - {mmss(start + a.dur)}  (edit t = song t - {start:.2f})")
    lines.append(f"BEATS {len(beats)}  first {beats[:4]}")
    lines.append(f"BASS HITS (edit time): {hits}")
    lines.append(f"SECTIONS: {merged}")
    lines.append(f"SUGGESTED CUE TIMES: {cue_times}")
    rep = "\n".join(lines) + vtxt
    open(os.path.join(proj, "song_report.txt"), "w", encoding="utf-8").write(rep)
    print(rep)

if __name__ == "__main__":
    main()
