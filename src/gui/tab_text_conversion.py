# -*- coding: utf-8 -*-
"""
Tab Chuyển Đổi & Hậu Xử Lý Văn Bản (Text Conversion & Post-Processing Tab)
Dự án: DICH_VIDEO (100% Mã nguồn sạch, không mã độc, không DRM)

Mục đích:
- Chuyển đổi phụ đề SRT sang văn bản liên tục (kịch bản trơn) phục vụ lồng tiếng hoặc đọc lại.
- Tối ưu hóa thời lượng hiển thị phụ đề theo quy tắc:
    + end_time <= start_time + max_duration
    + end_time <= start_time của phụ đề liền kề phía sau
    + start_time được giữ nguyên vẹn.
- Dịch chuyển thời gian (+/- N giây) để đồng bộ phụ đề khi bị lệch pha âm thanh.
- Tự động sửa lỗi timestamp định dạng sai (ví dụ thiếu phần giờ).
"""

from __future__ import annotations
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from ..core.subtitle_parser import (
    SubtitleEntry,
    entries_to_plain_text,
    entries_to_srt,
    optimize_subtitle_durations,
    parse_srt,
    shift_subtitles,
)


class TextConversionTab(ctk.CTkFrame):
    """Giao diện Tab 4: Chuyển đổi định dạng và tối ưu phụ đề."""

    def __init__(self, master):
        super().__init__(master)
        self.entries: list[SubtitleEntry] = []
        self._build_ui()

    def _build_ui(self):
        # 1. Khung chọn file phụ đề
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(top_frame, text="File phụ đề (.srt, .ass):", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10, pady=8)
        self.fpath_entry = ctk.CTkEntry(top_frame, placeholder_text="Chọn file phụ đề để chuyển đổi hoặc tối ưu...", width=450)
        self.fpath_entry.pack(side="left", fill="x", expand=True, padx=10, pady=8)

        ctk.CTkButton(top_frame, text="Chọn file...", width=100, command=self._browse_file).pack(side="right", padx=10, pady=8)

        # 2. Khung công cụ tiện ích (Toolbox)
        tools_frame = ctk.CTkFrame(self)
        tools_frame.pack(fill="x", padx=16, pady=(0, 8))

        # Tiện ích 1: Tối ưu thời lượng
        ctk.CTkLabel(tools_frame, text="Thời lượng tối đa (giây):").grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.max_dur_entry = ctk.CTkEntry(tools_frame, width=60)
        self.max_dur_entry.insert(0, "6.0")
        self.max_dur_entry.grid(row=0, column=1, padx=5, pady=8, sticky="w")

        ctk.CTkButton(tools_frame, text="⚡ Tối Ưu Thời Lượng", command=self._optimize_durations, fg_color="#393E46").grid(row=0, column=2, padx=10, pady=8)

        # Tiện ích 2: Dịch chuyển timestamp (+/- giây)
        ctk.CTkLabel(tools_frame, text="Dịch chuyển (+/- giây):").grid(row=0, column=3, padx=(16, 5), pady=8, sticky="w")
        self.shift_entry = ctk.CTkEntry(tools_frame, width=60)
        self.shift_entry.insert(0, "0.0")
        self.shift_entry.grid(row=0, column=4, padx=5, pady=8, sticky="w")

        ctk.CTkButton(tools_frame, text="⏱️ Dịch Chuyển Time", command=self._shift_time, fg_color="#393E46").grid(row=0, column=5, padx=10, pady=8)

        # Tiện ích 3: Chuyển đổi thành văn bản liên tục
        ctk.CTkButton(tools_frame, text="📄 Chuyển Thành Kịch Bản Văn Bản (Plain Text)", command=self._convert_to_plain_text, fg_color="#00ADB5", hover_color="#007B83").grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="ew")

        # 3. Khung hiển thị nội dung kết quả (Textbox)
        text_container = ctk.CTkFrame(self)
        text_container.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        self.text_display = ctk.CTkTextbox(text_container, font=ctk.CTkFont(family="Consolas", size=13))
        self.text_display.pack(fill="both", expand=True, padx=8, pady=8)

        # 4. Khung trạng thái & nút lưu
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=16, pady=(0, 16))

        self.stats_label = ctk.CTkLabel(bottom_frame, text="Số câu: 0 | Số ký tự: 0", font=ctk.CTkFont(size=12))
        self.stats_label.pack(side="left")

        ctk.CTkButton(bottom_frame, text="💾 Lưu Kết Quả...", command=self._save_result, width=150).pack(side="right")

    def _browse_file(self):
        fpath = filedialog.askopenfilename(
            title="Chọn file phụ đề",
            filetypes=[("Phụ đề", "*.srt;*.ass"), ("Tất cả", "*.*")],
        )
        if fpath:
            self.fpath_entry.delete(0, "end")
            self.fpath_entry.insert(0, fpath)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                self.entries = parse_srt(content)
                self.text_display.delete("1.0", "end")
                self.text_display.insert("1.0", entries_to_srt(self.entries))
                self._update_stats()
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể đọc file:\n{e}")

    def _update_stats(self):
        text = self.text_display.get("1.0", "end")
        char_count = len(text)
        line_count = len(self.entries)
        self.stats_label.configure(text=f"Số câu phụ đề: {line_count} | Tổng số ký tự: {char_count}")

    def _optimize_durations(self):
        """Tối ưu thời lượng phụ đề không để câu quá dài hoặc đè lên câu sau."""
        if not self.entries:
            messagebox.showwarning("Cảnh báo", "Vui lòng nạp file phụ đề trước.")
            return

        try:
            max_dur = float(self.max_dur_entry.get())
        except ValueError:
            messagebox.showerror("Lỗi", "Thời lượng tối đa không hợp lệ!")
            return

        self.entries = optimize_subtitle_durations(self.entries, max_duration=max_dur)
        self.text_display.delete("1.0", "end")
        self.text_display.insert("1.0", entries_to_srt(self.entries))
        self._update_stats()
        messagebox.showinfo("Thành công", f"Đã tối ưu thời lượng cho {len(self.entries)} câu phụ đề!")

    def _shift_time(self):
        """Cộng/trừ giây vào toàn bộ phụ đề."""
        if not self.entries:
            messagebox.showwarning("Cảnh báo", "Vui lòng nạp file phụ đề trước.")
            return

        try:
            offset = float(self.shift_entry.get())
        except ValueError:
            messagebox.showerror("Lỗi", "Số giây dịch chuyển không hợp lệ!")
            return

        self.entries = shift_subtitles(self.entries, offset_seconds=offset)
        self.text_display.delete("1.0", "end")
        self.text_display.insert("1.0", entries_to_srt(self.entries))
        self._update_stats()
        messagebox.showinfo("Thành công", f"Đã dịch chuyển toàn bộ phụ đề {offset:+.2f} giây!")

    def _convert_to_plain_text(self):
        """Chuyển phụ đề thành đoạn văn bản liên tục duy nhất."""
        if not self.entries:
            messagebox.showwarning("Cảnh báo", "Vui lòng nạp file phụ đề trước.")
            return

        plain_text = entries_to_plain_text(self.entries, separator=".\n\n")
        self.text_display.delete("1.0", "end")
        self.text_display.insert("1.0", plain_text)
        self._update_stats()

    def _save_result(self):
        content = self.text_display.get("1.0", "end").strip()
        if not content:
            messagebox.showwarning("Cảnh báo", "Không có nội dung để lưu.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Lưu file kết quả",
            defaultextension=".txt",
            filetypes=[("Văn bản TXT", "*.txt"), ("Phụ đề SRT", "*.srt"), ("Tất cả", "*.*")],
        )
        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Đã lưu", f"Đã lưu kết quả tại:\n{save_path}")

