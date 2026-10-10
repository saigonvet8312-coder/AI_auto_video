"""Ảnh nền cho cảnh: ảnh tải lên, đường link, hoặc ảnh do AI tạo theo mô tả."""
from __future__ import annotations

import base64
import io
import os
import re
import shutil
from pathlib import Path

from .project import UserError, digest
from .templates import THEMES

IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")
AI_MODEL = os.environ.get("AVG_AI_MODEL", "segmind/SSD-1B")
AI_SIZE = (576, 1024)


def media_dir(pdir: Path) -> Path:
    d = pdir / "media"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_media(pdir: Path) -> list[Path]:
    return sorted(p for p in media_dir(pdir).iterdir() if p.suffix.lower() in IMG_EXT and not p.name.startswith("ai-"))


def save_uploads(pdir: Path, files) -> list[str]:
    saved = []
    for f in files or []:
        src = Path(getattr(f, "name", f))
        dst = media_dir(pdir) / re.sub(r"[^\w.\-]+", "_", src.name)
        if src.resolve() != dst.resolve():
            shutil.copy(src, dst)
        saved.append(dst.name)
    return saved


def ai_prompt_full(prompt: str, st: dict) -> str:
    style = THEMES.get(st.get("theme"), THEMES["aurora"])["style"]
    return f"{prompt.strip()}, {style}, vertical composition, no text, no watermark, no logo"


def ai_path(pdir: Path, prompt: str, st: dict) -> Path:
    # Không phụ thuộc chủ đề: đổi chủ đề không làm mất ảnh đã tạo (muốn ảnh theo phong cách mới thì bấm “Tạo lại”).
    key = digest(prompt.strip(), AI_MODEL, AI_SIZE, st.get("seed"))
    return media_dir(pdir) / f"ai-{key}.png"


def classify(value: str, pdir: Path):
    """Trả về (loại, nội dung): none | url | file | missing | ai."""
    v = (value or "").strip()
    if not v:
        return "none", None
    if re.match(r"https?://", v, re.I):
        return "url", v
    for p in media_dir(pdir).iterdir():
        if p.name.lower() == v.lower() and p.suffix.lower() in IMG_EXT:
            return "file", p
    if re.fullmatch(r"\S+\.(jpe?g|png|webp|gif)", v, re.I):
        return "missing", v
    return "ai", v


def _url_path(pdir: Path, url: str) -> Path:
    return media_dir(pdir) / f"url-{digest(url)}.img"


def fetch_url(pdir: Path, url: str) -> Path:
    dst = _url_path(pdir, url)
    if dst.exists():
        return dst
    import requests

    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
    except Exception as e:  # noqa: BLE001
        raise UserError(f"Không tải được ảnh từ link: {url} ({e})")
    if "image" not in r.headers.get("content-type", "image"):
        raise UserError(f"Link không phải ảnh: {url}")
    dst.write_bytes(r.content)
    return dst


def resolve(pdir: Path, scene: dict, st: dict, download: bool = True) -> Path | None:
    kind, payload = classify(scene.get("bg", ""), pdir)
    if kind == "none":
        return None
    if kind == "file":
        return payload
    if kind == "url":
        return fetch_url(pdir, payload) if download else (_url_path(pdir, payload) if _url_path(pdir, payload).exists() else None)
    if kind == "ai":
        p = ai_path(pdir, payload, st)
        return p if p.exists() else None
    raise UserError(f"Không thấy ảnh “{payload}” trong thư viện ảnh của dự án.")


def has_bg(pdir: Path, scene: dict) -> bool:
    return classify(scene.get("bg", ""), pdir)[0] != "none"


def bg_key(pdir: Path, scene: dict, st: dict) -> str:
    """Dấu vân tay của ảnh nền, dùng để biết khi nào phải dựng lại cảnh."""
    kind, payload = classify(scene.get("bg", ""), pdir)
    if kind == "none":
        return ""
    p = None
    if kind == "file":
        p = payload
    elif kind == "url":
        p = _url_path(pdir, payload)
    elif kind == "ai":
        p = ai_path(pdir, payload, st)
    size = p.stat().st_size if p is not None and p.exists() else 0
    return f"{kind}:{scene['bg']}:{size}"


def data_uri(path: Path, max_w: int = 1200, max_h: int = 2100) -> str:
    try:
        from PIL import Image

        im = Image.open(path).convert("RGB")
        im.thumbnail((max_w, max_h))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=88)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()
