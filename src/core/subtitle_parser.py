# -*- coding: utf-8 -*-
"""
Module Phân tích và Xử lý Phụ đề (Subtitle Parser & Processor)
Dự án: DICH_VIDEO (100% Mã nguồn sạch, không mã độc, không DRM)

Mục đích:
- Phân tích cú pháp (parse) và xuất bản các định dạng phụ đề chuẩn: SRT, ASS, TXT.
- Tự động sửa lỗi timestamp (ví dụ thiếu phần giờ MM:SS,mmm -> HH:MM:SS,mmm).
- Tối ưu hóa thời lượng hiển thị phụ đề (tránh phụ đề bị tràn hoặc đè lên câu kế tiếp).
- Dịch chuyển thời gian (Time-shift +/- N giây).
- Phát hiện các ký tự tiếng Trung/Hàn/Nhật (CJK) còn sót lại sau khi dịch.
- Chia nhỏ danh sách phụ đề thành N khối để dịch song song bằng Google Gemini.
"""

from __future__ import annotations
import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SubtitleEntry:
    """Đại diện cho một câu phụ đề đơn lẻ."""
    index: int
    start: float  # Thời điểm bắt đầu (tính bằng giây)
    end: float    # Thời điểm kết thúc (tính bằng giây)
    text: str     # Nội dung văn bản

    @property
    def duration(self) -> float:
        """Độ dài thời lượng của câu phụ đề tính bằng giây."""
        return max(0.0, self.end - self.start)

    def to_srt_block(self, override_index: Optional[int] = None) -> str:
        """Chuyển đổi câu phụ đề thành khối chuẩn SRT."""
        idx = override_index if override_index is not None else self.index
        start_str = seconds_to_srt_time(self.start)
        end_str = seconds_to_srt_time(self.end)
        return f"{idx}\n{start_str} --> {end_str}\n{self.text.strip()}\n"


# =====================================================================
# CÁC HÀM XỬ LÝ THỜI GIAN (TIMESTAMP UTILITIES)
# =====================================================================

def srt_time_to_seconds(time_str: str) -> float:
    """
    Chuyển đổi chuỗi thời gian SRT hoặc ASS sang số giây (float).
    Hỗ trợ các dạng:
      - 01:23:45,678 (SRT chuẩn)
      - 01:23:45.678 (Dấu chấm)
      - 23:45,678 (Thiếu giờ)
      - 1:23:45.67 (ASS centiseconds)
    """
    time_str = time_str.strip().replace(",", ".")
    parts = time_str.split(":")
    if len(parts) == 3:
        h = float(parts[0])
        m = float(parts[1])
        s = float(parts[2])
        return h * 3600.0 + m * 60.0 + s
    elif len(parts) == 2:
        m = float(parts[0])
        s = float(parts[1])
        return m * 60.0 + s
    elif len(parts) == 1:
        return float(parts[0])
    return 0.0


def seconds_to_srt_time(seconds: float) -> str:
    """Chuyển đổi số giây thành định dạng SRT: HH:MM:SS,mmm"""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        ms = 999
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def seconds_to_ass_time(seconds: float) -> str:
    """Chuyển đổi số giây thành định dạng ASS: H:MM:SS.cs (centiseconds)"""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h:01d}:{m:02d}:{s:02d}.{cs:02d}"


# =====================================================================
# BỘ PHÂN TÍCH CÚ PHÁP PHỤ ĐỀ (SUBTITLE PARSERS)
# =====================================================================

def parse_srt(content: str) -> List[SubtitleEntry]:
    """
    Phân tích chuỗi nội dung file SRT thành danh sách các SubtitleEntry.
    Hỗ trợ xử lý thông minh các dòng timestamp bị thiếu giờ hoặc lỗi khoảng trắng.
    """
    entries: List[SubtitleEntry] = []
    # Chuẩn hóa xuống dòng
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    # Biểu thức chính quy bắt khối phụ đề
    # Mẫu timestamp: (giờ:phút:giây,ms) --> (giờ:phút:giây,ms)
    time_regex = re.compile(
        r"(\d{1,2}:\d{2}:\d{2}[,\.]\d{2,3}|\d{1,2}:\d{2}[,\.]\d{2,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{2,3}|\d{1,2}:\d{2}[,\.]\d{2,3})"
    )

    blocks = re.split(r"\n\s*\n+", normalized.strip())
    current_index = 1

    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        match_line_idx = -1
        time_match = None

        # Tìm dòng chứa timestamp
        for i, line in enumerate(lines):
            m = time_regex.search(line)
            if m:
                match_line_idx = i
                time_match = m
                break

        if not time_match:
            continue

        start_sec = srt_time_to_seconds(time_match.group(1))
        end_sec = srt_time_to_seconds(time_match.group(2))

        # Đảm bảo start < end
        if end_sec <= start_sec:
            end_sec = start_sec + 1.0

        # Nội dung chữ là các dòng phía sau dòng timestamp
        text_lines = lines[match_line_idx + 1 :]
        text = "\n".join(text_lines).strip()

        if text:
            entries.append(
                SubtitleEntry(
                    index=current_index,
                    start=start_sec,
                    end=end_sec,
                    text=text,
                )
            )
            current_index += 1

    return entries


