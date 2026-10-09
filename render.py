"""Dựng hình từng cảnh: HTML động → ảnh từng khung (Chromium) → MP4 (FFmpeg)."""
from __future__ import annotations

import base64
import math
import subprocess
import tempfile
from pathlib import Path

from .project import QUALITY, UserError, digest, remove_stale
from .templates import TEMPLATE_VERSION, build_html

PREVIEW_SECONDS = 4.0
_VISUAL_KEYS = ("template", "kicker", "headline", "sub", "items")
_STYLE_KEYS = ("brand", "tagline", "url", "accent_from", "accent_to")


def anim_seconds_for(st: dict, duration: float | None) -> float:
    """Độ dài đoạn hoạt hình. Cố định (không phụ thuộc giọng) trừ khi bật chuyển động liên tục."""
    if st["continuous"] and duration:
        return round(duration, 1)
    return round(float(st["anim_seconds"]), 1)


def anim_path(pdir: Path, i: int, scene: dict, st: dict, anim_sec: float) -> Path:
    key = digest(
        TEMPLATE_VERSION,
        {k: scene[k] for k in _VISUAL_KEYS},
        {k: st[k] for k in _STYLE_KEYS},
        st["quality"],
        anim_sec,
    )
    return pdir / "clips" / f"anim-{i:02d}-{key}.mp4"


class Renderer:
    """Mở Chromium một lần, dùng cho nhiều cảnh."""

    def __init__(self, quality: str):
        self.q = QUALITY[quality]

    def __enter__(self):
        from playwright.sync_api import sync_playwright

        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = self._browser.new_context(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
        self.page = ctx.new_page()
        self._cdp = ctx.new_cdp_session(self.page)  # chụp qua CDP nhanh gần gấp đôi
        return self

    def __exit__(self, *exc):
        for obj in (getattr(self, "_browser", None), getattr(self, "_pw", None)):
            try:
                obj.close() if hasattr(obj, "close") else obj.stop()
            except Exception:  # noqa: BLE001
                pass

    def render(self, html: str, out: Path, anim_sec: float) -> int:
        fps = self.q["fps"]
        n = max(2, math.ceil(anim_sec * fps))
        page = self.page
        page.set_content(html, wait_until="load")
        try:
            page.evaluate("document.fonts.ready.then(() => true)")
        except Exception:  # noqa: BLE001
            pass
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "mjpeg",
            "-i", "pipe:0", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
            "-r", str(fps), str(out),
        ]
        with tempfile.TemporaryFile() as errf:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=errf)
            for k in range(n):
                page.evaluate(
                    "t => { for (const a of document.getAnimations()) { a.pause(); a.currentTime = t; } }",
                    k * 1000.0 / fps,
                )
                shot = self._cdp.send(
                    "Page.captureScreenshot", {"format": "jpeg", "quality": 92, "optimizeForSpeed": True,
                     "clip": {"x": 0, "y": 0, "width": 1080, "height": 1920, "scale": self.q["scale"]}}
                )
                proc.stdin.write(base64.b64decode(shot["data"]))
            proc.stdin.close()
            rc = proc.wait()
            if rc != 0:
                errf.seek(0)
                raise RuntimeError("FFmpeg lỗi khi mã hoá cảnh: " + errf.read().decode(errors="ignore")[-300:])
        return n


def render_scenes(pdir: Path, scenes: list[dict], st: dict, durations: dict[int, float] | None = None,
                  force: bool = False, only: list[int] | None = None, log=print) -> dict[int, Path]:
    durations = durations or {}
    if st["continuous"] and not durations:
        log("ℹ️ Chế độ chuyển động liên tục cần có giọng đọc trước; tạm dùng thời lượng hoạt hình mặc định.")
    out: dict[int, Path] = {}
    made = 0
    with Renderer(st["quality"]) as r:
        for i, sc in enumerate(scenes):
            if only is not None and i not in only:
                continue
            anim = anim_seconds_for(st, durations.get(i))
            path = anim_path(pdir, i, sc, st, anim)
            out[i] = path
            if path.exists() and not force:
                log(f"• Cảnh {i + 1}: dùng lại hình đã có")
                continue
            log(f"🖼️ Cảnh {i + 1}/{len(scenes)} ({sc['template']}): đang dựng {anim:.1f}s hoạt hình...")
            n = r.render(build_html(sc, st), path, anim)
            remove_stale(path.parent, f"anim-{i:02d}-*.mp4", path)
            made += 1
            log(f"   ✓ {n} khung hình")
    log(f"✅ Xong hình: dựng mới {made}, dùng lại {len(out) - made}.")
    return out
