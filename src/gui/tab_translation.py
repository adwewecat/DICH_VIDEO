# -*- coding: utf-8 -*-
"""
Tab Dịch Thuật Ngữ Cảnh AI (Context-Aware AI Translation Tab)
Dự án: DICH_VIDEO (100% Mã nguồn sạch, không mã độc, không DRM)

Mục đích:
- Nạp file phụ đề gốc (.srt, .ass) cần dịch sang tiếng Việt.
- Tùy chọn nạp kèm file Audio/Video để Gemini "nghe" toàn bộ ngữ cảnh (Two-Pass Translation).
- Dịch đồng thời hoặc chia nhiều luồng song song với cơ chế xoay vòng Key chống Rate Limit.
- Bảng xem trước song ngữ tương tác trực quan: xem câu gốc, bản dịch, cho phép chỉnh sửa từng dòng.
- Tự động quét và dịch lại các câu còn sót ký tự tiếng Trung (CJK).
- Xuất file SRT tiếng Việt hoặc chuyển trực tiếp sang Tab Lồng tiếng.
"""

from __future__ import annotations
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk

from ..core.config import config
from ..core.gemini_pool import gemini_pool
from ..core.subtitle_parser import (
    SubtitleEntry,
    contains_cjk,
    entries_to_srt,
    find_untranslated_cjk_entries,
    parse_srt,
    split_subtitles_into_parts,
)