def entries_to_srt(entries: List[SubtitleEntry]) -> str:
    """Chuyển đổi danh sách SubtitleEntry thành chuỗi định dạng SRT hoàn chỉnh."""
    blocks = [entry.to_srt_block(override_index=i + 1) for i, entry in enumerate(entries)]
    return "\n".join(blocks)


def entries_to_plain_text(entries: List[SubtitleEntry], separator: str = ". ") -> str:
    """Gộp toàn bộ nội dung phụ đề thành một chuỗi văn bản liên tục duy nhất."""
    cleaned_texts = [entry.text.replace("\n", " ").strip() for entry in entries if entry.text.strip()]
    return separator.join(cleaned_texts)


# =====================================================================
# THUẬT TOÁN TỐI ƯU HÓA & XỬ LÝ NÂNG CAO
# =====================================================================

def optimize_subtitle_durations(
    entries: List[SubtitleEntry], max_duration: float = 6.0
) -> List[SubtitleEntry]:
    """
    Tối ưu hóa thời lượng phụ đề theo quy tắc chuẩn:
    1. end_time <= start_time + max_duration (tránh phụ đề bị treo quá lâu).
    2. end_time <= start_time của câu phụ đề liền kề phía sau (tránh bị đè phụ đề).
    3. start_time hoàn toàn được bảo toàn nguyên vẹn.
    """
    optimized: List[SubtitleEntry] = []
    n = len(entries)

    for i in range(n):
        entry = entries[i]
        start = entry.start
        end = entry.end

        # Quy tắc 1: Không vượt quá thời lượng tối đa cho phép
        if end > start + max_duration:
            end = start + max_duration

        # Quy tắc 2: Không được vượt quá thời điểm bắt đầu của câu kế tiếp
        if i + 1 < n:
            next_start = entries[i + 1].start
            if end > next_start:
                # Giữ khoảng nghỉ nhỏ 0.05 giây giữa 2 câu
                end = max(start + 0.3, next_start - 0.05)

        optimized.append(
            SubtitleEntry(
                index=i + 1,
                start=start,
                end=end,
                text=entry.text,
            )
        )

    return optimized


def shift_subtitles(entries: List[SubtitleEntry], offset_seconds: float) -> List[SubtitleEntry]:
    """Dịch chuyển toàn bộ phụ đề: cộng/trừ N giây vào cả start_time và end_time."""
    shifted = []
    for entry in entries:
        new_start = max(0.0, entry.start + offset_seconds)
        new_end = max(new_start + 0.1, entry.end + offset_seconds)
        shifted.append(
            SubtitleEntry(
                index=entry.index,
                start=new_start,
                end=new_end,
                text=entry.text,
            )
        )
    return shifted


def contains_cjk(text: str) -> bool:
    """Kiểm tra chuỗi có chứa ký tự tiếng Trung, Nhật, Hàn (CJK) hay không."""
    # Khối CJK Unified Ideographs và Hiragana/Katakana/Hangul
    cjk_pattern = re.compile(
        r"[\u4e00-\u9fff\u3400-\u4dbf\u20000-\u2a6df\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]"
    )
    return bool(cjk_pattern.search(text))


def find_untranslated_cjk_entries(entries: List[SubtitleEntry]) -> List[SubtitleEntry]:
    """Lọc ra các dòng phụ đề còn sót ký tự tiếng Trung/Hàn/Nhật để dịch lại."""
    return [entry for entry in entries if contains_cjk(entry.text)]


def split_subtitles_into_parts(
    entries: List[SubtitleEntry], num_parts: int
) -> List[Dict[str, Any]]:
    """
    Chia danh sách phụ đề thành num_parts phần đều nhau để gửi song song lên Gemini.
    Mỗi phần trả về dict gồm:
      - part_no: số thứ tự phần (1-based)
      - subs: danh sách SubtitleEntry của phần này
      - original_indices: chỉ mục gốc của từng câu để ghép lại sau khi dịch
    """
    if num_parts <= 1 or len(entries) <= num_parts:
        return [
            {
                "part_no": 1,
                "subs": entries,
                "original_indices": list(range(len(entries))),
            }
        ]

    chunk_size = math.ceil(len(entries) / num_parts)
    parts = []

    for p in range(num_parts):
        start_idx = p * chunk_size
        end_idx = min(len(entries), (p + 1) * chunk_size)
        if start_idx >= len(entries):
            break

        chunk_subs = entries[start_idx:end_idx]
        parts.append(
            {
                "part_no": p + 1,
                "subs": chunk_subs,
                "original_indices": list(range(start_idx, end_idx)),
            }
        )

    return parts
