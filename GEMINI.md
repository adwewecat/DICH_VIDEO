# 📜 GEMINI.md - HỒ SƠ QUẢN TRỊ & QUY TẮC DỰ ÁN DICH_VIDEO

> **LƯU Ý CỐT LÕI CHO MỌI AI / DEV**:
> File này là **kim chỉ nam và nhật ký liên tục** của dự án `DICH_VIDEO`.
> Dù máy tính bị cài lại Windows, đổi môi trường làm việc hay chuyển giao cho bất kỳ AI (Gemini, Claude, Codex, GPT...) hoặc Developer nào khác tiếp quản, **BẮT BUỘC PHẢI ĐỌC FILE NÀY ĐẦU TIÊN** để nắm toàn bộ bối cảnh, quy tắc bất di bất dịch, hiện trạng hệ thống và các bước cần thực thi tiếp theo.

---

## 📌 1. QUY TẮC BẤT DI BẤT DỊCH CỦA DỰ ÁN (STRICT RULES)

1. **Ghi chép liên tục vào `GEMINI.md`**:
   - Trước khi bắt đầu làm hoặc sửa bất kỳ tính năng nào, phải ghi rõ mục tiêu vào đây.
   - Sau khi hoàn thành hoặc có phát hiện mới, phải cập nhật tiến độ, trạng thái và việc cần làm tiếp theo.
2. **Tự động đẩy code lên GitHub ngay lập tức**:
   - Bất kỳ lúc nào thêm tính năng mới hoặc chỉnh sửa code, **BẮT BUỘC PHẢI PUSH NGAY LÊN GITHUB**:
     - **Remote Repository**: `https://github.com/adwewecat/DICH_VIDEO.git`
     - **Branch**: `main`
3. **Tiêu chuẩn Code Sạch 100% (Clean Code)**:
   - Loại bỏ hoàn toàn code thừa, dead code, file rác.
   - Tuyệt đối không để lại mã độc, backdoor, telemetry, kết nối server lạ, mã khóa bản quyền (DRM, license check, HWID, nạp tiền ví VietQR).
   - Code phải được ghi chú (comment) và tài liệu hóa (docstring) chi tiết từng dòng, từng hàm, từng khối logic để người đọc sau dễ hiểu và dễ bảo trì.
4. **Tích hợp REA (`morluto/rea`)**:
   - Dự án tích hợp công cụ dịch ngược chuyên sâu REA (Reverse Engineer Anything) từ `https://github.com/morluto/rea.git` dưới dạng Git Submodule tại `tools/rea` và đăng ký MCP Tool phục vụ phân tích dịch ngược nhị phân khi cần thiết.

---

## 🔍 2. BÁO CÁO PHÂN TÍCH AN NINH DỰ ÁN GỐC (`v-translate-07-11`)

Dự án gốc nằm trong thư mục `v-translate-07-11` là một bản build đóng gói PyInstaller chứa file thực thi `v-translate-07-11.exe` và thư viện lõi bị biên dịch đóng bằng Cython: `v_translate_07_11_core.cp310-win_amd64.pyd` (dung lượng 18.4 MB).

Qua quá trình dịch ngược tĩnh và rà soát sâu các chuỗi nhị phân (Static Binary Analysis) bằng Python và REA, chúng tôi đã phát hiện các thành phần **GÂY HẠI / KHÓA BẢN QUYỀN / KẾT NỐI SERVER LẠ** sau đây:

### 🚨 Danh sách các cơ chế hạn chế & kết nối server lạ phát hiện trong bản gốc:
1. **Cơ chế Khóa Bản Quyền & Kill-Switch (`_verify_license`, `_LicenseDialog`)**:
   - Ứng dụng liên tục kiểm tra bản quyền trực tuyến khi khởi động (`_check_primary_license`, `_load_license_key`).
   - Nếu máy tính không có mạng (`_verify_license._no_internet`) hoặc server báo lỗi, ứng dụng sẽ **khóa hoàn toàn giao diện, không cho sử dụng và thoát đột ngột (`sys.exit(1)`)**.
   - Hiển thị pop-up bắt liên hệ Zalo (`_show_zalo_contact`) để mua key kích hoạt.
   - Chạy tiến trình ngầm (`_LicenseSessionMonitor._refresh`) để thăm dò định kỳ và hủy quyền sử dụng từ xa.
2. **Thu thập thông tin định danh phần cứng (HWID Tracking)**:
   - Các hàm: `_collect_legacy_hwid_parts`, `_v2_hwid_digest`, `_license_cache_hwid_candidates`, `_get_hwid`, `_clean_hw_uuid`.
   - Quét thông số phần cứng thiết bị người dùng (UUID bo mạch chủ, MAC card mạng, ID Windows) và mã hóa gửi lên server từ xa nhằm ràng buộc 1 máy tính / 1 bản quyền.
