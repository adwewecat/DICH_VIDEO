# -*- coding: utf-8 -*-
"""
Module Tải Video Đa Nền Tảng (Video Downloader)
Dự án: DICH_VIDEO (100% Mã nguồn sạch, không mã độc, không DRM)

Mục đích:
- Tải video chất lượng cao từ Douyin (TikTok Trung Quốc sạch không dính watermark/logo),
  TikTok, YouTube, Bilibili, Facebook, Kuaishou,...
- Sử dụng trực tiếp thư viện `yt-dlp` chính hãng và cập nhật liên tục.
- Báo cáo tiến trình tải trực quan (tốc độ, phần trăm hoàn thành, ETA) lên giao diện.
"""

from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import yt_dlp

from .config import config


class VideoDownloader:
    """Quản lý tải video từ liên kết mạng xã hội."""

    def __init__(self):
        pass

    def download_video(
        self,
        url: str,
        output_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Optional[str]:
        """
        Tải video từ URL được cung cấp.
        Trả về đường dẫn file video đã tải về máy, hoặc None nếu thất bại.
        """
        if not url or not url.strip():
            return None

        clean_url = url.strip()
        # Trích xuất link nếu người dùng dán kèm text tiêu đề (ví dụ chia sẻ từ app Douyin/TikTok)
        match = re.search(r"https?://[^\s]+", clean_url)
        if match:
            clean_url = match.group(0)

        target_dir = output_dir or config.get("output_directory")
        Path(target_dir).mkdir(parents=True, exist_ok=True)

        downloaded_file: Optional[str] = None

        def _yt_hook(d: Dict[str, Any]):
            nonlocal downloaded_file
            if d.get("status") == "downloading" and progress_callback:
                total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded_bytes = d.get("downloaded_bytes") or 0
                percent = (downloaded_bytes / total_bytes * 100) if total_bytes > 0 else 0.0
                speed = d.get("speed") or 0
                eta = d.get("eta") or 0

                progress_callback({
                    "status": "downloading",
                    "percent": percent,
                    "downloaded_bytes": downloaded_bytes,
                    "total_bytes": total_bytes,
                    "speed": speed,
                    "eta": eta,
                })
            elif d.get("status") == "finished":
                downloaded_file = d.get("filename")
                if progress_callback:
                    progress_callback({
                        "status": "finished",
                        "percent": 100.0,
                        "filename": downloaded_file,
                    })

        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": os.path.join(target_dir, "%(title)s_%(id)s.%(ext)s"),
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [_yt_hook],
            # Thiết lập header để vượt qua chặn bot của Douyin / Bilibili
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            },
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(clean_url, download=True)
                if downloaded_file and os.path.isfile(downloaded_file):
                    return downloaded_file
                # Nếu file merge thành .mp4
                title = info.get("title", "video")
                video_id = info.get("id", "")
                candidate = os.path.join(target_dir, f"{title}_{video_id}.mp4")
                if os.path.isfile(candidate):
                    return candidate
                return downloaded_file
        except Exception as e:
            print(f"[Downloader] Lỗi khi tải video: {e}")
            return None


# Singleton instance dùng chung
video_downloader = VideoDownloader()
