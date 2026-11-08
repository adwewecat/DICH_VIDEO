# -*- coding: utf-8 -*-
"""
Tab Tải Video & Trích Xuất Phụ Đề (Video Downloader & Subtitle Extraction Tab)
Dự án: DICH_VIDEO (100% Mã nguồn sạch, không mã độc, không DRM)

Mục đích:
- Tải video không dính logo từ Douyin, TikTok, YouTube, Bilibili, Facebook qua yt-dlp.
- Xem trước khung hình video bằng OpenCV, kéo thanh trượt để kiểm tra mọi thời điểm trong video.
- Thiết lập tọa độ vùng phụ đề cần nhận diện hoặc làm mờ (ROI).
- Tách nhanh âm thanh video sang file MP3 chất lượng cao để sẵn sàng cho quy trình dịch ngữ cảnh.
- Làm mờ/xóa vùng phụ đề cũ bằng bộ lọc tối ưu của FFmpeg.
"""

from __future__ import annotations
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import cv2
from PIL import Image

from ..core.config import config
from ..core.media_merger import media_merger
from ..core.video_downloader import video_downloader


class VideoExtractTab(ctk.CTkFrame):
    """Giao diện Tab 1: Tải video, trích xuất audio và xử lý vùng phụ đề."""

    def __init__(self, master, on_extracted_audio_cb=None):
        super().__init__(master)
        self.on_extracted_audio_cb = on_extracted_audio_cb

        self.current_video_path: str = ""
        self.cap: cv2.VideoCapture | None = None
        self.total_frames: int = 0
        self.video_fps: float = 30.0
        self.video_width: int = 0
        self.video_height: int = 0

        self._build_ui()

    def _build_ui(self):
        # 1. Khung tải video từ link
        dl_frame = ctk.CTkFrame(self)
        dl_frame.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(dl_frame, text="Dán Link Video (Douyin, TikTok, YouTube,...):", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.url_entry = ctk.CTkEntry(dl_frame, placeholder_text="https://v.douyin.com/... hoặc https://www.youtube.com/watch?v=...", width=450)
        self.url_entry.grid(row=0, column=1, padx=10, pady=8, sticky="ew")

        self.dl_btn = ctk.CTkButton(dl_frame, text="⬇️ Tải Video Sạch", command=self._download_video_threaded, width=140, fg_color="#00ADB5", hover_color="#007B83")
        self.dl_btn.grid(row=0, column=2, padx=10, pady=8)

        dl_frame.columnconfigure(1, weight=1)

        # 2. Khung chọn file video cục bộ
        file_frame = ctk.CTkFrame(self)
        file_frame.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(file_frame, text="Hoặc chọn file video trên máy:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10, pady=8)
        self.video_path_label = ctk.CTkLabel(file_frame, text="Chưa có video nào được chọn", text_color="gray", anchor="w")
        self.video_path_label.pack(side="left", fill="x", expand=True, padx=10, pady=8)

        ctk.CTkButton(file_frame, text="Chọn video...", width=120, command=self._browse_local_video).pack(side="right", padx=10, pady=8)

        # 3. Khung xem trước video & Điều khiển vị trí vùng phụ đề
        preview_container = ctk.CTkFrame(self)
        preview_container.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # Khung bên trái: Màn hình preview
        left_preview = ctk.CTkFrame(preview_container)
        left_preview.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        self.preview_canvas = tk.Canvas(left_preview, bg="#1a1a1a", highlightthickness=0)
        self.preview_canvas.pack(fill="both", expand=True, padx=4, pady=4)

        # Thanh trượt frame
        self.seek_slider = ctk.CTkSlider(left_preview, from_=0, to=100, command=self._on_seek_slider)
        self.seek_slider.pack(fill="x", padx=10, pady=(4, 8))
        self.seek_slider.set(0)

        # Khung bên phải: Tọa độ vùng phụ đề (ROI) & Tác vụ nhanh
        right_panel = ctk.CTkFrame(preview_container, width=280)
        right_panel.pack(side="right", fill="y", padx=8, pady=8)

        ctk.CTkLabel(right_panel, text="📐 Vùng Phụ Đề (ROI):", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 4))
        ctk.CTkLabel(right_panel, text="Xác định tọa độ vùng phụ đề cũ\nđể OCR hoặc làm mờ:", font=ctk.CTkFont(size=12), text_color="gray").pack(anchor="w", padx=10, pady=(0, 10))

        # Nhập tọa độ X, Y, W, H
        self.roi_x_entry = self._create_coord_row(right_panel, "Tọa độ X (cột bắt đầu):", "0")
        self.roi_y_entry = self._create_coord_row(right_panel, "Tọa độ Y (hàng bắt đầu):", "0")
        self.roi_w_entry = self._create_coord_row(right_panel, "Chiều rộng W (pixels):", "0")
        self.roi_h_entry = self._create_coord_row(right_panel, "Chiều cao H (pixels):", "0")

        # Nút tự động chọn vùng phụ đề chân video
        ctk.CTkButton(right_panel, text="Tự đặt vùng chân video (15% đáy)", command=self._set_bottom_roi, fg_color="#393E46").pack(fill="x", padx=10, pady=(8, 4))

        # Tác vụ 1: Tách Audio nhanh sang MP3
        ctk.CTkLabel(right_panel, text="⚙️ Tác Vụ Nhanh:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(16, 4))

        self.extract_audio_btn = ctk.CTkButton(
            right_panel,
            text="🎵 Tách Audio sang MP3",
            command=self._extract_audio_threaded,
            fg_color="#3F72AF",
            hover_color="#112D4E",
        )
        self.extract_audio_btn.pack(fill="x", padx=10, pady=4)

        # Tác vụ 2: Làm mờ vùng phụ đề cũ
        self.blur_video_btn = ctk.CTkButton(
            right_panel,
            text="✨ Làm Mờ Vùng Phụ Đề Cũ",
            command=self._blur_video_threaded,
            fg_color="#E84545",
            hover_color="#903749",
        )
        self.blur_video_btn.pack(fill="x", padx=10, pady=4)

        # 4. Thanh trạng thái dưới cùng
        self.status_label = ctk.CTkLabel(self, text="Sẵn sàng nạp video.", font=ctk.CTkFont(size=12))
        self.status_label.pack(side="left", padx=20, pady=(0, 12))

    def _create_coord_row(self, parent, label_text: str, default_val: str) -> ctk.CTkEntry:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(row, text=label_text, font=ctk.CTkFont(size=12)).pack(side="left")
        entry = ctk.CTkEntry(row, width=70)
        entry.insert(0, default_val)
        entry.pack(side="right")
        return entry

    # =================================================================
    # QUẢN LÝ VIDEO & PREVIEW
    # =================================================================

    def _browse_local_video(self):
        fpath = filedialog.askopenfilename(
            title="Chọn file video",
            filetypes=[("Video files", "*.mp4;*.mkv;*.avi;*.mov;*.flv;*.webm"), ("Tất cả", "*.*")],
        )
        if fpath:
            self.load_video(fpath)

    def load_video(self, video_path: str):
        """Mở video bằng OpenCV và hiển thị frame đầu tiên."""
        if not os.path.isfile(video_path):
            return

        if self.cap:
            self.cap.release()

        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            messagebox.showerror("Lỗi", "Không thể mở file video bằng OpenCV!")
            return

        self.current_video_path = video_path
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.video_fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.video_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.video_path_label.configure(
            text=f"{os.path.basename(video_path)} ({self.video_width}x{self.video_height}, {self.video_fps:.1f} fps)",
            text_color="#EEEEEE",
        )

        self.seek_slider.configure(to=max(1, self.total_frames - 1))
        self.seek_slider.set(0)

        # Mặc định vùng ROI 15% đáy
        self._set_bottom_roi()
        # Hiển thị frame đầu
        self._display_frame_at(0)
        self.status_label.configure(text=f"Đã nạp video: {os.path.basename(video_path)}")

    def _display_frame_at(self, frame_idx: int):
        if not self.cap or not self.cap.isOpened():
            return

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return

        # Đổi màu BGR sang RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Vẽ hình chữ nhật ROI lên khung hình preview
        try:
            rx = int(self.roi_x_entry.get())
            ry = int(self.roi_y_entry.get())
            rw = int(self.roi_w_entry.get())
            rh = int(self.roi_h_entry.get())
            cv2.rectangle(rgb_frame, (rx, ry), (rx + rw, ry + rh), (0, 255, 128), 2)
        except Exception:
            pass

        # Resize để vừa vặn với kích thước Canvas
        c_w = max(100, self.preview_canvas.winfo_width())
        c_h = max(100, self.preview_canvas.winfo_height())

        h, w, _ = rgb_frame.shape
        scale = min(c_w / w, c_h / h)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))

        resized = cv2.resize(rgb_frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        pil_img = Image.fromarray(resized)

        # Chuyển đổi sang PhotoImage cho Tkinter Canvas
        from PIL import ImageTk
        self._tk_img = ImageTk.PhotoImage(pil_img)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(c_w // 2, c_h // 2, image=self._tk_img, anchor="center")

    def _on_seek_slider(self, val):
        frame_idx = int(val)
        self._display_frame_at(frame_idx)

    def _set_bottom_roi(self):
        """Tự động tính toán vùng phụ đề chiếm 15% phía đáy video."""
        if self.video_width > 0 and self.video_height > 0:
            roi_h = int(self.video_height * 0.16)
            roi_y = int(self.video_height * 0.82)
            roi_w = int(self.video_width * 0.90)
            roi_x = int(self.video_width * 0.05)

            self.roi_x_entry.delete(0, "end")
            self.roi_x_entry.insert(0, str(roi_x))
            self.roi_y_entry.delete(0, "end")
            self.roi_y_entry.insert(0, str(roi_y))
            self.roi_w_entry.delete(0, "end")
            self.roi_w_entry.insert(0, str(roi_w))
            self.roi_h_entry.delete(0, "end")
            self.roi_h_entry.insert(0, str(roi_h))

            curr_frame = int(self.seek_slider.get())
            self._display_frame_at(curr_frame)

    # =================================================================
    # TẢI VIDEO & TÁC VỤ NỀN
    # =================================================================

    def _download_video_threaded(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập liên kết video!")
            return

        self.dl_btn.configure(state="disabled")
        self.status_label.configure(text="Đang kết nối và tải video bằng yt-dlp...")

        def worker():
            def progress_cb(data):
                percent = data.get("percent", 0.0)
                self.after(0, lambda: self.status_label.configure(text=f"Đang tải video: {percent:.1f}%"))

            fpath = video_downloader.download_video(url=url, progress_callback=progress_cb)

            def done():
                self.dl_btn.configure(state="normal")
                if fpath and os.path.isfile(fpath):
                    self.load_video(fpath)
                    messagebox.showinfo("Thành công", f"Đã tải video sạch không logo thành công:\n{fpath}")
                else:
                    messagebox.showerror("Thất bại", "Không thể tải video từ liên kết này. Vui lòng kiểm tra lại link.")

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _extract_audio_threaded(self):
        if not self.current_video_path:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn video trước.")
            return

        out_audio = os.path.splitext(self.current_video_path)[0] + ".mp3"
        self.extract_audio_btn.configure(state="disabled")
        self.status_label.configure(text="Đang trích xuất audio MP3 bằng FFmpeg...")

        def worker():
            ok = media_merger.extract_audio(self.current_video_path, out_audio)

            def done():
                self.extract_audio_btn.configure(state="normal")
                if ok:
                    self.status_label.configure(text=f"Đã tách audio: {os.path.basename(out_audio)}")
                    messagebox.showinfo("Thành công", f"Đã trích xuất audio thành công tại:\n{out_audio}")
                    if self.on_extracted_audio_cb:
                        self.on_extracted_audio_cb(out_audio)
                else:
                    messagebox.showerror("Lỗi", "Không thể trích xuất audio từ video.")

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _blur_video_threaded(self):
        if not self.current_video_path:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn video trước.")
            return

        try:
            rx = int(self.roi_x_entry.get())
            ry = int(self.roi_y_entry.get())
            rw = int(self.roi_w_entry.get())
            rh = int(self.roi_h_entry.get())
        except ValueError:
            messagebox.showerror("Lỗi", "Tọa độ ROI không hợp lệ!")
            return

        out_video = os.path.splitext(self.current_video_path)[0] + "_blurred.mp4"
        self.blur_video_btn.configure(state="disabled")
        self.status_label.configure(text="Đang áp dụng bộ lọc làm mờ vùng phụ đề bằng FFmpeg...")

        def worker():
            ok = media_merger.blur_subtitle_region(self.current_video_path, out_video, rx, ry, rw, rh)

            def done():
                self.blur_video_btn.configure(state="normal")
                if ok:
                    self.status_label.configure(text=f"Đã làm mờ video: {os.path.basename(out_video)}")
                    messagebox.showinfo("Thành công", f"Đã xuất video làm mờ phụ đề tại:\n{out_video}")
                else:
                    messagebox.showerror("Lỗi", "Không thể xử lý làm mờ video.")

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

