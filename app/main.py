"""Giao diện web (Gradio): kịch bản → giọng đọc → hình ảnh → xuất video."""
from __future__ import annotations

import os
from pathlib import Path

import gradio as gr

from . import aiimage, assemble, director, media, render, scriptkit as K, tts
from . import project as P
from .jobs import run_job
from .project import UserError
from .templates import THEMES

SETTING_KEYS = [
    "brand", "tagline", "url", "theme", "custom_colors", "accent_from", "accent_to", "quality",
    "continuous", "speed", "seed", "normalize", "ref_text", "style_json",
]


# ── Tiện ích dùng chung ───────────────────────────────────────────────────────
def merge_settings(vals) -> dict:
    st = {**P.DEFAULT_SETTINGS, **dict(zip(SETTING_KEYS, vals))}
    st["speed"] = float(st["speed"] or 1.0)
    st["seed"] = int(st["seed"] or 0)
    st["brand"] = (st["brand"] or "").strip() or P.DEFAULT_SETTINGS["brand"]
    st["ref_text"] = st["ref_text"] or ""
    st["custom_colors"] = bool(st["custom_colors"])
    st["style_json"] = st["style_json"] or ""
    return st


def prepare(name: str, rows, vals, save: bool = True):
    st = merge_settings(vals)
    scenes = K.complete_all(K.rows_to_scenes(rows))
    K.require_valid(scenes)
    pdir = P.project_dir(name)
    if save:
        P.save_project(name, scenes, st)
    return pdir, scenes, st


def _ref_status(name: str) -> str:
    has = tts.ref_path(P.project_dir(name)) is not None
    return "✅ Dự án đã có giọng mẫu." if has else "⚠️ Chưa có giọng mẫu — nên tải lên để giọng đọc nhất quán."


# ── Dự án ─────────────────────────────────────────────────────────────────────
def _gallery(name: str):
    return [(str(p), p.name) for p in media.list_media(P.project_dir(name))]


def open_project(name):
    data = P.load_project(name)
    st = data["settings"]
    rows = K.scenes_to_rows(data["scenes"])
    return [rows] + [st[k] for k in SETTING_KEYS] + [_ref_status(name), f"📂 Đã mở dự án **{P.slugify(name)}**.", _gallery(name)]


def save_project(name, rows, *vals):
    try:
        prepare(name, rows, vals)
    except UserError as e:
        return f"⚠️ {e}"
    return f"💾 Đã lưu dự án **{P.slugify(name)}** tại `{P.project_dir(name)}`."


# ── ① Kịch bản ────────────────────────────────────────────────────────────────
def split_handler(text, add_outro, brand):
    if not (text or "").strip():
        raise gr.Error("Hãy dán kịch bản vào ô bên trên.")
    scenes = K.complete_all(K.split_script(text, brand=brand, add_outro=bool(add_outro)))
    return K.scenes_to_rows(scenes)


def fill_handler(rows):
    return K.scenes_to_rows(K.complete_all(K.rows_to_scenes(rows)))


def director_handler(rows, api_key, model, topic, use_ai, brand, style_json):
    scenes = K.rows_to_scenes(rows)
    try:
        style = media.parse_style(style_json)
        if use_ai and style is None:
            raise UserError("Hãy dán JSON phong cách ảnh ở tab ③ trước (hoặc bỏ tick “Để AI mô tả ảnh nền”).")
        theme, designed = director.direct(
            scenes, api_key, model or director.DEFAULT_MODEL, topic or "", (brand or "").strip(), bool(use_ai), style)
    except UserError as e:
        raise gr.Error(str(e))
    except Exception as e:  # noqa: BLE001
        raise gr.Error(f"Đạo diễn AI gặp lỗi: {e}")
    label = render_theme_label(theme)
    return K.scenes_to_rows(designed), theme, f"✨ Đạo diễn AI đã thiết kế {len(designed)} cảnh · chủ đề **{label}**."


def render_theme_label(theme: str) -> str:
    from .templates import THEMES
    return THEMES.get(theme, {}).get("label", theme)


