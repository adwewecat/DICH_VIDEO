# 📘 HƯỚNG DẪN SỬ DỤNG CHI TIẾT HỆ THỐNG DICH_VIDEO (TỪNG CHỨC NĂNG, TỪNG DÒNG)

> **Dự án**: DICH_VIDEO - Hệ thống dịch video, trích xuất phụ đề và lồng tiếng AI  
> **Phiên bản**: 2.0 Clean Edition (100% Mã nguồn sạch, không DRM, không quảng cáo, hoàn toàn miễn phí)

---

## 📑 MỤC LỤC
1. [Khởi Động Ứng Dụng](#1-khởi-động-ứng-dụng)
2. [Cấu Hình Google Gemini API (Miễn Phí)](#2-cấu-hình-google-gemini-api-miễn-phí)
3. [Tab 1: Trích Xuất Video & Tải Video Sạch](#3-tab-1-trích-xuất-video--tải-video-sạch)
4. [Tab 2: Dịch Thuật Ngữ Cảnh AI (Two-Pass Translation)](#4-tab-2-dịch-thuật-ngữ-cảnh-ai-two-pass-translation)
5. [Tab 3: Lồng Tiếng AI & Đồng Bộ Âm Thanh (AI Dubbing)](#5-tab-3-lồng-tiếng-ai--đồng-bộ-âm-thanh-ai-dubbing)
6. [Tab 4: Chuyển Đổi Định Dạng & Tối Ưu Phụ Đề](#6-tab-4-chuyển-đổi-định-dạng--tối-ưu-phụ-đề)
7. [Khắc Phục Sự Cố Thường Gặp (Troubleshooting)](#7-khắc-phục-sự-cố-thường-gặp)

---

## 1. KHỞI ĐỘNG ỨNG DỤNG

### Cách 1: Chạy 1-Click bằng file `run.bat` (Khuyên dùng nhất)
1. Trong thư mục dự án `D:\LAPTRINH\Dich_video`, **chỉ cần nhấp đúp chuột (Double click) vào file `run.bat`**.
2. Chương trình sẽ tự động:
   - Kiểm tra Python trên máy của bạn.
   - Kiểm tra và tự động cài đặt thư viện còn thiếu từ `requirements.txt`.
   - Khởi động giao diện ứng dụng đồ họa ngay lập tức.

### Cách 2: Chạy từ dòng lệnh (Terminal / PowerShell / CMD)
1. Mở PowerShell hoặc Command Prompt tại thư mục dự án `D:\LAPTRINH\Dich_video`.
2. Chạy lệnh:
   ```bash
   python main.py
   ```
3. Giao diện chính của **DICH_VIDEO** sẽ xuất hiện với tông màu tối hiện đại (Dark Mode).

---

## 2. CẤU HÌNH GOOGLE GEMINI API (MIỄN PHÍ)

### Hướng dẫn từng bước:
1. Nhìn vào góc dưới cùng bên trái của thanh Sidebar, bấm nút **`🔑 Cài Đặt Gemini API`**.
2. Một cửa sổ cài đặt hiện ra:
   - **Ô nhập danh sách API Keys**:
     - Truy cập trang [Google AI Studio](https://aistudio.google.com/) bằng tài khoản Google của bạn.
     - Bấm **Create API Key** và copy key.
     - Dán key vào ô nhập liệu. **Bạn có thể dán nhiều API Key (mỗi dòng 1 key)**.
     - *Tính năng tự động*: Khi một key bị giới hạn tốc độ (Rate Limit 429), ứng dụng sẽ tự động chuyển sang key kế tiếp mà không làm gián đoạn bản dịch.
   - **Mục Mô hình AI (AI Model)**:
     - `gemini-2.5-flash`: Mô hình mới nhất, dịch nhanh và thông minh nhất.
     - `gemini-2.0-flash`: Tốc độ phản hồi cực nhanh, độ trễ thấp.
     - `gemini-1.5-pro`: Hiểu sâu ngữ cảnh phức tạp đối với phim tài liệu hoặc truyện nhiều nhân vật.
   - **Nút "Kiểm tra kết nối"**:
     - Bấm nút này để kiểm tra xem key có hoạt động tốt hay không. Nếu thành công sẽ có thông báo xanh.
   - Bấm **`Lưu Cấu Hình`** để hoàn tất.

---

## 3. TAB 1: TRÍCH XUẤT VIDEO & TẢI VIDEO SẠCH

Tab này phục vụ chuẩn bị tư liệu đầu vào (video gốc và audio gốc).

### 1. Dán Link Tải Video:
- **Ô nhập liệu**: Dán đường link video từ Douyin (TikTok Trung Quốc), TikTok quốc tế, YouTube, Bilibili, hoặc Facebook.
- **Nút `⬇️ Tải Video Sạch`**:
  - Tự động lọc sạch watermark/logo (đặc biệt đối với video Douyin).
  - Tải về video có độ nét cao nhất vào thư mục máy tính và tự động nạp vào màn hình xem trước.

### 2. Chọn Video Cục Bộ:
- Nếu bạn đã có sẵn file video trên máy tính, bấm nút **`Chọn video...`** để nạp file (hỗ trợ .mp4, .mkv, .avi, .mov).

### 3. Màn hình Xem Trước & Thao Tác Kéo Thả Vùng Làm Mờ (ROI):
- **Màn hình Canvas tương tác trực tiếp 2 chiều**:
  - **Kéo di chuyển (Move)**: Nhấp chuột vào giữa vùng chữ nhật màu xanh và kéo để di chuyển vùng làm mờ đến bất kỳ vị trí nào trên video.
  - **Co giãn 8 hướng (Resize)**: Nhấp vào một trong **8 điểm neo hình vuông** (4 góc và 4 cạnh) để kéo giãn hoặc thu nhỏ vùng làm mờ theo chiều mong muốn. Con trỏ chuột sẽ tự động thay đổi hướng mũi tên tương ứng.
  - **Vẽ vùng mới**: Nhấp chuột ra ngoài và kéo để vẽ một khung làm mờ hoàn toàn mới.
  - **Huy hiệu thông tin nổi**: Hiển thị kích thước thực `WxH`, tọa độ `X, Y` và phần trăm chiều cao video ngay phía trên hộp chọn.
- **Thanh trượt thời gian (Slider)**: Kéo qua lại để xem bất kỳ giây/frame nào trong video.
- **Khung tọa độ số**: Tự động nhảy số theo thao tác chuột, hoặc bạn có thể gõ số trực tiếp bằng bàn phím.
- **Các nút đặt nhanh vị trí**:
  - `15% Chân Video (Chuẩn)`: Tự động khoanh vùng chân video chuyên dụng cho phụ đề phim/video ngắn.
  - `20% Đáy`: Phù hợp với phụ đề 2 dòng hoặc kích thước chữ to.
  - `15% Đầu Video`: Dùng để che logo hoặc watermark ở góc trên.
  - `Toàn Màn Hình`: Phủ mờ toàn bộ khung hình.

### 4. Khối Điều Khiển Thực Thi Nổi Bật (Execution Panel):
- **Tùy chọn chế độ thực thi**:
  - ⚡ **Trọn gói: Tách Audio + Làm mờ Video** *(Khuyên dùng)*: Vừa tách audio để sẵn sàng dịch thuật, vừa làm mờ sạch chữ phụ đề cũ trên video.
  - 🎬 **Chỉ làm mờ phụ đề video (Xóa Hardsub)**: Chỉ xuất video đã làm mờ theo vùng ROI.
  - 🎵 **Chỉ tách âm thanh sang MP3**: Trích xuất nhanh audio chất lượng cao.
- **Mức độ làm mờ**: Có 3 mức tùy chọn: *Tiêu chuẩn (10:5)*, *Mạnh (20:10)*, *Nhẹ (5:2)*.
- **Nút `🚀 BẮT ĐẦU THỰC THI`**:
  - Nút bấm to màu xanh ngọc nổi bật ở cột phải.
  - Nhấn để chạy quy trình, có thanh tiến trình `%` thời gian thực và đếm giây chi tiết.
- **Sau khi hoàn tất**:
  - Nút **`📂 Mở Thư Mục Kết Quả`**: Mở ngay folder chứa file video/audio đã xuất.
  - Nút **`➡️ Sang Bước 2: Dịch Thuật AI`**: Tự động chuyển tiếp audio sang Tab 2 và mở sẵn giao diện dịch thuật.

---

## 4. TAB 2: DỊCH THUẬT NGỮ CẢNH AI (TWO-PASS TRANSLATION)

Đây là "trái tim" của hệ thống, giúp chuyển ngữ chuẩn xác theo văn phong đời thường của người Việt.

### Các Bước Thực Hiện:
1. **File phụ đề gốc (.srt, .ass)**:
   - Bấm `Chọn file...` để nạp file phụ đề gốc (tiếng Trung, tiếng Anh, v.v.).
   - Danh sách câu gốc sẽ lập tức hiển thị trên Bảng đối chiếu song ngữ ở giữa màn hình.
2. **Audio/Video kèm theo (Tùy chọn)**:
   - Nếu đã tách audio ở Tab 1, ô này sẽ tự động điền sẵn.
   - Nếu chưa có, bạn có thể bấm chọn file audio MP3/WAV tương ứng với video.
3. **Cơ chế Dịch 2 Lượt (Two-Pass Translation with Audio)**:
   - Tích chọn **`Bật nghe Audio hiểu ngữ cảnh (Pass 1)`**:
     - *Lượt 1*: Gemini sẽ "nghe" toàn bộ file audio để xác định: nhân vật nào đang nói, quan hệ giữa họ là gì (vợ chồng, đồng nghiệp, bạn bè, bố con), cảm xúc vui vẻ hay tức giận.
     - *Lượt 2*: Gemini dùng bộ nhớ ngữ cảnh này để dịch từng câu SRT. Nhờ vậy, câu dịch sẽ chuẩn xưng hô (anh - em, mày - tao), không bao giờ bị tình trạng câu trước xưng "tôi", câu sau lại xưng "em".
4. **Số luồng chia nhỏ**:
   - Chọn từ `1 phần` đến `5 phần`. Chia nhiều phần sẽ gửi song song giúp tốc độ dịch nhanh gấp 3 - 5 lần.
5. **Nút `🚀 Bắt Đầu Dịch AI`**:
   - Bấm để bắt đầu tiến trình. Thanh tiến trình sẽ hiển thị phần trăm hoàn thành.
   - Khi dịch xong, cột **Bản dịch tiếng Việt** trên bảng sẽ được cập nhật đầy đủ.
6. **Chỉnh sửa trực tiếp**:
   - Bạn có thể **click đúp chuột vào bất kỳ dòng nào** trên bảng để mở ô chỉnh sửa câu dịch theo ý muốn.
7. **Nút `🔍 Dịch lại câu sót chữ Trung`**:
   - Tự động rà soát toàn bộ danh sách, nếu phát hiện câu nào còn sót ký tự tiếng Trung/Hàn hoặc chưa dịch, ứng dụng sẽ gom lại và gửi Gemini dịch lại riêng các câu đó.
8. **Nút `💾 Lưu File SRT Tiếng Việt...`**:
   - Lưu phụ đề tiếng Việt đã hoàn thiện ra file `.srt`.
9. **Nút `🎙️ Chuyển sang Tab Lồng Tiếng ➡️`**:
   - Bấm nút này để tự động nạp toàn bộ phụ đề đã dịch sang Tab 3 để tiến hành đọc thuyết minh.

---

## 5. TAB 3: LỒNG TIẾNG AI & ĐỒNG BỘ ÂM THANH (AI DUBBING)

Tab này biến văn bản phụ đề thành giọng đọc audio chuyên nghiệp và ghép vào video.

### Các Chức Năng Chi Tiết:
1. **Động cơ TTS (TTS Engine)**:
   - **Edge-TTS (Khuyên dùng)**: Kết nối dịch vụ giọng đọc chất lượng cao của Microsoft, hoàn toàn miễn phí, không tốn tài nguyên máy tính.
   - **Local TTS v3 (Ngoại tuyến 48kHz)**: Chạy trực tiếp trên CPU/GPU của bạn qua ONNX Runtime với 25 giọng đọc Việt - Anh (Hải Đăng, Mai Anh, Thùy Dung, Minh Đức,...).
2. **Chọn giọng đọc (Voice)**:
   - `vi-VN-HoaiMyNeural`: Giọng nữ miền Bắc trầm ấm, truyền cảm, thích hợp đọc truyện, phim tâm lý, phóng sự.
   - `vi-VN-NamMinhNeural`: Giọng nam miền Bắc rõ ràng, dứt khoát, thích hợp review phim, tin tức, vlog.
3. **Tính năng Tự Động Co Giãn Nhịp Điệu (Time-Stretching)**:
   - *Vấn đề thực tế*: Câu tiếng Việt thường dài hơn câu tiếng Trung từ 20% đến 40%. Nếu đọc bình thường, giọng đọc sẽ bị trễ và đè lên câu nói tiếp theo của video.
   - *Giải pháp của DICH_VIDEO*: Tự động tính toán độ dài câu đọc. Nếu câu đọc dài hơn thời gian hiển thị của phụ đề, thuật toán sẽ tự động tăng tốc độ đọc mượt mà bằng FFmpeg `atempo` (giữ nguyên cao độ giọng nói, không méo tiếng) để giọng đọc kết thúc đúng lúc nhân vật ngậm miệng.
4. **Tính năng Audio Ducking (Hòa Âm Chuyên Nghiệp)**:
   - Tự động hạ âm lượng nhạc nền video gốc xuống mức 20% khi có giọng lồng tiếng phát lên. Khi giọng nói dứt, nhạc nền sẽ tự động tăng lại, tạo cảm giác âm thanh như trong rạp chiếu phim.
5. **Nút `🎙️ Bắt Đầu Lồng Tiếng AI`**:
   - Chọn nơi lưu file âm thanh (`.wav` hoặc `.mp3`).
   - Nếu bạn đã chọn Video gốc ở ô trên, ứng dụng sẽ **tự động xuất ra file Video MP4 hoàn chỉnh** có sẵn cả hình ảnh, phụ đề cứng và track giọng nói lồng tiếng hòa trộn.

---

## 6. TAB 4: CHUYỂN ĐỔI ĐỊNH DẠNG & TỐI ƯU PHỤ ĐỀ

Tab tiện ích hỗ trợ biên tập viên video:
1. **Tối Ưu Thời Lượng (`⚡ Tối Ưu Thời Lượng`)**:
   - Tự động cắt ngắn các câu phụ đề hiển thị quá lâu (quá 6 giây).
   - Tự động co thời điểm kết thúc nếu câu đó đè lên câu phía sau, giữ khoảng nghỉ 0.05s tự nhiên.
2. **Dịch Chuyển Thời Gian (`⏱️ Dịch Chuyển Time`)**:
   - Ví dụ video bị lệch âm thanh nhanh hơn phụ đề 1.5 giây: nhập `-1.5` và bấm nút để lùi toàn bộ timestamp về trước 1.5 giây.
3. **Chuyển Thành Kịch Bản Văn Bản (`📄 Chuyển Thành Kịch Bản`)**:
   - Loại bỏ toàn bộ số thứ tự và mốc thời gian, nối các câu thành một văn bản trơn có chấm phẩy đầy đủ, phục vụ đọc podcast hoặc gửi duyệt kịch bản.

---

## 7. KHẮC PHỤC SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING)

| Hiện tượng | Nguyên nhân | Cách khắc phục |
| :--- | :--- | :--- |
| **Báo lỗi "Chưa có API Key"** | Chưa nhập key hoặc key bị xoá | Bấm nút `🔑 Cài Đặt Gemini API` ở góc dưới bên trái, dán key và bấm `Lưu Cấu Hình`. |
| **Gặp lỗi Rate Limit (429)** | Key miễn phí bị giới hạn số lượt gọi/phút | Nhập thêm 2 - 3 key khác từ các tài khoản Google khác nhau vào danh sách; hệ thống sẽ tự động xoay vòng key. |
| **Không tải được video Douyin** | Link chia sẻ bị dính văn bản rác hoặc link hết hạn | Copy lại link trực tiếp từ trình duyệt hoặc app, dán vào ô link và bấm tải lại. |
| **Giọng đọc lồng tiếng bị chậm** | Bỏ chọn tính năng Auto Time-Stretch | Luôn tích chọn ô `Tự động co giãn tốc độ (Time-Stretch)` trong Tab Lồng tiếng. |
| **Không tìm thấy FFmpeg** | Chưa cài đặt FFmpeg trên Windows | Ứng dụng đã tự động nhận diện `ffmpeg.exe` trong thư mục `v-translate-07-11/_internal`. Bạn cũng có thể cài thêm FFmpeg vào PATH hệ thống nếu muốn. |

