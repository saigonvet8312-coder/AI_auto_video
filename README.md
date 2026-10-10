# AI Auto Video

Biến kịch bản của bạn thành **video dọc 9:16** có giọng đọc tiếng Việt, chạy hoàn toàn trên Google Colab.

**Kịch bản → giọng đọc (OmniVoice) → hình ảnh động (HTML + Chromium) → ghép video (FFmpeg)**

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/saigonvet8312-coder/AI_auto_video/blob/main/AI_auto_video.ipynb)

## Cách dùng

1. Mở notebook bằng nút Colab ở trên, chọn **Runtime → Change runtime type → T4 GPU**.
2. Chạy lần lượt 3 phần (mỗi phần là một cell riêng):
   - **Phần 1 — Cài đặt:** chỉ chạy một lần mỗi phiên Colab.
   - **Phần 2 — Mã nguồn & thư mục dự án:** gắn Google Drive, lấy mã mới nhất.
   - **Phần 3 — Mở giao diện:** hiện đường link, mở ở tab mới.
3. Trong giao diện, đi qua 4 tab. Mỗi tab có nút chạy riêng:

| Tab | Việc làm |
|---|---|
| ① Kịch bản | Dán kịch bản, tách cảnh, chỉnh sửa trong bảng |
| ② Giọng đọc | Tải giọng mẫu, tạo giọng từng cảnh, nghe thử |
| ③ Hình ảnh | Chọn chủ đề, thương hiệu, thư viện ảnh/ảnh AI, dựng hình, xem thử từng cảnh |
| ④ Xuất video | Ghép video cuối, hoặc “Chạy tất cả” |

Kết quả nằm trong `<thư mục dự án>/<tên dự án>/`: `video.mp4`, `voice.mp3`, `script.txt`, `captions.srt`.

## Làm video bớt nhàm chán

- **6 chủ đề hình ảnh** (tab ③): Cực quang, Neon công nghệ, Điện ảnh tối, Giấy sáng, Hoàng hôn, Tối giản đậm. Mỗi chủ đề có nền, màu, kiểu chữ và hiệu ứng riêng; đổi chủ đề không cần tạo lại giọng.
- **8 mẫu cảnh:** hero, stat (số tự chạy lên), statement (từ khoá được tô sáng), list, quote, compare, image, outro. Mẫu và hiệu ứng vào cảnh được tự luân phiên để các cảnh không giống nhau.
- **Ảnh nền cho từng cảnh** (cột “Ảnh nền”): tên file đã tải lên thư viện, đường link ảnh, hoặc **một mô tả để AI tạo ảnh** (tab ③ → “Tạo ảnh AI”). Cảnh có ảnh nền có chuyển động máy quay.
- **Đạo diễn AI** (tab ①, tuỳ chọn, cần Anthropic API key): Claude đọc kịch bản rồi chọn chủ đề, mẫu cảnh, chữ ngắn gọn và mô tả ảnh nền cho từng cảnh.

## Chạy từng phần, không mất công

Mọi bước đều **lưu kết quả và dùng lại**. Sửa một cảnh thì chỉ cảnh đó được tạo giọng/dựng hình lại. Dự án lưu trên Google Drive nên Colab ngắt kết nối vẫn mở lại làm tiếp được.

## Bảng kịch bản

Chỉ cần điền cột **Lời đọc**, các ô trống còn lại được tự điền (bấm “Điền tự động” để xem).

| Cột | Ý nghĩa |
|---|---|
| Mẫu | `hero` · `stat` · `statement` · `list` · `quote` · `compare` · `image` · `outro` |
| Nhãn | Chữ nhỏ phía trên tiêu đề |
| Tiêu đề | Chữ lớn trên màn hình (`|` xuống dòng, `*từ khoá*` để tô sáng) |
| Phụ đề | Dòng mô tả bên dưới |
| Danh sách | Các mục của mẫu `list`, cách nhau bằng `|` |
| Ảnh nền | Tên file trong thư viện, link ảnh, hoặc mô tả để AI tạo ảnh |
| Lời đọc | Nội dung được đọc. Số, %, đơn vị (MP, GB, mAh…) tự đọc thành chữ |

## Cấu trúc mã

```
AI_auto_video.ipynb   notebook Colab (3 phần)
app/
  main.py        giao diện Gradio
  scriptkit.py   tách cảnh, điền tự động, kiểm tra
  vnnum.py       đọc số/ký hiệu thành chữ tiếng Việt
  tts.py         tạo giọng bằng OmniVoice, có cache
  templates.py   6 chủ đề + 8 mẫu cảnh (HTML/CSS)
  media.py       ảnh nền: tải lên, link, ảnh AI
  aiimage.py     tạo ảnh nền bằng AI
  director.py    đạo diễn AI (Claude)
  render.py      dựng hình bằng Chromium + FFmpeg
  assemble.py    ghép video, trộn âm thanh, xuất phụ đề
  jobs.py        chạy nền, phát nhật ký trực tiếp
  project.py     dự án, cài đặt, cache
```

## Xử lý sự cố

| Triệu chứng | Cách xử lý |
|---|---|
| Phần 1 báo cần khởi động lại | Restart session rồi chạy lại từ Phần 1 |
| Giọng mỗi cảnh một khác | Tải **giọng mẫu** ở tab ② |
| Dựng hình lâu | Chọn chất lượng “Nhanh”, tắt “Nền chuyển động suốt cảnh” |
| Chữ tiếng Việt lỗi dấu | Chạy lại Phần 1 (cài font) |
| Muốn làm lại một bước | Tick “Tạo lại / Dựng lại từ đầu” rồi chạy |

## Giấy phép các thành phần

Giọng đọc: [OmniVoice](https://github.com/k2-fsa/OmniVoice) (Apache-2.0) · Ảnh AI: segmind/SSD-1B (Apache-2.0, đổi được bằng biến `AVG_AI_MODEL`) · Trình duyệt tự động: Playwright (Apache-2.0) · Giao diện: Gradio (Apache-2.0) · FFmpeg.
