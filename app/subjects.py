"""Tự viết mô tả CHỦ THỂ ảnh nền (tiếng Anh) cho từng cảnh từ lời đọc tiếng Việt."""
from __future__ import annotations

import json
import subprocess
import sys

from .director import DEFAULT_MODEL
from .scriptkit import short_title

SYSTEM = """Bạn viết mô tả ảnh nền cho video dọc 9:16. Với mỗi cảnh (lời đọc tiếng Việt), hãy viết MỘT mô tả CHỦ THỂ bằng TIẾNG ANH:
- 10–25 từ, hình ảnh cụ thể hoặc ẩn dụ gắn với nội dung cảnh, dễ vẽ bằng AI.
- KHÔNG chứa chữ, logo, tên người nổi tiếng, hay thương hiệu.
- Phong cách ảnh đã được cố định ({style_name}: {style_hint}), vì vậy CHỈ mô tả chủ thể/hình ảnh chính, không lặp lại phong cách, ánh sáng, màu sắc.
Chỉ trả về một mảng JSON các chuỗi, đúng số lượng và thứ tự cảnh, không giải thích."""


def _claude(voices: list[str], style: dict, api_key: str, model: str, client=None) -> list[str]:
    if client is None:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key.strip())
    system = SYSTEM.format(style_name=style["style_name"], style_hint=style["full_prompt_string"][:200])
    user = "\n".join(f"{i}. {v.strip()}" for i, v in enumerate(voices, 1))
    msgs = [{"role": "user", "content": user}]
    for _ in range(2):
        text = client.messages.create(model=model or DEFAULT_MODEL, max_tokens=2000, system=system,
                                      messages=msgs).content[0].text
        try:
            data = json.loads(text[text.index("["): text.rindex("]") + 1])
            if isinstance(data, list) and len(data) == len(voices) and all(isinstance(x, str) and x.strip() for x in data):
                return [x.strip() for x in data]
            err = f"cần đúng {len(voices)} chuỗi"
        except Exception as e:  # noqa: BLE001
            err = str(e)
        msgs += [{"role": "assistant", "content": text},
                 {"role": "user", "content": f"Lỗi: {err}. Chỉ trả về mảng JSON {len(voices)} chuỗi."}]
    raise ValueError("Claude chưa trả về danh sách hợp lệ")


def _translate(voices: list[str], log) -> list[str]:
    try:
        try:
            from deep_translator import GoogleTranslator
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "deep-translator"], check=True)
            from deep_translator import GoogleTranslator
        tr = GoogleTranslator(source="vi", target="en")
        out = []
        for v in voices:
            en = tr.translate(" ".join(v.split()[:30]))
            out.append(f"a striking visual metaphor for: {en}".strip())
        return out
    except Exception as e:  # noqa: BLE001
        log(f"⚠️ Không dịch tự động được ({e}); dùng nguyên văn tiếng Việt (ảnh có thể kém sát nội dung).")
        return [short_title(v, 14) for v in voices]


def generate(voices: list[str], style: dict, api_key: str = "", model: str = "", log=print, client=None) -> list[str]:
    if client is not None or (api_key or "").strip():
        try:
            log("🪄 Đang nhờ Claude viết mô tả chủ thể ảnh cho từng cảnh...")
            return _claude(voices, style, api_key, model, client)
        except Exception as e:  # noqa: BLE001
            log(f"⚠️ Không dùng được Claude ({e}); chuyển sang dịch tự động.")
    else:
        log("ℹ️ Chưa có Anthropic API key: dùng dịch tự động để mô tả ảnh (nhập key ở tab ① để ảnh sát nội dung hơn).")
    return _translate(voices, log)
