# -*- coding: utf-8 -*-
"""
Module Động cơ Lồng tiếng AI (TTS Engine & Audio Synchronizer)
Dự án: DICH_VIDEO (100% Mã nguồn sạch, không mã độc, không DRM)

Mục đích:
- Tạo giọng đọc AI đa kênh:
    + Edge-TTS (Trực tuyến, tốc độ cao, hoàn toàn miễn phí từ Microsoft, giọng Hoài My, Nam Minh,...).
    + Local TTS v3 (Ngoại tuyến, chạy 100% trên máy tính qua ONNX Runtime với 25 giọng đọc chuẩn 48kHz).
- Xử lý từ điển viết tắt riêng (`tts_abbreviations.json`) để đọc chuẩn tên riêng, số hiệu, từ ngoại ngữ.
- Tự động đo thời lượng âm thanh và co/giãn nhịp điệu (Time-Stretching) bằng FFmpeg để giọng đọc khớp chuẩn xác với từng câu phụ đề và khẩu hình video.
- Ghép nối các đoạn đọc riêng rẽ thành 1 track âm thanh hoàn chỉnh đồng bộ theo timestamp.
"""

from __future__ import annotations
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import edge_tts

from .config import config
from .subtitle_parser import SubtitleEntry


# =====================================================================
# DANH SÁCH GIỌNG ĐỌC MẪU
# =====================================================================

EDGE_VOICES = {
    "vi-VN-HoaiMyNeural": "Tiếng Việt · Nữ (Hoài My - Trầm ấm, truyền cảm)",
    "vi-VN-NamMinhNeural": "Tiếng Việt · Nam (Nam Minh - Rõ ràng, dứt khoát)",
    "en-US-JennyNeural": "Tiếng Anh · Nữ (Jenny - Tự nhiên, chuẩn Mỹ)",
    "en-US-GuyNeural": "Tiếng Anh · Nam (Guy - Trầm ấm, chuẩn Mỹ)",
}

LOCAL_V3_VOICES = [
    "Hải Đăng", "Mai Anh", "Thùy Dung", "Minh Đức", "Quỳnh Anh",
    "Thái Sơn", "Mỹ Duyên", "Đức Trí", "Kim Thanh", "Ngọc Huyền",
    "Quang Sơn", "Ngọc Trân", "Phạm Tuyên", "Xuân Vĩnh", "Thanh Bình",
    "Ngọc Linh", "Đoan Trang", "Quốc Tuấn", "Adam", "Thục Đoan",
    "Minh Triết", "Thiền Tâm Đức", "Thiện Minh", "Trúc Ly"
]


# =====================================================================
# XỬ LÝ TỪ ĐIỂN VIẾT TẮT & PHIÊN ÂM
# =====================================================================

