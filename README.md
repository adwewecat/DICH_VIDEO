# 🎬 DICH_VIDEO: Hệ Thống Dịch Video, Trích Xuất Subtitle OCR & Lồng Tiếng AI (100% Clean Code)

[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Clean Code](https://img.shields.io/badge/Security-100%25%20Clean%20%26%20Ad--Free-brightgreen.svg)]()
[![GitHub Repo](https://img.shields.io/badge/GitHub-DICH__VIDEO-orange.svg)](https://github.com/adwewecat/DICH_VIDEO.git)

---

## 📖 1. Giới thiệu Dự Án

**DICH_VIDEO** là bộ công cụ chuyên nghiệp, tự động hóa toàn diện quy trình chuyển ngữ và lồng tiếng video:
1. **Trích xuất phụ đề (Hardsub OCR)**: Nhận diện và bóc tách phụ đề cứng trực tiếp từ video hình ảnh (Douyin, TikTok, YouTube, Bilibili) bằng công nghệ Computer Vision (OpenCV + OCR AI).
2. **Dịch thuật ngữ cảnh bằng AI (Gemini AI Translation)**: Sử dụng mô hình Google Gemini mới nhất với khả năng nghe audio gốc (Audio Multimodal) kết hợp phân tích văn bản để dịch chuẩn xác từng câu, giữ trọn vẹn ngữ cảm nhân vật.
3. **Lồng tiếng AI (AI Dubbing)**: Hỗ trợ cả **Local TTS v3 48kHz chất lượng phòng thu (chạy offline trên máy tính, 25 giọng đọc Việt - Anh)** và **Edge-TTS / VBee**, tự động kéo giãn/co ngắn âm thanh để khớp từng mili-giây với khẩu hình và độ dài video gốc.
4. **Hậu kỳ tự động hóa**: Xóa/làm mờ phụ đề gốc trên video, gắn phụ đề mới, hòa âm tiếng nói với nhạc nền video gốc qua FFmpeg.

> 🛡️ **Cam kết 100% Code Sạch (Clean Code)**:
> Bản dự án đã được dịch ngược, phân tích toàn diện và bóc tách sạch sẽ từ bản đóng gói `v-translate-07-11`:
> - ❌ **ĐÃ XÓA BỎ**: Toàn bộ mã độc quyền khóa bản quyền (DRM, license check).
> - ❌ **ĐÃ XÓA BỎ**: Mã gián điệp quét thông tin phần cứng (HWID spy).
> - ❌ **ĐÃ XÓA BỎ**: Hệ thống bắt nạp tiền ví VietQR / Proxy server Apps Script.
> - ✅ **HOÀN TOÀN TỰ DO**: Bạn được sử dụng API Key cá nhân miễn phí của Google Gemini, chạy trực tiếp trên máy mà không sợ bị khóa hay thu phí.

---

## 🛠️ 2. Tích hợp Công Cụ Dịch Ngược REA (`morluto/rea`)

Dự án tích hợp trực tiếp **REA (Reverse Engineer Anything)** từ [morluto/rea](https://github.com/morluto/rea) dưới dạng Git Submodule tại thư mục `tools/rea/`.
REA cung cấp giao diện dòng lệnh (CLI) và MCP Server mạnh mẽ cho phép các AI Agent (Antigravity, Claude, Codex) và lập trình viên dịch ngược mọi file nhị phân, phân tích ứng dụng Electron, trích xuất cấu trúc dữ liệu và phát hiện hành vi ngầm của phần mềm.

Để kiểm tra trạng thái REA:
```bash
npx rea-agents doctor
```

---

## 🚀 3. Hướng Dẫn Cài Đặt Môi Trường

### Bước 1: Yêu cầu hệ thống
- Hệ điều hành: Windows 10 / 11 (64-bit).
- Python: Phiên bản **3.10 trở lên** (Khuyên dùng Python 3.10 hoặc 3.12).
- FFmpeg: Đã được cài đặt và thêm vào biến môi trường PATH (hoặc đặt `ffmpeg.exe` vào thư mục dự án).

### Bước 2: Cài đặt thư viện Python
Mở Terminal / PowerShell tại thư mục dự án và chạy lệnh:
```bash
pip install -r requirements.txt
```

---

## 🖥️ 4. Hướng Dẫn Chi Tiết Từng Chức Năng (Từng Tab)

### 📌 Tab 1: Trích Xuất Phụ Đề Video (Video Subtitle Extraction)
- **Tải video trực tiếp**: Hỗ trợ dán link video Douyin, TikTok, YouTube, Bilibili để tải video gốc độ phân giải cao nhất không dính watermark (tự động qua `yt-dlp`).
- **Chọn vùng phụ đề (Subtitle Region Selection)**: Hiển thị trình xem trước video, dùng chuột vẽ khung chọn chính xác vị trí phụ đề cứng cần nhận diện.
- **Nhận diện chữ (OCR Pipeline)**:
  - Tự động nhận diện khung hình có chứa phụ đề.
  - Sử dụng mô hình nhận diện ký tự quang học chuyên dụng cho tiếng Trung / tiếng Anh / tiếng Hàn.
  - Loại bỏ các khung hình trùng lặp để tạo ra file `.srt` với timestamp chính xác.
- **Làm mờ phụ đề cũ (Inpaint/Blur)**: Tự động phủ lớp mờ thông minh tại vị trí phụ đề cũ để chuẩn bị chèn phụ đề tiếng Việt.

### 📌 Tab 2: Dịch Thuật Ngữ Cảnh AI (Context-Aware Translation)
- **Quản lý danh sách Gemini API Key (Key Pool Rotation)**:
  - Cho phép người dùng nhập 1 hoặc nhiều Google Gemini API Key (lấy miễn phí tại [Google AI Studio](https://aistudio.google.com/)).
  - Hệ thống tự động xoay vòng key khi gặp giới hạn tốc độ (Rate Limit / Quota Exceeded), đảm bảo quá trình dịch không bị gián đoạn.
- **Cơ chế Dịch 2 Lượt (Two-Pass Translation with Audio)**:
  - *Lượt 1 (Pass 1 - Audio Context)*: Tách âm thanh của video và gửi lên Gemini File API để AI "nghe" toàn bộ ngữ cảnh, phân biệt cảm xúc, giọng điệu, đại từ nhân xưng của các nhân vật.
  - *Lượt 2 (Pass 2 - Subtitle Translation)*: Dịch từng đoạn phụ đề SRT kết hợp ngữ cảnh đã phân tích ở Lượt 1, xuất ra phụ đề tiếng Việt tự nhiên, chuẩn văn phong đời thực.
- **Rà soát & Sửa lỗi (Quality Check)**:
  - Tự động kiểm tra phát hiện câu còn sót tiếng Trung hoặc ký tự lạ.
  - Cung cấp giao diện bảng xem trước song ngữ, cho phép người dùng click sửa trực tiếp từng dòng.

### 📌 Tab 3: Lồng Tiếng AI (AI Dubbing & Audio Sync)
- **Lựa chọn bộ máy giọng đọc (TTS Engines)**:
  - **Local TTS v3 (Khuyên dùng)**: Chạy hoàn toàn offline bằng ONNX Runtime / OpenVINO, cung cấp 25 giọng đọc tiếng Việt và tiếng Anh chuẩn studio 48kHz (Hải Đăng, Mai Anh, Thùy Dung, Minh Đức, Quỳnh Anh, Thái Sơn,...).
  - **Edge-TTS**: Giọng đọc Microsoft Edge tốc độ cực nhanh, miễn phí, đa dạng cảm xúc (Hoài My, Nam Minh,...).
- **Từ điển viết tắt & phiên âm riêng (`tts_abbreviations.json`)**:
  - Tự động thay thế các từ viết tắt, tên riêng nước ngoài thành cách phát âm tiếng Việt trước khi đọc.
- **Tự động căn chỉnh thời lượng (Audio Time-Stretching)**:
  - Tự động tính toán độ dài câu đọc so với khoảng thời gian của phụ đề gốc.
  - Nếu câu đọc dài hơn video, hệ thống tự động tăng tốc độ đọc mượt mà (không méo tiếng) để khớp chính xác với khẩu hình.
- **Ghép âm thanh & Video (FFmpeg Media Merger)**:
  - Tự động giảm âm lượng nhạc nền video gốc (Audio Ducking) khi có giọng đọc thuyết minh và hòa trộn thành file video hoàn chỉnh MP4.

### 📌 Tab 4: Chuyển Đổi & Hậu Xử Lý Văn Bản (Text Conversion)
- Chuyển đổi qua lại giữa định dạng SRT, ASS, TXT.
- Gộp các câu ngắn ngắt quãng thành đoạn văn hoàn chỉnh.
- Làm sạch timestamp và xuất kịch bản dạng kịch bản phân vai.

---

## 🔒 5. Quy Tắc Dự Án & Quản Lý Mã Nguồn

Mọi đóng góp và phát triển dự án phải tuân thủ nghiêm ngặt các quy tắc trong [GEMINI.md](file:///d:/LAPTRINH/Dich_video/GEMINI.md):
- Cập nhật nhật ký công việc vào `GEMINI.md` trước và sau mỗi tác vụ.
- Đẩy code ngay lên GitHub `https://github.com/adwewecat/DICH_VIDEO.git` khi có thay đổi.
- Duy trì chuẩn mực **Clean Code 100%**, loại bỏ mã rác và chú thích code đầy đủ.