def style_check(text):
    try:
        style = media.parse_style(text)
    except UserError as e:
        return f"⚠️ {e}"
    if style is None:
        return "ℹ️ Chưa có JSON phong cách."
    filled = [k for k in media.STYLE_FIELDS if style[k]]
    return f"✅ Hợp lệ — **{style['style_name']}** · các trường có dữ liệu: {', '.join(filled)}"


def style_load(file):
    if not file:
        return gr.update()
    path = getattr(file, "name", file)
    return Path(path).read_text(encoding="utf-8")


def media_handler(name, files):
    if not files:
        raise gr.Error("Hãy chọn ảnh trước.")
    saved = media.save_uploads(P.project_dir(name), files)
    return _gallery(name), None, f"🖼️ Đã thêm {len(saved)} ảnh: " + ", ".join(f"`{n}`" for n in saved)


def _job_ai(pdir, scenes, st, force, log):
    aiimage.generate_all(pdir, scenes, st, force=force, log=log)


def ai_handler(name, force, rows, *vals):
    try:
        pdir, scenes, st = prepare(name, rows, vals)
    except UserError as e:
        yield f"⚠️ {e}"
        return
    for log, _res, _err in run_job(_job_ai, pdir, scenes, st, bool(force)):
        yield log


# ── ② Giọng đọc ───────────────────────────────────────────────────────────────
def _job_tts(pdir, scenes, st, force, ref_upload, log):
    if ref_upload and tts.set_reference(pdir, ref_upload):
        log("✓ Đã lưu giọng mẫu cho dự án.")
    tts.synthesize_all(pdir, scenes, st, force=force, log=log)


def tts_handler(name, force, ref_audio, rows, *vals):
    try:
        pdir, scenes, st = prepare(name, rows, vals)
    except UserError as e:
        yield f"⚠️ {e}"
        return
    for log, _res, _err in run_job(_job_tts, pdir, scenes, st, bool(force), ref_audio):
        yield log


def listen_handler(name, idx, rows, *vals):
    try:
        pdir, scenes, st = prepare(name, rows, vals, save=False)
    except UserError as e:
        raise gr.Error(str(e))
    i = int(idx) - 1
    if not 0 <= i < len(scenes):
        raise gr.Error(f"Chỉ có {len(scenes)} cảnh.")
    v = tts.voice_info(pdir, i, scenes[i], st)
    if not v:
        raise gr.Error("Cảnh này chưa có giọng — hãy bấm “Tạo giọng” trước.")
    return str(v[0])


# ── ③ Hình ảnh ────────────────────────────────────────────────────────────────
def _job_render(pdir, scenes, st, force, log):
    durations = {}
    for i, sc in enumerate(scenes):
        v = tts.voice_info(pdir, i, sc, st)
        if v:
            durations[i] = v[1]
    render.render_scenes(pdir, scenes, st, durations or None, force=force, log=log)


def render_handler(name, force, rows, *vals):
    try:
        pdir, scenes, st = prepare(name, rows, vals)
    except UserError as e:
        yield f"⚠️ {e}"
        return
    for log, _res, _err in run_job(_job_render, pdir, scenes, st, bool(force)):
        yield log


def _job_preview(pdir, scenes, st, i, log):
    return assemble.preview_scene(pdir, i, scenes, st, log=log)


def preview_handler(name, idx, rows, *vals):
    try:
        pdir, scenes, st = prepare(name, rows, vals, save=False)
    except UserError as e:
        yield f"⚠️ {e}", None
        return
    i = int(idx) - 1
    if not 0 <= i < len(scenes):
        yield f"⚠️ Chỉ có {len(scenes)} cảnh.", None
        return
    for log, res, _err in run_job(_job_preview, pdir, scenes, st, i):
        yield log, (str(res) if res else None)


# ── ④ Xuất video ──────────────────────────────────────────────────────────────
def _job_assemble(pdir, scenes, st, log):
    return assemble.assemble(pdir, scenes, st, log=log)


def _job_all(pdir, scenes, st, ref_upload, log):
    if ref_upload and tts.set_reference(pdir, ref_upload):
        log("✓ Đã lưu giọng mẫu cho dự án.")
    return assemble.run_all(pdir, scenes, st, log=log)


