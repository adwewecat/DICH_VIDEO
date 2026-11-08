# -*- coding: utf-8 -*-
import sys

bat_code = """@echo off
chcp 65001 >nul
cd /d "%~dp0"
title DICH_VIDEO - He Thong Dich Video va Long Tieng AI

echo =====================================================================
echo           CHƯƠNG TRÌNH DICH_VIDEO - CLEAN EDITION 2.0
echo       Dịch Video, Trích Xuất Subtitle OCR va Lồng Tiếng AI
echo =====================================================================
echo.

:: 1. Kiem tra Python
set PY_CMD=
where python >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=python
    goto :FOUND_PYTHON
)

where py >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=py
    goto :FOUND_PYTHON
)

if exist "%LOCALAPPDATA%\\Programs\\Python\\Python312\\python.exe" (
    set PY_CMD="%LOCALAPPDATA%\\Programs\\Python\\Python312\\python.exe"
    goto :FOUND_PYTHON
)

if exist "%LOCALAPPDATA%\\Programs\\Python\\Python310\\python.exe" (
    set PY_CMD="%LOCALAPPDATA%\\Programs\\Python\\Python310\\python.exe"
    goto :FOUND_PYTHON
)

echo [!] LOI: May tinh cua ban chua cai dat Python hoac chua them Python vao PATH!
echo [*] Vui long tai va cai dat Python 3.10 tro len tai: https://www.python.org/
echo [*] Nho tich chon "Add Python to PATH" trong luc cai dat.
echo.
pause
exit /b 1

:FOUND_PYTHON
echo [*] Dang su dung moi truong Python:
%PY_CMD% --version
echo.

:: 2. Kiem tra va cai dat thu vien (neu thieu)
echo [*] Dang kiem tra cac thu vien can thiet...
%PY_CMD% -c "import customtkinter, cv2, edge_tts, google.genai, yt_dlp" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Phat hien thieu mot so thu vien, dang tu dong cai dat tu requirements.txt...
    %PY_CMD% -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo [!] Canh bao: Co loi xay ra trong qua trinh cai dat thu vien!
        pause
    )
) else (
    echo [OK] Cac thu vien da san sang!
)

echo.
echo [*] Dang khoi dong giao dien DICH_VIDEO...
echo.

:: 3. Khoi chay ung dung chinh
%PY_CMD% main.py

if %errorlevel% neq 0 (
    echo.
    echo [!] Ung dung da thoat voi ma loi: %errorlevel%
    pause
)
"""

# Force CRLF
crlf_content = bat_code.replace("\r\n", "\n").replace("\n", "\r\n")
with open("run.bat", "wb") as f:
    f.write(crlf_content.encode("utf-8"))

print("Successfully wrote run.bat with CRLF!")