class TranslationTab(ctk.CTkFrame):
    """Giao diện Tab 2: Dịch thuật phụ đề ngữ cảnh bằng Google Gemini AI."""

    def __init__(self, master, on_send_to_dubbing_cb=None):
        super().__init__(master)
        self.on_send_to_dubbing_cb = on_send_to_dubbing_cb

        # Dữ liệu nội bộ
        self.current_entries: list[SubtitleEntry] = []
        self.translated_entries: list[SubtitleEntry] = []
        self.is_translating: bool = False

        self._build_ui()

    def _build_ui(self):
        # 1. Khung trên cùng: Chọn file phụ đề & audio kèm theo
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=16, pady=(16, 8))

        # Chọn file SRT
        ctk.CTkLabel(top_frame, text="File phụ đề gốc (.srt, .ass):", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self.srt_path_entry = ctk.CTkEntry(top_frame, placeholder_text="Đường dẫn file phụ đề gốc...", width=380)
        self.srt_path_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=8)
        ctk.CTkButton(top_frame, text="Chọn file...", width=95, command=self._browse_srt_file).grid(row=0, column=2, padx=(4, 4), pady=8)
        self.auto_transcribe_btn = ctk.CTkButton(
            top_frame,
            text="🪄 Tự Tạo Phụ Đề AI (Transcribe)",
            width=210,
            fg_color="#6C5CE7",
            hover_color="#5843BE",
            font=ctk.CTkFont(weight="bold"),
            command=self._auto_transcribe_threaded,
        )
        self.auto_transcribe_btn.grid(row=0, column=3, padx=(4, 10), pady=8)

        # Chọn file Audio / Video ngữ cảnh (Tùy chọn)
        ctk.CTkLabel(top_frame, text="Audio/Video kèm theo (Tùy chọn):", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", padx=10, pady=8)
        self.audio_path_entry = ctk.CTkEntry(top_frame, placeholder_text="Chọn audio/video để AI nghe ngữ cảnh (Two-Pass)...", width=400)
        self.audio_path_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=8)
        ctk.CTkButton(top_frame, text="Chọn file...", width=100, command=self._browse_audio_file).grid(row=1, column=2, padx=10, pady=8)

        top_frame.columnconfigure(1, weight=1)

        # 2. Khung điều khiển & Tùy chọn dịch
        opt_frame = ctk.CTkFrame(self)
        opt_frame.pack(fill="x", padx=16, pady=(0, 8))

        # Tùy chọn chia phần dịch song song
        ctk.CTkLabel(opt_frame, text="Số luồng chia nhỏ:").pack(side="left", padx=(10, 4), pady=10)
        self.parts_combo = ctk.CTkComboBox(opt_frame, values=["1 phần (tuần tự)", "2 phần", "3 phần", "4 phần", "5 phần"], width=130)
        self.parts_combo.set("2 phần")
        self.parts_combo.pack(side="left", padx=4, pady=10)

        # Bật chế độ Two-Pass Audio Context
        self.two_pass_checkbox = ctk.CTkCheckBox(opt_frame, text="Bật nghe Audio hiểu ngữ cảnh (Pass 1)")
        self.two_pass_checkbox.select()
        self.two_pass_checkbox.pack(side="left", padx=16, pady=10)

        # Nút Bắt đầu dịch
        self.start_btn = ctk.CTkButton(
            opt_frame,
            text="🚀 Bắt Đầu Dịch AI",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_translation_threaded,
            fg_color="#00ADB5",
            hover_color="#007B83",
            width=160,
        )
        self.start_btn.pack(side="right", padx=10, pady=10)

        # Nút Quét & Dịch lại chữ Trung sót
        self.repair_cjk_btn = ctk.CTkButton(
            opt_frame,
            text="🔍 Dịch lại câu sót chữ Trung",
            command=self._repair_cjk_threaded,
            fg_color="#E84545",
            hover_color="#903749",
            width=180,
        )
        self.repair_cjk_btn.pack(side="right", padx=4, pady=10)

        # 3. Thanh tiến trình & Trạng thái
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.pack(fill="x", padx=16, pady=(0, 6))

        self.progress_bar = ctk.CTkProgressBar(status_frame)
        self.progress_bar.pack(fill="x", side="top", pady=(0, 4))
        self.progress_bar.set(0.0)

        self.status_label = ctk.CTkLabel(status_frame, text="Sẵn sàng nạp file phụ đề.", font=ctk.CTkFont(size=12))
        self.status_label.pack(side="left")

        self.count_label = ctk.CTkLabel(status_frame, text="Tổng số câu: 0", font=ctk.CTkFont(size=12, weight="bold"))
        self.count_label.pack(side="right")

        # 4. Bảng đối chiếu song ngữ (Treeview)
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        columns = ("stt", "start", "end", "original", "translated")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("stt", text="#")
        self.tree.heading("start", text="Bắt đầu")
        self.tree.heading("end", text="Kết thúc")
        self.tree.heading("original", text="Câu gốc")
        self.tree.heading("translated", text="Bản dịch tiếng Việt (Click đúp để sửa)")

        self.tree.column("stt", width=50, anchor="center")
        self.tree.column("start", width=90, anchor="center")
        self.tree.column("end", width=90, anchor="center")
        self.tree.column("original", width=350, anchor="w")
        self.tree.column("translated", width=420, anchor="w")

        scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_y.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self._on_tree_double_click)

        # 5. Khung chân trang: Xuất file & Chuyển tiếp
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=16, pady=(0, 16))

        self.save_srt_btn = ctk.CTkButton(
            bottom_frame,
            text="💾 Lưu File SRT Tiếng Việt...",
            command=self._save_translated_srt,
            width=180,
        )
        self.save_srt_btn.pack(side="left")

        self.send_to_dubbing_btn = ctk.CTkButton(
            bottom_frame,
            text="🎙️ Chuyển sang Tab Lồng Tiếng ➡️",
            command=self._send_to_dubbing,
            fg_color="#3F72AF",
            hover_color="#112D4E",
            width=220,
        )
        self.send_to_dubbing_btn.pack(side="right")

    # =================================================================
    # CÁC HÀM XỬ LÝ SỰ KIỆN GIAO DIỆN
    # =================================================================

    def _browse_srt_file(self):
        fpath = filedialog.askopenfilename(
            title="Chọn file phụ đề",
            filetypes=[("Phụ đề Subtitle", "*.srt;*.ass"), ("Tất cả", "*.*")],
        )
        if fpath:
            self.load_subtitle_file(fpath)

    def load_subtitle_file(self, fpath: str):
        """Nạp và phân tích file phụ đề hiển thị lên bảng."""
        self.srt_path_entry.delete(0, "end")
        self.srt_path_entry.insert(0, fpath)

        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            self.current_entries = parse_srt(content)
            self.translated_entries = [
                SubtitleEntry(index=e.index, start=e.start, end=e.end, text="")
                for e in self.current_entries
            ]

            self._refresh_table()
            self.count_label.configure(text=f"Tổng số câu: {len(self.current_entries)}")
            self.status_label.configure(text=f"Đã nạp file thành công: {os.path.basename(fpath)}")
        except Exception as e:
            messagebox.showerror("Lỗi đọc file", f"Không thể đọc file phụ đề:\n{e}")

    def _browse_audio_file(self):
        fpath = filedialog.askopenfilename(
            title="Chọn file Audio/Video ngữ cảnh",
            filetypes=[
                ("Audio/Video", "*.mp3;*.wav;*.m4a;*.mp4;*.mkv;*.avi"),
                ("Tất cả", "*.*"),
            ],
        )
        if fpath:
            self.audio_path_entry.delete(0, "end")
            self.audio_path_entry.insert(0, fpath)

    def _refresh_table(self):
        """Xóa và vẽ lại bảng Treeview dữ liệu phụ đề."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        from ..core.subtitle_parser import seconds_to_srt_time

        for i, orig in enumerate(self.current_entries):
            trans_text = ""
            if i < len(self.translated_entries):
                trans_text = self.translated_entries[i].text

            self.tree.insert(
                "",
                "end",
                values=(
                    orig.index,
                    seconds_to_srt_time(orig.start),
                    seconds_to_srt_time(orig.end),
                    orig.text,
                    trans_text,
                ),
            )

    def _on_tree_double_click(self, event):
        """Cho phép người dùng click đúp vào dòng để sửa nhanh bản dịch tiếng Việt."""
        selected = self.tree.selection()
        if not selected:
            return

        item = selected[0]
        values = self.tree.item(item, "values")
        stt = int(values[0])
        curr_trans = values[4]

        # Mở hộp thoại nhập text
        dialog = ctk.CTkInputDialog(
            text=f"Sửa bản dịch cho câu #{stt}:\n{values[3]}",
            title=f"Sửa câu #{stt}",
        )
        new_val = dialog.get_input()
        if new_val is not None:
            new_val = new_val.strip()
            # Cập nhật trong danh sách
            if 0 <= stt - 1 < len(self.translated_entries):
                self.translated_entries[stt - 1].text = new_val
                self.tree.item(item, values=(values[0], values[1], values[2], values[3], new_val))

    def _auto_transcribe_threaded(self):
        """Tự động dùng Gemini AI nghe âm thanh và tạo file phụ đề SRT kèm timestamp chuẩn."""
        audio_file = self.audio_path_entry.get().strip()
        if not audio_file or not os.path.isfile(audio_file):
            audio_file = filedialog.askopenfilename(
                title="Chọn file âm thanh hoặc video để AI trích xuất phụ đề",
                filetypes=[
                    ("Audio / Video", "*.mp3;*.wav;*.m4a;*.mp4;*.mkv;*.avi"),
                    ("Tất cả", "*.*"),
                ],
            )
            if not audio_file:
                return
            self.audio_path_entry.delete(0, "end")
            self.audio_path_entry.insert(0, audio_file)

        self.auto_transcribe_btn.configure(state="disabled")
        self.status_label.configure(text="Đang kết nối Gemini AI để trích xuất phụ đề...")
        self.progress_bar.set(0.15)

        def worker():
            def prog_cb(msg):
                self.after(0, lambda: self.status_label.configure(text=msg))

            ok, srt_text, srt_path = gemini_pool.transcribe_audio_to_srt(
                audio_path=audio_file,
                progress_callback=prog_cb,
            )

            def done():
                self.auto_transcribe_btn.configure(state="normal")
                self.progress_bar.set(1.0 if ok else 0.0)
                if ok and os.path.isfile(srt_path):
                    self.load_subtitle_file(srt_path)
                    messagebox.showinfo(
                        "Thành công",
                        f"Đã trích xuất thành công {len(self.current_entries)} câu phụ đề bằng AI!\n\nFile SRT đã lưu tại:\n{srt_path}"
                    )
                else:
                    self.status_label.configure(text="❌ Trích xuất phụ đề thất bại.")
                    messagebox.showerror("Lỗi trích xuất phụ đề", f"Không thể trích xuất phụ đề từ âm thanh:\n\n{srt_path}")

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    # =================================================================
    # TIẾN TRÌNH DỊCH THUẬT NỀN (THREADED WORKER)
    # =================================================================

    def _start_translation_threaded(self):
        if not self.current_entries:
            audio_fpath = self.audio_path_entry.get().strip()
            if audio_fpath and os.path.isfile(audio_fpath):
                ask = messagebox.askyesno(
                    "Tự Tạo Phụ Đề AI",
                    f"Bảng phụ đề hiện đang trống!\n\nBạn có muốn Gemini AI tự động nghe file âm thanh:\n'{os.path.basename(audio_fpath)}'\nvà trích xuất toàn bộ câu thoại thành file phụ đề (.srt) ngay bây giờ không?"
                )
                if ask:
                    self._auto_transcribe_threaded()
                return
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn hoặc nạp file phụ đề trước.")
            return

        if not gemini_pool.api_keys:
            messagebox.showerror(
                "Chưa có API Key",
                "Bạn chưa cấu hình Google Gemini API Key!\nVui lòng nhấn biểu tượng Cài đặt API để nhập key.",
            )
            return

        self.start_btn.configure(state="disabled")
        self.progress_bar.set(0.0)
        self.is_translating = True

        def worker():
            context_memory = ""
            # Lượt 1: Phân tích ngữ cảnh audio nếu có
            audio_fpath = self.audio_path_entry.get().strip()
            if self.two_pass_checkbox.get() and audio_fpath and os.path.isfile(audio_fpath):
                self.after(0, lambda: self.status_label.configure(text="[Pass 1] Đang tải audio và phân tích ngữ cảnh video..."))
                context_memory = gemini_pool.analyze_audio_context(audio_fpath)

            # Lượt 2: Dịch các câu phụ đề
            parts_str = self.parts_combo.get()
            num_parts = int(parts_str.split()[0]) if parts_str else 2
            chunks = split_subtitles_into_parts(self.current_entries, num_parts)

            total_chunks = len(chunks)
            completed_chunks = 0

            for chunk_data in chunks:
                part_no = chunk_data["part_no"]
                chunk_subs: list[SubtitleEntry] = chunk_data["subs"]
                orig_indices: list[int] = chunk_data["original_indices"]

                def update_cb(msg):
                    self.after(0, lambda: self.status_label.configure(text=f"[Phần {part_no}/{total_chunks}] {msg}"))

                raw_texts = [sub.text for sub in chunk_subs]
                try:
                    translated_texts = gemini_pool.translate_chunk(
                        texts=raw_texts,
                        context_memory=context_memory,
                        progress_callback=update_cb,
                    )
                    # Gán lại kết quả
                    for idx_in_chunk, orig_idx in enumerate(orig_indices):
                        if idx_in_chunk < len(translated_texts):
                            self.translated_entries[orig_idx].text = translated_texts[idx_in_chunk]

                except Exception as e:
                    self.after(0, lambda err=e: messagebox.showerror("Lỗi dịch", f"Có lỗi xảy ra khi dịch phần {part_no}:\n{err}"))
                    break

                completed_chunks += 1
                progress_val = completed_chunks / total_chunks
                self.after(0, lambda val=progress_val: self.progress_bar.set(val))
                self.after(0, self._refresh_table)

            def done():
                self.start_btn.configure(state="normal")
                self.is_translating = False
                self.progress_bar.set(1.0)
                self.status_label.configure(text="✅ Hoàn tất dịch thuật phụ đề bằng AI!")
                messagebox.showinfo("Thành công", f"Đã dịch hoàn tất {len(self.current_entries)} câu phụ đề!")

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _repair_cjk_threaded(self):
        """Quét và dịch lại các câu còn sót ký tự tiếng Trung/Hàn."""
        cjk_entries = []
        cjk_indices = []
        for i, trans_entry in enumerate(self.translated_entries):
            if contains_cjk(trans_entry.text) or not trans_entry.text.strip():
                cjk_entries.append(self.current_entries[i])
                cjk_indices.append(i)

        if not cjk_entries:
            messagebox.showinfo("Thông báo", "Không phát hiện câu nào còn sót ký tự tiếng Trung/Hàn!")
            return

        confirm = messagebox.askyesno(
            "Xác nhận",
            f"Phát hiện {len(cjk_entries)} câu còn sót ký tự CJK hoặc chưa dịch.\nBạn có muốn gửi dịch lại bằng Gemini không?",
        )
        if not confirm:
            return

        self.repair_cjk_btn.configure(state="disabled")

        def worker():
            raw_texts = [sub.text for sub in cjk_entries]
            try:
                translated = gemini_pool.translate_chunk(texts=raw_texts)
                for local_i, global_i in enumerate(cjk_indices):
                    if local_i < len(translated):
                        self.translated_entries[global_i].text = translated[local_i]

                self.after(0, self._refresh_table)
                self.after(0, lambda: messagebox.showinfo("Thành công", f"Đã sửa thành công {len(cjk_entries)} câu sót chữ Trung!"))
            except Exception as e:
                self.after(0, lambda err=e: messagebox.showerror("Lỗi sửa câu", f"Lỗi khi dịch lại:\n{err}"))
            finally:
                self.after(0, lambda: self.repair_cjk_btn.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _save_translated_srt(self):
        if not self.translated_entries or not any(e.text for e in self.translated_entries):
            messagebox.showwarning("Cảnh báo", "Chưa có nội dung bản dịch để lưu.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Lưu file phụ đề tiếng Việt",
            defaultextension=".srt",
            filetypes=[("SRT Subtitle", "*.srt"), ("Tất cả", "*.*")],
        )
        if save_path:
            srt_str = entries_to_srt(self.translated_entries)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(srt_str)
            messagebox.showinfo("Đã lưu", f"Đã lưu phụ đề tiếng Việt tại:\n{save_path}")

    def _send_to_dubbing(self):
        """Chuyển phụ đề đã dịch sang Tab Lồng tiếng."""
        if not self.translated_entries or not any(e.text for e in self.translated_entries):
            messagebox.showwarning("Cảnh báo", "Vui lòng hoàn thành bản dịch trước khi lồng tiếng.")
            return

        if self.on_send_to_dubbing_cb:
            self.on_send_to_dubbing_cb(self.translated_entries)

