# -*- coding: utf-8 -*-
"""
Module Xử lý Hậu kỳ & Hòa âm Video bằng FFmpeg (Media Merger & Post-Processing)
Dự án: DICH_VIDEO (100% Mã nguồn sạch, không mã độc, không DRM)

Mục đích:
- Tách audio gốc từ video sang MP3/WAV phục vụ nhận diện ngữ cảnh hoặc ASR.
- Làm mờ/xóa vùng phụ đề cứng (Video Subtitle Delogo/Blur) trên video gốc bằng bộ lọc FFmpeg.
- Hòa âm tiếng lồng tiếng AI với âm thanh gốc của video (Audio Ducking: tự giảm nhạc nền video xuống 20% khi có tiếng đọc thuyết minh).
- Đóng gói phụ đề mềm (soft-sub) hoặc gắn chết phụ đề cứng (hard-sub) vào video xuất bản cuối cùng.
"""

from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

from .tts_engine import find_ffmpeg_tool


class MediaMerger:
    """Điều phối toàn bộ tác vụ FFmpeg xử lý video và âm thanh."""

    def __init__(self):
        self.ffmpeg_bin = find_ffmpeg_tool("ffmpeg")
        self.ffprobe_bin = find_ffmpeg_tool("ffprobe")

    def get_duration(self, media_path: str) -> float:
        """Lấy tổng thời lượng video hoặc audio (tính bằng giây)."""
        if not os.path.isfile(media_path):
            return 0.0
        try:
            cmd = [
                self.ffprobe_bin,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                media_path,
            ]
            res = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
            return float(res.strip())
        except Exception:
            return 0.0

    def extract_audio(
        self,
        video_path: str,
        output_audio_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> bool:
        """Trích xuất âm thanh từ file video sang định dạng MP3 (192kbps)."""
        if not os.path.isfile(video_path):
            return False

        if progress_callback:
            progress_callback(10.0, "Đang khởi chạy bộ trích xuất audio FFmpeg...")

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "libmp3lame",
            "-ab", "192k",
            "-ar", "44100",
            output_audio_path,
        ]

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if progress_callback:
                progress_callback(100.0, "Trích xuất audio hoàn tất!")
            return os.path.isfile(output_audio_path) and os.path.getsize(output_audio_path) > 100
        except Exception as e:
            print(f"[MediaMerger] Lỗi trích xuất audio: {e}")
            return False

    def blur_subtitle_region(
        self,
        video_path: str,
        output_video_path: str,
        x: int,
        y: int,
        w: int,
        h: int,
        blur_intensity: str = "medium",
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> bool:
        """
        Làm mờ vùng chứa phụ đề cũ trên video bằng bộ lọc boxblur của FFmpeg.
        x, y, w, h: Tọa độ pixel của vùng phụ đề cần làm mờ.
        blur_intensity: "light" (nhẹ), "medium" (vừa), "heavy" (mạnh).
        """
        if not os.path.isfile(video_path):
            return False

        # Đảm bảo w và h là số chẵn cho tương thích libx264
        w = max(2, w - (w % 2))
        h = max(2, h - (h % 2))
        x = max(0, x - (x % 2))
        y = max(0, y - (y % 2))

        blur_param = "10:5"
        if blur_intensity == "light":
            blur_param = "5:2"
        elif blur_intensity == "heavy":
            blur_param = "20:10"

        # Bộ lọc làm mờ vùng chỉ định: cắt vùng -> làm mờ -> đè ngược lại video gốc
        filter_str = f"[0:v]crop={w}:{h}:{x}:{y},boxblur={blur_param}[blurred];[0:v][blurred]overlay={x}:{y}[v]"

        total_duration = self.get_duration(video_path)
        if progress_callback:
            progress_callback(0.0, "Bắt đầu tiến trình làm mờ video bằng FFmpeg...")

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i", video_path,
            "-filter_complex", filter_str,
            "-map", "[v]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-c:a", "copy",
            "-progress", "pipe:1",
            output_video_path,
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                universal_newlines=True,
                encoding="utf-8",
                errors="ignore",
            )

            if proc.stdout:
                for line in proc.stdout:
                    line = line.strip()
                    if line.startswith("out_time_ms=") and total_duration > 0:
                        try:
                            cur_ms = int(line.split("=")[1])
                            cur_sec = cur_ms / 1_000_000.0
                            pct = min(99.0, max(0.0, (cur_sec / total_duration) * 100.0))
                            if progress_callback:
                                progress_callback(
                                    pct,
                                    f"Đang làm mờ video: {pct:.1f}% ({cur_sec:.1f}s / {total_duration:.1f}s)"
                                )
                        except Exception:
                            pass

            proc.wait()
            if proc.returncode == 0 and os.path.isfile(output_video_path):
                if progress_callback:
                    progress_callback(100.0, "Đã hoàn tất làm mờ phụ đề video!")
                return True
            return False
        except Exception as e:
            print(f"[MediaMerger] Lỗi làm mờ vùng phụ đề: {e}")
            return False

    def burn_hardsub_and_merge_audio(
        self,
        video_path: str,
        subtitle_path: str,
        dubbed_audio_path: Optional[str],
        output_video_path: str,
        ducking_level: float = 0.2,
    ) -> bool:
        """
        Xuất bản video hoàn chỉnh:
        1. Gắn phụ đề cứng (Burn-in Subtitles) tiếng Việt vào video.
        2. Nếu có track lồng tiếng: hòa trộn track lồng tiếng với audio gốc của video (giảm âm lượng gốc xuống ducking_level).
        """
        if not os.path.isfile(video_path):
            return False

        # Chuẩn hóa đường dẫn cho FFmpeg filter (dấu gạch chéo ngược trên Windows)
        sub_escaped = subtitle_path.replace("\\", "/").replace(":", "\\:")

        if dubbed_audio_path and os.path.isfile(dubbed_audio_path):
            # Có track lồng tiếng: hòa âm nhạc nền gốc (volume=ducking_level) + giọng đọc (volume=1.0)
            filter_complex = (
                f"[0:v]subtitles='{sub_escaped}'[v];"
                f"[0:a]volume={ducking_level:.2f}[bg];"
                f"[1:a]volume=1.0[voice];"
                f"[bg][voice]amix=inputs=2:duration=first[a]"
            )
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-i", video_path,
                "-i", dubbed_audio_path,
                "-filter_complex", filter_complex,
                "-map", "[v]",
                "-map", "[a]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "20",
                "-c:a", "aac",
                "-b:a", "192k",
                output_video_path,
            ]
        else:
            # Không có lồng tiếng: chỉ gắn phụ đề
            filter_complex = f"[0:v]subtitles='{sub_escaped}'[v]"
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-i", video_path,
                "-filter_complex", filter_complex,
                "-map", "[v]",
                "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "20",
                "-c:a", "copy",
                output_video_path,
            ]

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return os.path.isfile(output_video_path) and os.path.getsize(output_video_path) > 1000
        except Exception as e:
            print(f"[MediaMerger] Lỗi xuất bản video: {e}")
            return False


# Singleton instance dùng chung
media_merger = MediaMerger()

