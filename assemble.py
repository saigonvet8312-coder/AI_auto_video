"""Ghép video cuối: khớp hình theo giọng, nối cảnh, trộn âm thanh, xuất phụ đề."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import numpy as np

from . import render, tts
from .project import QUALITY, UserError, digest, remove_stale
from .scriptkit import sentences


def _ffmpeg(*args: str) -> None:
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("FFmpeg lỗi: " + r.stderr.strip()[-400:])


def _fit(anim: Path, frames: int, fps: int, out: Path) -> None:
    """Cắt/kéo dài clip hoạt hình đúng `frames` khung (giữ khung cuối nếu thiếu)."""
    _ffmpeg(
        "-i", str(anim), "-vf", "tpad=stop_mode=clone:stop_duration=120", "-frames:v", str(frames),
        "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(out),
    )


def _ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def make_srt(scenes: list[dict], starts: list[float], speech: list[float]) -> str:
    cues, n = [], 1
    for sc, t0, dur in zip(scenes, starts, speech):
        parts = sentences(sc["voice"]) or [sc["voice"]]
        total = sum(len(p) for p in parts) or 1
        t = t0
        for p in parts:
            d = dur * len(p) / total
            cues.append(f"{n}\n{_ts(t)} --> {_ts(t + d)}\n{p}\n")
            t += d
            n += 1
    return "\n".join(cues)


def _collect(pdir: Path, scenes: list[dict], st: dict):
    voices, anims, missing = {}, {}, []
    for i, sc in enumerate(scenes):
        v = tts.voice_info(pdir, i, sc, st)
        if v is None:
            missing.append(f"giọng cảnh {i + 1}")
            continue
        voices[i] = v
        a = render.anim_path(pdir, i, sc, st, render.anim_seconds_for(st, v[1]))
        if not a.exists():
            missing.append(f"hình cảnh {i + 1}")
        anims[i] = a
    if missing:
        raise UserError("Chưa đủ nguyên liệu: " + ", ".join(missing) + ". Hãy chạy bước tương ứng trước.")
    return voices, anims


def assemble(pdir: Path, scenes: list[dict], st: dict, log=print) -> dict[str, Path]:
    fps = QUALITY[st["quality"]]["fps"]
    voices, anims = _collect(pdir, scenes, st)
    n = len(scenes)

    # Mốc thời gian (giây) và số khung hình tích luỹ để không lệch dần
    durs = [voices[i][1] for i in range(n)]
    hold = float(st["outro_hold"])
    starts, t = [], 0.0
    for d in durs:
        starts.append(t)
        t += d
    total = t + hold
    bounds = [round(s * fps) for s in starts] + [round(total * fps)]

    log("🎞️ Khớp hình theo giọng từng cảnh...")
    fits = []
    for i in range(n):
        frames = max(1, bounds[i + 1] - bounds[i])
        out = pdir / "clips" / f"fit-{i:02d}-{digest(anims[i].name, frames, fps)}.mp4"
        if not out.exists():
            _fit(anims[i], frames, fps, out)
            remove_stale(out.parent, f"fit-{i:02d}-*.mp4", out)
        fits.append(out)

    log("🔗 Nối các cảnh...")
    lst = pdir / "clips" / "concat.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in fits), encoding="utf-8")
    silent = pdir / "video-silent.mp4"
    _ffmpeg("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(silent))

    log("🔊 Ghép giọng đọc...")
    pcm = np.concatenate([tts.read_wav(voices[i][0]) for i in range(n)] + [tts.silence(hold)])
    wav = pdir / "voice.wav"
    tts.write_wav(wav, pcm)
    mp3 = pdir / "voice.mp3"
    _ffmpeg("-i", str(wav), "-codec:a", "libmp3lame", "-q:a", "2", str(mp3))
    wav.unlink(missing_ok=True)

    video = pdir / "video.mp4"
    _ffmpeg("-i", str(silent), "-i", str(mp3), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart", str(video))

    gap = float(st["gap"])
    (pdir / "script.txt").write_text("\n\n".join(s["voice"].strip() for s in scenes), encoding="utf-8")
    (pdir / "captions.srt").write_text(
        make_srt(scenes, starts, [max(d - gap, 0.1) for d in durs]), encoding="utf-8"
    )
    log(f"✅ Hoàn tất: {total:.1f}s · {video.stat().st_size / 1e6:.1f} MB")
    return {"video": video, "voice": mp3, "script": pdir / "script.txt", "srt": pdir / "captions.srt"}


def preview_scene(pdir: Path, i: int, scenes: list[dict], st: dict, log=print) -> Path:
    """Xem thử một cảnh (kèm giọng nếu đã có)."""
    fps = QUALITY[st["quality"]]["fps"]
    sc = scenes[i]
    v = tts.voice_info(pdir, i, sc, st)
    dur = v[1] if v else render.PREVIEW_SECONDS + 1.0
    anim_sec = render.anim_seconds_for(st, v[1] if v else None)
    render.render_scenes(pdir, scenes, st, {i: v[1]} if v else None, only=[i], log=log)
    anim = render.anim_path(pdir, i, sc, st, anim_sec)
    out = pdir / "preview.mp4"
    tmp = pdir / "preview-silent.mp4"
    _fit(anim, max(1, round(dur * fps)), fps, tmp)
    if v:
        _ffmpeg("-i", str(tmp), "-i", str(v[0]), "-c:v", "copy", "-c:a", "aac", "-shortest", str(out))
    else:
        tmp.replace(out)
    tmp.unlink(missing_ok=True)
    return out


def run_all(pdir: Path, scenes: list[dict], st: dict, log=print) -> dict[str, Path]:
    voices = tts.synthesize_all(pdir, scenes, st, log=log)
    render.render_scenes(pdir, scenes, st, {i: d for i, (_, d) in voices.items()}, log=log)
    return assemble(pdir, scenes, st, log=log)