3. **Cơ chế Thu phí / Ví tiền / Nạp tiền VietQR (`open_vietqr_topup_dialog`)**:
   - Các hàm: `ContextAwareTranslationTab._confirm_paid_wallet_run_dialog`, `open_vietqr_topup_dialog`, `_render_qr_for_amount`, `_poll_balance_loop`, `_PersonalWalletFallbackSession`.
   - Tác giả ban đầu tạo cổng nạp tiền thông qua tạo mã VietQR động, ép người dùng phải chuyển khoản ngân hàng để nạp tiền vào "Ví V-Translate", trừ tiền cho mỗi lần dịch hoặc lồng tiếng.
4. **Cơ chế Server Proxy ngầm (Google Apps Script Proxy)**:
   - Ứng dụng ghi nhận thông điệp: `"Call paid proxy JSON endpoints on Apps Script with lease auth & idempotent retry"`.
   - Thay vì gọi trực tiếp Google Gemini API bằng API Key của người dùng, luồng bị định tuyến qua Google Apps Script của tác giả kèm kiểm tra hạn mức `_FeatureLease`, `_FeatureUsageMeter`.
5. **Cưỡng ép cập nhật (`_show_update_dialog`, `_force_quit`)**:
   - Có thể từ chối chạy bản hiện tại nếu server từ xa báo có bản mới.

> **KẾT LUẬN VỀ AN NINH**:
> Bản gốc không chứa mã độc gián điệp đánh cắp ví crypto/mật khẩu trình duyệt, nhưng chứa **toàn bộ hệ thống kiểm soát độc quyền (DRM, HWID Spy, VietQR Paywall, Remote Kill-Switch, Lease Proxy)** gây phụ thuộc và mất quyền kiểm soát phần mềm.
> **GIẢI PHÁP ĐÃ THỰC HIỆN**: Xây dựng lại hệ thống mã nguồn mở 100% Clean Code tại `src/`, chạy trực tiếp bằng Python, loại bỏ sạch toàn bộ các đoạn code độc hại trên, cho phép người dùng tự nhập Google Gemini API Key cá nhân (miễn phí), chạy trực tiếp TTS Local hoặc Edge TTS offline không tốn 1 xu.

---

## 🏗️ 3. KIẾN TRÚC TỔNG THỂ CỦA ỨNG DỤNG (CLEAN ARCHITECTURE)

Dự án được tái cấu trúc thành ứng dụng Python độc lập, cấu trúc module rõ ràng trong thư mục `src/`:

```
Dich_video/
├── .gitignore                      # Cấu hình bỏ qua file nặng > 100MB, rác build
├── .gitmodules                     # Đăng ký Git Submodule (tools/rea)
├── GEMINI.md                       # Sổ tay quy tắc, kiến trúc & nhật ký dự án (File này)
├── README.md                       # Hướng dẫn tổng quan cho người dùng & Dev
├── HUONG_DAN_SU_DUNG.md            # Hướng dẫn sử dụng chi tiết từng chức năng, từng dòng
├── requirements.txt                # Danh sách thư viện Python chuẩn mực
├── run.bat                         # File khởi chạy 1-click trên Windows (Auto-check & Run)
├── main.py                         # Điểm khởi chạy ứng dụng chính (Clean GUI)
├── src/                            # Toàn bộ mã nguồn sạch của ứng dụng
│   ├── core/                       # Các module xử lý logic lõi
│   │   ├── config.py               # Quản lý lưu/nạp cấu hình người dùng an toàn
│   │   ├── gemini_pool.py          # Quản lý luân phiên và gọi API Google Gemini (Free API Key)
│   │   ├── subtitle_parser.py      # Xử lý định dạng SRT, ASS, sửa lỗi time, tối ưu thời lượng
│   │   ├── tts_engine.py           # Quản lý Text-to-Speech (Local TTS v3 48kHz, Edge-TTS)
│   │   ├── video_downloader.py     # Tải video Douyin, YouTube (yt-dlp), Bilibili không logo
│   │   └── media_merger.py         # Tích hợp FFmpeg ghép video, nhạc nền, audio lồng tiếng
│   └── gui/                        # Giao diện người dùng đồ họa (CustomTkinter)
│       ├── main_window.py          # Cửa sổ chính kết hợp 4 Tab chức năng và Sidebar
│       ├── tab_video_extract.py    # Tab 1: Trích xuất phụ đề video (OCR hardsub / làm mờ)
│       ├── tab_translation.py      # Tab 2: Dịch thuật ngữ cảnh bằng Gemini AI
│       ├── tab_dubbing.py          # Tab 3: Lồng tiếng AI (Local TTS v3 & Edge TTS)
│       ├── tab_text_conversion.py  # Tab 4: Chuyển đổi và hậu xử lý văn bản
│       └── dialog_api_settings.py  # Hộp thoại cài đặt API Keys Gemini trực quan
└── tools/                          # Các công cụ hỗ trợ & dịch ngược
    ├── rea/                        # Git Submodule: Reverse Engineer Anything
    ├── pyinstxtractor.py           # Bộ trích xuất gói PyInstaller
    ├── pycdc.exe                   # Trình dịch ngược bytecode Python 3.10
    └── analyze_pyd.py              # Script phân tích an ninh file nhị phân
```