def _stream_result(job, *args):
    for log, res, _err in run_job(job, *args):
        if res:
            yield log, str(res["video"]), [str(p) for p in res.values()]
        else:
            yield log, gr.update(), gr.update()


def assemble_handler(name, rows, *vals):
    try:
        pdir, scenes, st = prepare(name, rows, vals)
    except UserError as e:
        yield f"⚠️ {e}", None, None
        return
    yield from _stream_result(_job_assemble, pdir, scenes, st)


def all_handler(name, ref_audio, rows, *vals):
    try:
        pdir, scenes, st = prepare(name, rows, vals)
    except UserError as e:
        yield f"⚠️ {e}", None, None
        return
    yield from _stream_result(_job_all, pdir, scenes, st, ref_audio)


# ── Giao diện ─────────────────────────────────────────────────────────────────
def build_ui() -> gr.Blocks:
    existing = P.list_projects()
    default_project = existing[0] if existing else "du-an-1"
    d = P.DEFAULT_SETTINGS

    with gr.Blocks(title="AI Auto Video", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            "# 🎬 AI Auto Video\n"
            "Biến kịch bản của bạn thành video dọc 9:16 — làm từng bước, bước nào xong được lưu lại để dùng tiếp."
        )
        with gr.Row():
            project = gr.Dropdown(choices=existing, value=default_project, allow_custom_value=True,
                                  label="Dự án (gõ tên mới để tạo)", scale=4)
            open_btn = gr.Button("📂 Mở", scale=1)
            save_btn = gr.Button("💾 Lưu", scale=1)
        status = gr.Markdown()

        with gr.Tabs():
            # ① Kịch bản ----------------------------------------------------
            with gr.Tab("① Kịch bản"):
                script_text = gr.Textbox(lines=8, label="Dán kịch bản của bạn",
                                         placeholder="Mỗi đoạn cách nhau một dòng trống. Đoạn dài sẽ tự tách thành nhiều cảnh.")
                with gr.Row():
                    add_outro = gr.Checkbox(value=True, label="Tự thêm cảnh kết (outro)")
                    split_btn = gr.Button("✂️ Tách thành các cảnh", variant="primary")
                    fill_btn = gr.Button("🪄 Điền tự động các ô trống")
                with gr.Accordion("✨ Đạo diễn AI — tự chọn chủ đề, mẫu cảnh, chữ và mô tả ảnh nền (tuỳ chọn)", open=False):
                    api_key = gr.Textbox(type="password", label="Anthropic API key (không lưu vào dự án)")
                    with gr.Row():
                        dir_model = gr.Textbox(value=director.DEFAULT_MODEL, label="Mô hình")
                        dir_topic = gr.Textbox(label="Chủ đề / phong cách mong muốn (không bắt buộc)",
                                               placeholder="vd: công nghệ, tông tối, nhịp nhanh")
                    dir_ai_img = gr.Checkbox(value=True, label="Để AI mô tả ảnh nền cho các cảnh")
                    director_btn = gr.Button("✨ Thiết kế video từ kịch bản")
                table = gr.Dataframe(
                    value=[[""] * len(K.HEADERS)], headers=K.HEADERS, datatype=["str"] * len(K.HEADERS),
                    type="array", interactive=True, wrap=True, label="Danh sách cảnh (sửa trực tiếp, có thể thêm dòng)",
                )
                gr.Markdown(
                    "**Cách điền:** chỉ cần cột **Lời đọc** là đủ — các ô khác để trống sẽ được tự điền.\n\n"
                    "- **Mẫu:** `hero` · `stat` · `statement` · `list` · `quote` · `compare` · `image` · `outro`\n"
                    "- **Tiêu đề:** dùng `|` để xuống dòng, đặt `*từ khoá*` trong dấu sao để tô sáng · **Danh sách:** các mục cách nhau "
                    "bằng `|`, có thể bắt đầu bằng emoji (ví dụ `🔋 Pin trâu`)\n"
                    "- **Ảnh nền:** tên file trong thư viện ảnh (tab ③), một đường link ảnh, hoặc **mô tả ảnh** (AI sẽ tạo)\n"
                    "- Lời đọc: số được tự đọc thành chữ (bật/tắt ở tab ②)."
                )

            # ② Giọng đọc ---------------------------------------------------
            with gr.Tab("② Giọng đọc"):
                ref_audio = gr.Audio(sources=["upload", "microphone"], type="filepath",
                                     label="Giọng mẫu (3–15 giây, rõ tiếng) — dùng để nhân bản giọng")
                ref_status = gr.Markdown()
                ref_text = gr.Textbox(value=d["ref_text"], label="Lời của giọng mẫu (không bắt buộc, để trống sẽ tự nhận dạng)")
                with gr.Row():
                    speed = gr.Slider(0.7, 1.4, value=d["speed"], step=0.05, label="Tốc độ đọc")
                    seed = gr.Number(value=d["seed"], precision=0, label="Seed")
                    normalize = gr.Checkbox(value=d["normalize"], label="Tự đọc số thành chữ")
                with gr.Row():
                    force_tts = gr.Checkbox(value=False, label="Tạo lại từ đầu (bỏ qua giọng đã có)")
                    tts_btn = gr.Button("🎙️ Tạo giọng cho các cảnh", variant="primary")
                tts_log = gr.Textbox(lines=8, label="Nhật ký", interactive=False, autoscroll=True)
                with gr.Row():
                    listen_idx = gr.Number(value=1, precision=0, label="Nghe thử cảnh số")
                    listen_btn = gr.Button("▶ Nghe")
                listen_audio = gr.Audio(label="Giọng của cảnh", interactive=False)

            # ③ Hình ảnh ----------------------------------------------------
            with gr.Tab("③ Hình ảnh"):
                theme = gr.Dropdown(choices=[(v["label"], k) for k, v in THEMES.items()], value=d["theme"],
                                    label="🎨 Chủ đề hình ảnh (quyết định nền, màu, kiểu chữ, hiệu ứng)")
                with gr.Row():
                    brand = gr.Textbox(value=d["brand"], label="Tên kênh / thương hiệu")
                    tagline = gr.Textbox(value=d["tagline"], label="Khẩu hiệu (cảnh kết)")
                    url = gr.Textbox(value=d["url"], label="Liên kết (cảnh kết)")
                with gr.Row():
                    custom_colors = gr.Checkbox(value=d["custom_colors"], label="Dùng màu của riêng tôi (thay màu của chủ đề)")
                    accent_from = gr.ColorPicker(value=d["accent_from"], label="Màu nhấn 1")
                    accent_to = gr.ColorPicker(value=d["accent_to"], label="Màu nhấn 2")
                with gr.Row():
                    quality = gr.Radio(
                        choices=[("Nhanh — 720×1280 · 24fps", "fast"), ("Chuẩn — 1080×1920 · 30fps", "standard")],
                        value=d["quality"], label="Chất lượng",
                    )
                continuous = gr.Checkbox(value=d["continuous"],
                                         label="Nền chuyển động suốt cảnh (đẹp hơn nhưng dựng lâu hơn)")
                with gr.Accordion("🎨 Phong cách ảnh AI của bạn (JSON) — bắt buộc khi dùng ảnh AI", open=True):
                    style_json = gr.Textbox(
                        lines=10, label="Dán JSON phong cách (mỗi video một JSON)",
                        placeholder='{"style_name": "...", "full_prompt_string": "...", "composition": "...", '
                                    '"lighting": "...", "color_palette": "...", "negative_prompt": "..."}',
                    )
                    with gr.Row():
                        style_file = gr.File(file_types=[".json"], label="…hoặc tải file .json")
                        style_btn = gr.Button("✔ Kiểm tra JSON")
                    style_info = gr.Markdown()
                    gr.Markdown(
                        "Các trường: `style_name`, **`full_prompt_string`** (bắt buộc), `composition`, `lighting`, "
                        "`color_palette`, `negative_prompt`. Mô tả ở cột *Ảnh nền* của từng cảnh chỉ cần nói về **chủ thể**, "
                        "phần còn lại lấy từ JSON này."
                    )
                with gr.Accordion("🖼️ Thư viện ảnh nền & ảnh AI", open=False):
                    media_files = gr.File(file_count="multiple", file_types=["image"], label="Tải ảnh lên (dùng tên file trong cột Ảnh nền)")
                    media_btn = gr.Button("📥 Thêm vào thư viện")
                    gallery = gr.Gallery(label="Thư viện ảnh của dự án", columns=6, height=220, interactive=False)
                    with gr.Row():
                        force_ai = gr.Checkbox(value=False, label="Tạo lại ảnh AI từ đầu")
                        ai_btn = gr.Button("🎨 Tạo ảnh AI cho các cảnh có mô tả")
                with gr.Row():
                    force_render = gr.Checkbox(value=False, label="Dựng lại từ đầu (bỏ qua hình đã có)")
                    render_btn = gr.Button("🖼️ Dựng hình các cảnh", variant="primary")
                render_log = gr.Textbox(lines=8, label="Nhật ký", interactive=False, autoscroll=True)
                with gr.Row():
                    preview_idx = gr.Number(value=1, precision=0, label="Xem thử cảnh số")
                    preview_btn = gr.Button("👁️ Xem thử")
                preview_video = gr.Video(label="Xem thử", interactive=False)

            # ④ Xuất video --------------------------------------------------
            with gr.Tab("④ Xuất video"):
                gr.Markdown("Cần có giọng (②) và hình (③) trước. Hoặc bấm **Chạy tất cả** để làm liền mạch.")
                with gr.Row():
                    assemble_btn = gr.Button("🎬 Ghép video cuối", variant="primary")
                    all_btn = gr.Button("🚀 Chạy tất cả (giọng → hình → ghép)")
                out_log = gr.Textbox(lines=8, label="Nhật ký", interactive=False, autoscroll=True)
                out_video = gr.Video(label="Video", interactive=False)
                out_files = gr.File(label="Tệp kết quả (video.mp4 · voice.mp3 · script.txt · captions.srt)",
                                    file_count="multiple", interactive=False)

        settings = [brand, tagline, url, theme, custom_colors, accent_from, accent_to, quality, continuous, speed, seed, normalize, ref_text, style_json]
        base = [project, table] + settings  # đầu vào chung

        demo.load(open_project, [project], [table] + settings + [ref_status, status, gallery])
        open_btn.click(open_project, [project], [table] + settings + [ref_status, status, gallery])
        save_btn.click(save_project, base, status)

        director_btn.click(director_handler, [table, api_key, dir_model, dir_topic, dir_ai_img, brand, style_json], [table, theme, status])
        style_btn.click(style_check, [style_json], style_info)
        style_file.change(style_load, [style_file], [style_json])
        media_btn.click(media_handler, [project, media_files], [gallery, media_files, status])
        ai_btn.click(ai_handler, [project, force_ai, table] + settings, render_log)
        split_btn.click(split_handler, [script_text, add_outro, brand], table)
        fill_btn.click(fill_handler, [table], table)

        tts_btn.click(tts_handler, [project, force_tts, ref_audio, table] + settings, tts_log)
        listen_btn.click(listen_handler, [project, listen_idx, table] + settings, listen_audio)

        render_btn.click(render_handler, [project, force_render, table] + settings, render_log)
        preview_btn.click(preview_handler, [project, preview_idx, table] + settings, [render_log, preview_video])

        assemble_btn.click(assemble_handler, base, [out_log, out_video, out_files])
        all_btn.click(all_handler, [project, ref_audio, table] + settings, [out_log, out_video, out_files])
    return demo


def main() -> None:
    P.ROOT.mkdir(parents=True, exist_ok=True)
    allowed = [str(P.ROOT)] + [p for p in ("/content",) if Path(p).exists()]
    demo = build_ui()
    demo.queue(default_concurrency_limit=1)
    demo.launch(
        share=os.environ.get("AVG_SHARE", "1") == "1",
        server_name="0.0.0.0",
        allowed_paths=allowed,
        show_error=True,
    )


if __name__ == "__main__":
    main()
