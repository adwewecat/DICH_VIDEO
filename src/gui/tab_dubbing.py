# -*- coding: utf-8 -*-
"""
Tab Lồng Tiếng AI & Đồng Bộ Âm Thanh (AI Dubbing & Audio Sync Tab)
Dự án: DICH_VIDEO (100% Mã nguồn sạch, không mã độc, không DRM)

Mục đích:
- Tạo giọng đọc thuyết minh tiếng Việt tự động cho từng câu phụ đề.
- Hỗ trợ cả Edge-TTS (miễn phí tốc độ cao) và Local TTS v3 (chạy offline).
- Tự động co giãn nhịp điệu (Time-Stretching) để giọng đọc khớp từng mili-giây với khẩu hình.
- Tùy chọn hòa âm trực tiếp vào Video với cơ chế Audio Ducking (hạ nhỏ nhạc nền khi nói).
"""

from __future__ import annotations
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk

from ..core.config import config
from ..core.media_merger import media_merger
from ..core.subtitle_parser import SubtitleEntry, parse_srt, seconds_to_srt_time
from ..core.tts_engine import EDGE_VOICES, LOCAL_V3_VOICES, dubbing_manager


class DubbingTab(ctk.CTkFrame):
    """Giao diện Tab 3: Lồng tiếng AI & Đồng bộ âm thanh."""

    def __init__(self, master):
        super().__init__(master)
        self.current_entries: list[SubtitleEntry] = []
        self.is_dubbing: bool = False
        self._build_ui()

    def _build_ui(self):
        # 1. Khung chọn phụ đề & video gốc
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", padx=16, pady=(16, 8))

        # Chọn phụ đề SRT tiếng Việt
        ctk.CTkLabel(input_frame, text="Phụ đề tiếng Việt (.srt):", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self.srt_entry = ctk.CTkEntry(input_frame, placeholder_text="Chọn file phụ đề tiếng Việt...", width=380)
        self.srt_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=8)
        ctk.CTkButton(input_frame, text="Chọn file...", width=100, command=self._browse_srt).grid(row=0, column=2, padx=10, pady=8)

        # Chọn video gốc để ghép (Tùy chọn)
        ctk.CTkLabel(input_frame, text="Video gốc để ghép (Tùy chọn):", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", padx=10, pady=8)
        self.video_entry = ctk.CTkEntry(input_frame, placeholder_text="Chọn video gốc để hòa âm xuất bản video hoàn chỉnh...", width=380)
        self.video_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=8)
        ctk.CTkButton(input_frame, text="Chọn video...", width=100, command=self._browse_video).grid(row=1, column=2, padx=10, pady=8)

        input_frame.columnconfigure(1, weight=1)

        # 2. Khung cấu hình giọng đọc AI
        voice_frame = ctk.CTkFrame(self)
        voice_frame.pack(fill="x", padx=16, pady=(0, 8))

        # Chọn bộ máy phát âm
        ctk.CTkLabel(voice_frame, text="Động cơ TTS:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.engine_combo = ctk.CTkComboBox(voice_frame, values=["Edge-TTS (Trực tuyến, chất lượng cao)", "Local TTS v3 (Ngoại tuyến, 48kHz)"], width=260, command=self._on_engine_changed)
        self.engine_combo.set("Edge-TTS (Trực tuyến, chất lượng cao)")
        self.engine_combo.grid(row=0, column=1, padx=5, pady=10, sticky="w")

        # Chọn giọng đọc cụ thể
        ctk.CTkLabel(voice_frame, text="Giọng đọc:").grid(row=0, column=2, padx=(16, 5), pady=10, sticky="w")
        self.voice_combo = ctk.CTkComboBox(voice_frame, values=list(EDGE_VOICES.keys()), width=240)
        self.voice_combo.set("vi-VN-HoaiMyNeural")
        self.voice_combo.grid(row=0, column=3, padx=5, pady=10, sticky="w")

        # Tùy chọn khớp nhịp độ (Auto Time-Stretch)
        self.auto_tempo_cb = ctk.CTkCheckBox(voice_frame, text="Tự động co giãn tốc độ (Time-Stretch) khớp độ dài câu")
        self.auto_tempo_cb.select()
        self.auto_tempo_cb.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w")

        # Tùy chọn Audio Ducking
        self.ducking_cb = ctk.CTkCheckBox(voice_frame, text="Audio Ducking (Giảm 80% âm lượng video gốc khi có giọng nói)")
        self.ducking_cb.select()
        self.ducking_cb.grid(row=1, column=2, columnspan=2, padx=16, pady=(0, 10), sticky="w")

        # 3. Tiến trình & Bảng xem trước phụ đề
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.pack(fill="x", padx=16, pady=(0, 4))

        self.progress_bar = ctk.CTkProgressBar(status_frame)
        self.progress_bar.pack(fill="x", side="top", pady=(0, 4))
        self.progress_bar.set(0.0)

        self.status_label = ctk.CTkLabel(status_frame, text="Sẵn sàng thực hiện lồng tiếng.", font=ctk.CTkFont(size=12))
        self.status_label.pack(side="left")

        self.count_label = ctk.CTkLabel(status_frame, text="Số câu cần đọc: 0", font=ctk.CTkFont(size=12, weight="bold"))
        self.count_label.pack(side="right")

        # Bảng hiển thị phụ đề
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        columns = ("stt", "start", "end", "dur", "text")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("stt", text="#")
        self.tree.heading("start", text="Bắt đầu")
        self.tree.heading("end", text="Kết thúc")
        self.tree.heading("dur", text="Thời lượng")
        self.tree.heading("text", text="Nội dung câu lồng tiếng")

        self.tree.column("stt", width=50, anchor="center")
        self.tree.column("start", width=90, anchor="center")
        self.tree.column("end", width=90, anchor="center")
        self.tree.column("dur", width=80, anchor="center")
        self.tree.column("text", width=600, anchor="w")

        scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_y.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")

        # 4. Khung nút bấm thực thi
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=16, pady=(0, 16))

        self.start_dub_btn = ctk.CTkButton(
            bottom_frame,
            text="🎙️ Bắt Đầu Lồng Tiếng AI",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_dubbing_threaded,
            fg_color="#00ADB5",
            hover_color="#007B83",
            width=200,
            height=38,
        )
        self.start_dub_btn.pack(side="right")

    # =================================================================
    # SỰ KIỆN GIAO DIỆN
    # =================================================================

    def _on_engine_changed(self, choice):
        if "Local" in choice:
            self.voice_combo.configure(values=LOCAL_V3_VOICES)
            self.voice_combo.set("Hải Đăng")
        else:
            self.voice_combo.configure(values=list(EDGE_VOICES.keys()))
            self.voice_combo.set("vi-VN-HoaiMyNeural")

    def _browse_srt(self):
        fpath = filedialog.askopenfilename(
            title="Chọn file phụ đề tiếng Việt",
            filetypes=[("SRT Subtitle", "*.srt"), ("Tất cả", "*.*")],
        )
        if fpath:
            self.srt_entry.delete(0, "end")
            self.srt_entry.insert(0, fpath)
            self.load_subtitles_from_file(fpath)

    def _browse_video(self):
        fpath = filedialog.askopenfilename(
            title="Chọn video gốc để ghép",
            filetypes=[("Video files", "*.mp4;*.mkv;*.avi;*.mov"), ("Tất cả", "*.*")],
        )
        if fpath:
            self.video_entry.delete(0, "end")
            self.video_entry.insert(0, fpath)

    def load_subtitles_from_file(self, fpath: str):
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            self.load_subtitles(parse_srt(content))
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc file phụ đề:\n{e}")

    def load_subtitles(self, entries: list[SubtitleEntry]):
        """Nạp danh sách phụ đề trực tiếp vào bảng."""
        self.current_entries = entries
        for item in self.tree.get_children():
            self.tree.delete(item)

        for e in entries:
            dur_str = f"{e.duration:.2f}s"
            self.tree.insert(
                "",
                "end",
                values=(
                    e.index,
                    seconds_to_srt_time(e.start),
                    seconds_to_srt_time(e.end),
                    dur_str,
                    e.text,
                ),
            )

        self.count_label.configure(text=f"Số câu cần đọc: {len(entries)}")
        self.status_label.configure(text=f"Đã nạp {len(entries)} câu phụ đề.")

    # =================================================================
    # TIẾN TRÌNH LỒNG TIẾNG NỀN
    # =================================================================

    def _start_dubbing_threaded(self):
        if not self.current_entries:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn file phụ đề hoặc nạp phụ đề từ Tab 2.")
            return

        selected_voice = self.voice_combo.get().strip()
        auto_tempo = self.auto_tempo_cb.get()
        video_fpath = self.video_entry.get().strip()

        # Hỏi vị trí lưu file âm thanh hoặc video
        default_dir = config.get("output_directory")
        save_path = filedialog.asksaveasfilename(
            title="Chọn nơi lưu file âm thanh lồng tiếng",
            initialdir=default_dir,
            defaultextension=".wav",
            filetypes=[("WAV Audio", "*.wav"), ("MP3 Audio", "*.mp3")],
        )
        if not save_path:
            return

        self.start_dub_btn.configure(state="disabled")
        self.progress_bar.set(0.0)

        def worker():
            def progress_cb(current, total, msg):
                val = current / total if total > 0 else 0.0
                self.after(0, lambda: self.progress_bar.set(val))
                self.after(0, lambda: self.status_label.configure(text=msg))

            # Thực hiện lồng tiếng
            success = dubbing_manager.process_subtitles_to_audio_track(
                subtitles=self.current_entries,
                output_dubbed_audio=save_path,
                voice=selected_voice,
                auto_tempo=auto_tempo,
                progress_callback=progress_cb,
            )

            if not success:
                self.after(0, lambda: messagebox.showerror("Lỗi", "Không thể tạo file âm thanh lồng tiếng!"))
                self.after(0, lambda: self.start_dub_btn.configure(state="normal"))
                return

            # Nếu có video gốc -> tự động hòa âm xuất bản video
            final_video_msg = ""
            if video_fpath and os.path.isfile(video_fpath):
                self.after(0, lambda: self.status_label.configure(text="Đang hòa âm và gắn phụ đề vào video gốc..."))
                vid_out = os.path.splitext(save_path)[0] + "_final.mp4"
                
                # Tạo file SRT tạm nếu cần
                temp_srt = os.path.splitext(save_path)[0] + "_temp.srt"
                from ..core.subtitle_parser import entries_to_srt
                with open(temp_srt, "w", encoding="utf-8") as f:
                    f.write(entries_to_srt(self.current_entries))

                vid_ok = media_merger.burn_hardsub_and_merge_audio(
                    video_path=video_fpath,
                    subtitle_path=temp_srt,
                    dubbed_audio_path=save_path,
                    output_video_path=vid_out,
                    ducking_level=0.2 if self.ducking_cb.get() else 1.0,
                )
                try:
                    os.remove(temp_srt)
                except Exception:
                    pass

                if vid_ok:
                    final_video_msg = f"\n\nVideo hoàn chỉnh đã xuất tại:\n{vid_out}"

            def done():
                self.start_dub_btn.configure(state="normal")
                self.progress_bar.set(1.0)
                self.status_label.configure(text="✅ Hoàn tất lồng tiếng AI!")
                messagebox.showinfo(
                    "Thành công",
                    f"Đã xuất file âm thanh lồng tiếng tại:\n{save_path}{final_video_msg}",
                )

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

