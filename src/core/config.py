# -*- coding: utf-8 -*-
"""
Module Quản lý Cấu hình Hệ thống (System Configuration Manager)
Dự án: DICH_VIDEO (100% Mã nguồn sạch, không mã độc, không DRM)

Mục đích:
- Nạp và lưu trữ an toàn các thiết lập người dùng (API Keys, mô hình AI, giọng đọc, đường dẫn thư mục).
- Lưu trữ cấu hình tại thư mục người dùng (%APPDATA%/DichVideo/settings.json) hoặc thư mục gốc.
- Đảm bảo hoàn toàn bảo mật: không gửi API Key hoặc dữ liệu ra bất kỳ máy chủ nào khác ngoài Google Gemini.
"""

from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List


class AppConfig:
    """Lớp quản lý cấu hình tập trung cho toàn bộ ứng dụng."""

    def __init__(self, config_filename: str = "settings.json"):
        # Xác định thư mục lưu trữ cấu hình an toàn
        appdata_dir = os.getenv("APPDATA")
        if appdata_dir:
            self.config_dir = Path(appdata_dir) / "DichVideo"
        else:
            self.config_dir = Path.home() / ".dich_video"

        # Tự động tạo thư mục cấu hình nếu chưa tồn tại
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.config_dir / config_filename

        # Cấu hình mặc định của hệ thống
        self.defaults: Dict[str, Any] = {
            # Danh sách Google Gemini API Keys (hỗ trợ nhiều key để tự động xoay vòng)
            "gemini_api_keys": [],
            # Mô hình Gemini mặc định
            "gemini_model": "gemini-2.5-flash",
            # Nhiệt độ sáng tạo (0.0 - 1.0, 0.3 là tối ưu cho dịch thuật chuẩn xác)
            "gemini_temperature": 0.3,
            # Cấp độ suy nghĩ (Thinking Level) cho các model Gemini 2.0+ Flash Thinking
            "thinking_level": "medium",
            # Giọng đọc TTS mặc định (Edge TTS hoặc Local TTS)
            "tts_engine": "edge_tts",
            "tts_voice": "vi-VN-HoaiMyNeural",
            "tts_speed": "+0%",
            "tts_pitch": "+0Hz",
            # Tự động điều chỉnh tốc độ đọc (time-stretching) để vừa khít thời lượng phụ đề gốc
            "auto_tempo_sync": True,
            # Audio Ducking: Giảm âm lượng nhạc nền video khi có tiếng lồng tiếng
            "audio_ducking_level": 0.2,
            # Thư mục xuất file kết quả mặc định
            "output_directory": str(Path.home() / "Videos" / "DichVideo_Output"),
            # Bật từ điển viết tắt
            "abbreviations_enabled": True,
            # Đường dẫn từ điển viết tắt riêng
            "abbreviations_path": "",
            # Giao diện
            "appearance_mode": "dark",
            "color_theme": "blue"
        }

        # Dữ liệu cấu hình hiện tại trong bộ nhớ
        self.data: Dict[str, Any] = self.defaults.copy()
        self.load()

    def load(self) -> None:
        """Đọc file cấu hình JSON từ đĩa. Nếu file chưa có hoặc lỗi, nạp giá trị mặc định."""
        if self.config_path.is_file():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved_data = json.load(f)
                    if isinstance(saved_data, dict):
                        self.data.update(saved_data)
            except Exception as e:
                print(f"[Config] Cảnh báo: Không thể đọc file cấu hình, dùng mặc định ({e})")

    def save(self) -> None:
        """Ghi đè cấu hình hiện tại ra file JSON trên đĩa."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] Lỗi: Không thể lưu cấu hình ({e})")

    def get(self, key: str, default: Any = None) -> Any:
        """Lấy giá trị theo key, nếu không có thì trả về default hoặc giá trị mặc định hệ thống."""
        return self.data.get(key, self.defaults.get(key, default))

    def set(self, key: str, value: Any) -> None:
        """Gán giá trị cho key và lưu tự động."""
        self.data[key] = value
        self.save()

    def get_gemini_keys(self) -> List[str]:
        """Lấy danh sách các Google Gemini API Keys hợp lệ."""
        keys = self.data.get("gemini_api_keys", [])
        if isinstance(keys, list):
            return [k.strip() for k in keys if isinstance(k, str) and k.strip()]
        return []

    def set_gemini_keys(self, keys: List[str]) -> None:
        """Cập nhật danh sách Google Gemini API Keys."""
        clean_keys = [k.strip() for k in keys if isinstance(k, str) and k.strip()]
        self.set("gemini_api_keys", clean_keys)


# Singleton instance để các module dùng chung
config = AppConfig()