---

## 📋 4. NHẬT KÝ THỰC THI (PROJECT PROGRESS LOG)

| Thời gian | Tác vụ đã thực hiện | Kết quả / Ghi chú | Trạng thái |
| :--- | :--- | :--- | :--- |
| **2026-11-08** | Khởi tạo Git Repo & Remote | Kết nối `https://github.com/adwewecat/DICH_VIDEO.git`, branch `main`. | ✅ Hoàn thành |
| **2026-11-08** | Cấu hình `.gitignore` | Bỏ qua các file nhị phân > 100MB (`ffmpeg.exe`, `ffprobe.exe`, `*.mp4`, `_internal`). | ✅ Hoàn thành |
| **2026-11-08** | Tích hợp `morluto/rea` | Clone và cấu hình thành Git Submodule `tools/rea`, kích hoạt REA MCP. | ✅ Hoàn thành |
| **2026-11-08** | Dịch ngược `v-translate-07-11` | Dùng `pyinstxtractor` và `pycdc`, giải mã PYZ và phân tích file nhị phân `v_translate_07_11_core`. | ✅ Hoàn thành |
| **2026-11-08** | Audit An ninh & Server lạ | Rà soát tìm thấy DRM, HWID tracking, VietQR paywall, Apps Script proxy. | ✅ Hoàn thành |
| **2026-11-08** | Tạo `GEMINI.md` & `README.md` | Tài liệu hóa toàn diện quy tắc, cấu trúc, phát hiện an ninh và hướng dẫn sử dụng. | ✅ Hoàn thành |
| **2026-11-08** | Xây dựng mã nguồn sạch (Clean Code) | Tái lập toàn bộ logic 4 Tab trong `src/`, loại bỏ sạch 100% mã độc / DRM. | ✅ Hoàn thành |
| **2026-11-08** | Viết `HUONG_DAN_SU_DUNG.md` | Tài liệu hướng dẫn sử dụng chi tiết từng chức năng, từng tab, từng dòng. | ✅ Hoàn thành |
| **2026-11-08** | Kiểm thử tự động (Unit Test) | Kiểm tra toàn bộ module core & GUI, kết quả 100% Pass không có lỗi. | ✅ Hoàn thành |
| **2026-11-08** | Tạo file `run.bat` | File chạy 1-click tự động kiểm tra Python, cài đặt thư viện thiếu và mở app. | ✅ Hoàn thành |
| **2026-11-08** | Cập nhật Model Gemini 3.8 Flash & Auto-fetch | Hỗ trợ Gemini 3.8 Flash, cho phép nhập model tùy ý và lấy danh sách live từ API. | ✅ Hoàn thành |
| **2026-11-08** | Khắc phục lỗi 404/503 & Tích hợp Auto-Fallback | Loại bỏ `gemini-2.5-flash` đã bị Google khai tử (404), mặc định `gemini-3.6-flash` cực nhanh và ổn định. Thêm cơ chế tự động chuyển model dự phòng khi gặp 404 hoặc 503 (quá tải) mà không gây gián đoạn. | ✅ Hoàn thành |
| **2026-11-08** | Push code lên GitHub | Đẩy toàn bộ thay đổi lên `adwewecat/DICH_VIDEO.git`. | ✅ Hoàn thành |

---

## 🎯 5. VIỆC CẦN LÀM TIẾP THEO (NEXT ACTIONS)

1. Người dùng có thể chạy trực tiếp ứng dụng bằng lệnh:
   ```bash
   python main.py
   ```
2. Thêm Google Gemini API Key vào mục Cài đặt và sử dụng bình thường.
3. Khi phát triển thêm các tính năng nâng cao (ví dụ: bổ sung thêm mô hình Whisper local ASR hoặc tích hợp thêm giọng đọc cloned), tiếp tục tuân thủ quy tắc bất di bất dịch: cập nhật `GEMINI.md` và push code ngay lên GitHub.
