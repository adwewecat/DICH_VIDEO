@echo off
chcp 65001 >nul
title DICH_VIDEO - Hệ Thống Dịch Video & Lồng Tiếng AI (Clean Edition)
cls

echo =====================================================================
echo           🎬 CHƯƠNG TRÌNH DICH_VIDEO - CLEAN EDITION 2.0
echo       Dịch Video, Trích Xuất Subtitle OCR & Lồng Tiếng AI
echo =====================================================================
echo.

:: 1. Kiểm tra môi trường Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% neq 0 (
        echo [!] LỖI: Máy tính của bạn chưa cài đặt Python hoặc chưa thêm Python vào biến PATH!
        echo [*] Vui lòng tải và cài đặt Python 3.10 trở lên tại: https://www.python.org/
        echo [*] Nhớ tích chọn "Add Python to PATH" trong lúc cài đặt.
        echo.
        pause
        exit /b 1
    ) else (
        set PY_CMD=py
    )
) else (
    set PY_CMD=python
)

:: 2. Hiển thị phiên bản Python đang dùng
echo [*] Đang sử dụng môi trường:
%PY_CMD% --version
echo.

:: 3. Kiểm tra và cài đặt thư viện cần thiết (nếu thiếu)
echo [*] Đang kiểm tra các thư viện cần thiết...
%PY_CMD% -c "import customtkinter, cv2, edge_tts, google.genai, yt_dlp" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Phát hiện thiếu một số thư viện, đang tự động cài đặt từ requirements.txt...
    echo [*] Quá trình này chỉ diễn ra lần đầu tiên, vui lòng đợi trong giây lát...
    %PY_CMD% -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo [!] Cảnh báo: Có lỗi xảy ra trong quá trình cài đặt thư viện!
        echo [*] Bạn hãy thử mở CMD với quyền Administrator và chạy lệnh: pip install -r requirements.txt
        echo.
        pause
    )
) else (
    echo [OK] Môi trường và các thư viện đã sẵn sàng!
)

echo.
echo =====================================================================
echo [*] Đang khởi động giao diện ứng dụng DICH_VIDEO...
echo =====================================================================
echo.

:: 4. Khởi chạy ứng dụng chính
%PY_CMD% main.py

:: 5. Nếu ứng dụng kết thúc bất thường, giữ cửa sổ console để đọc thông báo lỗi
if %errorlevel% neq 0 (
    echo.
    echo [!] Ứng dụng đã thoát với mã lỗi: %errorlevel%
    echo [*] Vui lòng xem thông báo lỗi ở trên để xử lý.
    pause
)