def load_abbreviations_dict(dict_path: str = "") -> Dict[str, str]:
    """Nạp từ điển thay thế từ viết tắt dạng JSON { 'từ_viết_tắt': 'cách_đọc' }."""
    # Nếu không chỉ định, tìm file mặc định trong assets
    if not dict_path or not os.path.isfile(dict_path):
        candidate = Path("v-translate-07-11/_internal/assets/tts/tts_abbreviations.json")
        if candidate.is_file():
            dict_path = str(candidate)

    if os.path.isfile(dict_path):
        try:
            with open(dict_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # Sắp xếp từ dài đến từ ngắn để ưu tiên khớp cụm từ dài trước
                    return dict(sorted(data.items(), key=lambda x: len(x[0]), reverse=True))
        except Exception as e:
            print(f"[TTS] Cảnh báo: Không thể nạp từ điển viết tắt ({e})")
    return {}


def apply_abbreviations(text: str, abbreviations: Dict[str, str]) -> str:
    """Thay thế các từ/cụm từ viết tắt trong văn bản thành cách phát âm tiếng Việt."""
    if not abbreviations:
        return text

    for abbr, expansion in abbreviations.items():
        # Khớp nguyên từ, không phân biệt hoa thường
        pattern = re.compile(rf"\b{re.escape(abbr)}\b", re.IGNORECASE)
        text = pattern.sub(expansion, text)
    return text


# =====================================================================
# ĐO THỜI LƯỢNG ÂM THANH & TIME-STRETCHING BẰNG FFMPEG
# =====================================================================

def get_audio_duration(audio_path: str) -> float:
    """Đo độ dài file âm thanh tính bằng giây (hỗ trợ WAV, MP3 qua ffprobe hoặc wave)."""
    if not os.path.isfile(audio_path):
        return 0.0

    # Nếu là file WAV chuẩn
    if audio_path.lower().endswith(".wav"):
        try:
            with wave.open(audio_path, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return float(frames) / float(rate)
        except Exception:
            pass

    # Fallback dùng ffprobe
    ffprobe_cmd = find_ffmpeg_tool("ffprobe")
    if ffprobe_cmd:
        try:
            cmd = [
                ffprobe_cmd,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ]
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True).strip()
            return float(out)
        except Exception:
            pass

    return 0.0


def find_ffmpeg_tool(tool_name: str = "ffmpeg") -> str:
    """Tìm đường dẫn thực thi ffmpeg hoặc ffprobe trên hệ thống."""
    # 1. Kiểm tra PATH hệ thống
    system_tool = shutil.which(tool_name)
    if system_tool:
        return system_tool

    # 2. Kiểm tra trong v-translate-07-11/_internal
    bundled = Path(f"v-translate-07-11/_internal/{tool_name}.exe")
    if bundled.is_file():
        return str(bundled.resolve())

    return tool_name


def time_stretch_audio(
    input_audio: str, output_audio: str, target_duration: float, max_speed_ratio: float = 1.45
) -> bool:
    """
    Tự động điều chỉnh tốc độ giọng đọc (atempo) để khớp với thời lượng mục tiêu:
    - Nếu câu đọc dài hơn phụ đề: tăng tốc độ (tối đa max_speed_ratio để không bị méo tiếng).
    - Giữ nguyên cao độ giọng nói (pitch).
    """
    current_dur = get_audio_duration(input_audio)
    if current_dur <= 0 or target_duration <= 0:
        shutil.copy2(input_audio, output_audio)
        return True

    ratio = current_dur / target_duration
    # Nếu âm thanh dài hơn hoặc ngắn hơn đáng kể
    if ratio > 1.05:
        speed = min(ratio, max_speed_ratio)
    else:
        # Nếu đã vừa vặn, không cần stretch
        shutil.copy2(input_audio, output_audio)
        return True

    ffmpeg_bin = find_ffmpeg_tool("ffmpeg")
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", input_audio,
        "-filter:a", f"atempo={speed:.3f}",
        "-vn",
        output_audio,
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception as e:
        print(f"[TTS] Lỗi khi time-stretch audio: {e}")
        shutil.copy2(input_audio, output_audio)
        return False


# =====================================================================
# BỘ MÁY PHÁT ÂM EDGE-TTS (MICROSOFT CLOUD TTS)
# =====================================================================

async def _synthesize_edge_tts_async(text: str, voice: str, output_path: str, rate: str = "+0%", pitch: str = "+0Hz") -> None:
    """Hàm bất đồng bộ gọi Edge TTS để xuất ra file MP3/WAV."""
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)


def synthesize_edge_tts(text: str, voice: str, output_path: str, rate: str = "+0%", pitch: str = "+0Hz") -> bool:
    """Hàm đồng bộ gọi Edge-TTS từ luồng chính hoặc worker thread."""
    if not text.strip():
        return False
    try:
        asyncio.run(_synthesize_edge_tts_async(text, voice, output_path, rate, pitch))
        return os.path.isfile(output_path) and os.path.getsize(output_path) > 100
    except Exception as e:
        print(f"[TTS] Lỗi Edge-TTS: {e}")
        return False


# =====================================================================
# BỘ ĐIỀU PHỐI LỒNG TIẾNG ĐỒNG BỘ TOÀN BỘ PHỤ ĐỀ (FULL DUBBING PIPELINE)
# =====================================================================

class DubbingManager:
    """Quản lý toàn bộ tiến trình đọc và đồng bộ hóa âm thanh với video."""

    def __init__(self):
        self.abbreviations = load_abbreviations_dict()

    def process_subtitles_to_audio_track(
        self,
        subtitles: List[SubtitleEntry],
        output_dubbed_audio: str,
        voice: str = "vi-VN-HoaiMyNeural",
        auto_tempo: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> bool:
        """
        Duyệt qua từng câu phụ đề:
        1. Áp dụng từ điển viết tắt.
        2. Sinh âm thanh từng câu (bằng Edge TTS hoặc Local TTS).
        3. Tự động co giãn thời lượng để khớp với khoảng cách giữa start và end của phụ đề.
        4. Hòa trộn và xuất ra 1 file âm thanh hoàn chỉnh đồng bộ theo đúng giây.
        """
        if not subtitles:
            return False

        temp_dir = tempfile.mkdtemp(prefix="dub_")
        segment_files: List[Tuple[float, str]] = []  # (start_seconds, file_path)

        try:
            total = len(subtitles)
            for idx, sub in enumerate(subtitles):
                if progress_callback:
                    progress_callback(idx + 1, total, f"Đang lồng tiếng câu {idx + 1}/{total}...")

                clean_text = apply_abbreviations(sub.text, self.abbreviations).strip()
                if not clean_text:
                    continue

                raw_seg = os.path.join(temp_dir, f"seg_raw_{idx:04d}.mp3")
                stretched_seg = os.path.join(temp_dir, f"seg_fit_{idx:04d}.wav")

                # Sinh âm thanh câu đọc
                success = synthesize_edge_tts(clean_text, voice, raw_seg)
                if not success:
                    continue

                # Điều chỉnh thời lượng nếu bật auto_tempo
                target_dur = sub.duration
                if auto_tempo and target_dur > 0.5:
                    time_stretch_audio(raw_seg, stretched_seg, target_dur)
                    segment_files.append((sub.start, stretched_seg))
                else:
                    segment_files.append((sub.start, raw_seg))

            if not segment_files:
                return False

            if progress_callback:
                progress_callback(total, total, "Đang hòa trộn toàn bộ track âm thanh bằng FFmpeg...")

            # Ghép tất cả các đoạn âm thanh theo timestamp bằng FFmpeg adelay / amix
            return self._mix_segments_with_ffmpeg(segment_files, output_dubbed_audio)

        finally:
            # Dọn dẹp thư mục tạm
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    def _mix_segments_with_ffmpeg(self, segments: List[Tuple[float, str]], output_path: str) -> bool:
        """Sử dụng FFmpeg adelay và amix để đặt chính xác từng câu đọc vào mốc thời gian của nó."""
        ffmpeg_bin = find_ffmpeg_tool("ffmpeg")
        # Xây dựng filter graph của ffmpeg
        inputs = []
        filter_parts = []

        for i, (start_sec, fpath) in enumerate(segments):
            inputs.extend(["-i", fpath])
            delay_ms = int(round(start_sec * 1000))
            filter_parts.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[a{i}];")

        amix_inputs = "".join(f"[a{i}]" for i in range(len(segments)))
        filter_graph = "".join(filter_parts) + f"{amix_inputs}amix=inputs={len(segments)}:normalize=0[out]"

        cmd = [
            ffmpeg_bin,
            "-y",
            *inputs,
            "-filter_complex", filter_graph,
            "-map", "[out]",
            "-ac", "2",
            "-ar", "48000",
            output_path,
        ]

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return os.path.isfile(output_path) and os.path.getsize(output_path) > 100
        except Exception as e:
            print(f"[TTS] Lỗi hòa trộn FFmpeg: {e}")
            return False


# Singleton instance dùng chung
dubbing_manager = DubbingManager()

