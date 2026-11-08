# -*- coding: utf-8 -*-
"""
Tab Tải Video, Preview Kéo Thả Vùng Làm Mờ & Thực Thi Pipeline
Dự án: DICH_VIDEO (100% Mã nguồn sạch, không mã độc, không DRM)

Mục đích:
- Tải video sạch không logo từ Douyin, TikTok, YouTube, Bilibili qua yt-dlp.
- Xem trước khung hình video bằng OpenCV, tua frame linh hoạt.
- Tương tác chuột 2 chiều: KÉO THẢ, CO GIÃN VÙNG LÀM MỜ (ROI) TRỰC TIẾP TRÊN MÀN HÌNH VIDEO.
  + 8 điểm neo (resize handles) ở 4 góc và 4 cạnh.
  + Thay đổi con trỏ chuột theo hướng co giãn (size_nw_se, size_ns, fleur...).
  + Tự động đồng bộ số liệu tọa độ X, Y, W, H.
- Khối điều khiển thực thi nổi bật với nút "🚀 BẮT ĐẦU THỰC THI".
  + Tùy chọn: Làm mờ phụ đề cũ, Tách Audio MP3, hoặc Chạy trọn gói.
  + Hiển thị thanh tiến trình % và thời gian thực.
  + Tự động chuyển tiếp sang Bước 2 (Dịch thuật AI).
"""

from __future__ import annotations
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import cv2
from PIL import Image, ImageTk

from ..core.config import config
from ..core.gemini_pool import gemini_pool
from ..core.media_merger import media_merger
from ..core.video_downloader import video_downloader


class VideoExtractTab(ctk.CTkFrame):
    """Giao diện Tab 1: Tải video, kéo thả co giãn vùng làm mờ và thực thi."""

    def __init__(self, master, on_extracted_audio_cb=None, on_next_step_cb=None):
        super().__init__(master)
        self.on_extracted_audio_cb = on_extracted_audio_cb
        self.on_next_step_cb = on_next_step_cb

        # Thông số video
        self.current_video_path: str = ""
        self.cap: cv2.VideoCapture | None = None
        self.total_frames: int = 0
        self.video_fps: float = 30.0
        self.video_width: int = 0
        self.video_height: int = 0

        # Tọa độ vùng làm mờ (Native video pixels)
        self.roi_x: int = 0
        self.roi_y: int = 0
        self.roi_w: int = 0
        self.roi_h: int = 0

        # Thông số hình học Canvas preview
        self._scale: float = 1.0
        self._off_x: int = 0
        self._off_y: int = 0
        self._tk_img: ImageTk.PhotoImage | None = None
        self._current_rgb_frame = None

        # Trạng thái tương tác kéo thả chuột
        self._drag_mode: str | None = None  # "move", "resize", "create"
        self._active_handle: str | None = None
        self._drag_start_x: int = 0
        self._drag_start_y: int = 0
        self._drag_start_vx: int = 0
        self._drag_start_vy: int = 0
        self._orig_roi = (0, 0, 0, 0)

        # Trạng thái tiến trình thực thi
        self._is_processing = False
        self.last_audio_file: str = ""
        self.last_blurred_video: str = ""
        self.last_srt_file: str = ""

        self._build_ui()

    def _build_ui(self):
        # =================================================================
        # 1. KHUNG TẢI VIDEO TỪ LINK
        # =================================================================
        dl_frame = ctk.CTkFrame(self)
        dl_frame.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            dl_frame,
            text="🔗 Dán Link Video (Douyin, TikTok, YouTube...):",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, padx=10, pady=8, sticky="w")

        self.url_entry = ctk.CTkEntry(
            dl_frame,
            placeholder_text="https://v.douyin.com/... hoặc https://www.youtube.com/watch?v=...",
            width=480,
        )
        self.url_entry.grid(row=0, column=1, padx=10, pady=8, sticky="ew")

        self.dl_btn = ctk.CTkButton(
            dl_frame,
            text="⬇️ Tải Video Sạch",
            command=self._download_video_threaded,
            width=135,
            fg_color="#00ADB5",
            hover_color="#007B83",
            font=ctk.CTkFont(weight="bold"),
        )
        self.dl_btn.grid(row=0, column=2, padx=10, pady=8)
        dl_frame.columnconfigure(1, weight=1)

        # =================================================================
        # 2. KHUNG CHỌN VIDEO CỤC BỘ TRÊN MÁY
        # =================================================================
        file_frame = ctk.CTkFrame(self)
        file_frame.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(
            file_frame,
            text="📁 Hoặc chọn video từ máy:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(side="left", padx=10, pady=6)

        self.video_path_label = ctk.CTkLabel(
            file_frame,
            text="Chưa có video nào được chọn (Hãy dán link ở trên hoặc bấm 'Chọn video')",
            text_color="gray",
            anchor="w",
        )
        self.video_path_label.pack(side="left", fill="x", expand=True, padx=10, pady=6)

        ctk.CTkButton(
            file_frame,
            text="Chọn video...",
            width=120,
            command=self._browse_local_video,
        ).pack(side="right", padx=10, pady=6)

        # =================================================================
        # 3. VÙNG TRUNG TÂM: MÀN HÌNH PREVIEW KÉO THẢ & BẢNG ĐIỀU KHIỂN
        # =================================================================
        main_content = ctk.CTkFrame(self, fg_color="transparent")
        main_content.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # --- CỘT TRÁI: MÀN HÌNH VIDEO PREVIEW ---
        left_preview = ctk.CTkFrame(main_content)
        left_preview.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Hướng dẫn thao tác kéo thả ngay trên màn hình
        tip_label = ctk.CTkLabel(
            left_preview,
            text="💡 Mẹo kéo thả: Nhấp và kéo vùng xanh để di chuyển | Kéo 8 điểm neo tròn ở góc/cạnh để co giãn",
            font=ctk.CTkFont(size=11),
            text_color="#00ADB5",
        )
        tip_label.pack(anchor="w", padx=10, pady=(6, 2))

        # Màn hình Canvas tương tác
        self.preview_canvas = tk.Canvas(
            left_preview,
            bg="#181818",
            highlightthickness=1,
            highlightbackground="#2A2A2A",
            cursor="crosshair",
        )
        self.preview_canvas.pack(fill="both", expand=True, padx=6, pady=4)

        # Ràng buộc các sự kiện chuột tương tác 2 chiều
        self.preview_canvas.bind("<Motion>", self._on_canvas_motion)
        self.preview_canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.preview_canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.preview_canvas.bind("<Configure>", self._on_canvas_configure)

        # Thanh trượt tua thời gian video
        slider_box = ctk.CTkFrame(left_preview, fg_color="transparent")
        slider_box.pack(fill="x", padx=10, pady=(4, 6))

        ctk.CTkLabel(slider_box, text="Tua Frame:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 6))
        self.seek_slider = ctk.CTkSlider(
            slider_box,
            from_=0,
            to=100,
            command=self._on_seek_slider,
        )
        self.seek_slider.pack(side="left", fill="x", expand=True, padx=6)
        self.seek_slider.set(0)

        self.frame_info_label = ctk.CTkLabel(slider_box, text="Frame: 0/0 (00:00)", font=ctk.CTkFont(size=11))
        self.frame_info_label.pack(side="right", padx=(6, 0))

        # --- CỘT PHẢI: BẢNG TỌA ĐỘ VÙNG ROI & KHỐI THỰC THI NỔI BẬT ---
        right_panel = ctk.CTkFrame(main_content, width=340)
        right_panel.pack(side="right", fill="y", padx=(0, 0))
        right_panel.pack_propagate(False)

        # 3.1. Thiết lập Vùng Làm Mờ (ROI)
        ctk.CTkLabel(
            right_panel,
            text="📐 Vùng Làm Mờ / Xóa Phụ Đề:",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=12, pady=(10, 4))

        # Nhập tọa độ số (tự đồng bộ 2 chiều với thao tác chuột)
        coord_grid = ctk.CTkFrame(right_panel, fg_color="transparent")
        coord_grid.pack(fill="x", padx=10, pady=2)

        self.roi_x_entry = self._create_coord_input(coord_grid, "X (Cột):", "0", 0, 0)
        self.roi_y_entry = self._create_coord_input(coord_grid, "Y (Hàng):", "0", 0, 1)
        self.roi_w_entry = self._create_coord_input(coord_grid, "W (Rộng):", "0", 1, 0)
        self.roi_h_entry = self._create_coord_input(coord_grid, "H (Cao):", "0", 1, 1)

        # Nút cài đặt nhanh vị trí thường dùng
        preset_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        preset_frame.pack(fill="x", padx=10, pady=6)

        ctk.CTkButton(
            preset_frame,
            text="15% Chân Video (Chuẩn)",
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="#393E46",
            command=lambda: self._set_preset_roi(0.05, 0.82, 0.90, 0.16),
        ).pack(fill="x", pady=2)

        preset_row2 = ctk.CTkFrame(preset_frame, fg_color="transparent")
        preset_row2.pack(fill="x", pady=2)

        ctk.CTkButton(
            preset_row2,
            text="20% Đáy",
            width=100,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#2B2E4A",
            command=lambda: self._set_preset_roi(0.03, 0.78, 0.94, 0.20),
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))

        ctk.CTkButton(
            preset_row2,
            text="15% Đầu Video",
            width=100,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#2B2E4A",
            command=lambda: self._set_preset_roi(0.05, 0.02, 0.90, 0.15),
        ).pack(side="left", fill="x", expand=True, padx=2)

        ctk.CTkButton(
            preset_row2,
            text="Toàn Màn Hình",
            width=100,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#2B2E4A",
            command=lambda: self._set_preset_roi(0.0, 0.0, 1.0, 1.0),
        ).pack(side="left", fill="x", expand=True, padx=(2, 0))

        # Phân cách
        ctk.CTkFrame(right_panel, height=2, fg_color="#333333").pack(fill="x", padx=12, pady=10)

        # =================================================================
        # 3.2. KHỐI THỰC THI CHÍNH (EXECUTION CONTROL PANEL)
        # =================================================================
        ctk.CTkLabel(
            right_panel,
            text="🚀 BẮT ĐẦU THỰC THI (PIPELINE):",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#00ADB5",
        ).pack(anchor="w", padx=12, pady=(0, 6))

        # Tùy chọn chế độ thực thi
        self.exec_mode = tk.StringVar(value="full_all")

        ctk.CTkRadioButton(
            right_panel,
            text="⚡ Trọn gói: Tạo Phụ Đề SRT + Tách Audio + Làm mờ",
            variable=self.exec_mode,
            value="full_all",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=12, pady=3)

        ctk.CTkRadioButton(
            right_panel,
            text="📝 Chỉ Trích xuất Phụ Đề (.srt) bằng AI",
            variable=self.exec_mode,
            value="srt",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=12, pady=3)

        ctk.CTkRadioButton(
            right_panel,
            text="🎬 Chỉ Làm mờ phụ đề video (Xóa hardsub)",
            variable=self.exec_mode,
            value="blur",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=12, pady=3)

        ctk.CTkRadioButton(
            right_panel,
            text="🎵 Chỉ Tách âm thanh sang MP3",
            variable=self.exec_mode,
            value="audio",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=12, pady=3)

        # Cài đặt độ mờ
        blur_opt_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        blur_opt_frame.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(blur_opt_frame, text="Mức độ mờ:", font=ctk.CTkFont(size=12)).pack(side="left")
        self.blur_intensity = ctk.CTkComboBox(
            blur_opt_frame,
            values=["Tiêu chuẩn (10:5)", "Mạnh (20:10)", "Nhẹ (5:2)"],
            width=160,
            height=28,
        )
        self.blur_intensity.set("Tiêu chuẩn (10:5)")
        self.blur_intensity.pack(side="right")

        # NÚT THỰC THI SIÊU NỔI BẬT (BIG PROMINENT EXECUTE BUTTON)
        self.execute_btn = ctk.CTkButton(
            right_panel,
            text="🚀 BẮT ĐẦU THỰC THI",
            height=46,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#00ADB5",
            hover_color="#007B83",
            command=self._start_execution_pipeline,
        )
        self.execute_btn.pack(fill="x", padx=12, pady=(12, 6))

        # Thanh tiến trình thực thi
        self.progress_bar = ctk.CTkProgressBar(right_panel, height=12)
        self.progress_bar.set(0.0)
        self.progress_bar.pack(fill="x", padx=12, pady=(4, 4))

        self.exec_status_label = ctk.CTkLabel(
            right_panel,
            text="Sẵn sàng thực thi. Chọn chế độ rồi nhấn nút phía trên.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            wraplength=310,
            justify="left",
        )
        self.exec_status_label.pack(anchor="w", padx=12, pady=(0, 6))

        # Các nút điều hướng tiếp theo sau khi chạy xong
        self.action_after_box = ctk.CTkFrame(right_panel, fg_color="transparent")
        self.action_after_box.pack(fill="x", padx=10, pady=(4, 8))

        self.open_output_btn = ctk.CTkButton(
            self.action_after_box,
            text="📂 Mở Thư Mục Kết Quả",
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color="#393E46",
            command=self._open_output_folder,
            state="disabled",
        )
        self.open_output_btn.pack(fill="x", pady=2)

        self.next_step_btn = ctk.CTkButton(
            self.action_after_box,
            text="➡️ Sang Bước 2: Dịch Thuật AI",
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2E7D32",
            hover_color="#1B5E20",
            command=self._go_to_next_step,
            state="disabled",
        )
        self.next_step_btn.pack(fill="x", pady=2)

    def _create_coord_input(self, parent, label_text: str, default_val: str, row: int, col: int) -> ctk.CTkEntry:
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=row, column=col, padx=4, pady=3, sticky="ew")
        ctk.CTkLabel(f, text=label_text, font=ctk.CTkFont(size=12)).pack(side="left")
        entry = ctk.CTkEntry(f, width=70, height=26, font=ctk.CTkFont(family="Consolas", size=11))
        entry.insert(0, default_val)
        entry.pack(side="right")
        entry.bind("<KeyRelease>", self._on_entry_changed)
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        return entry

    # =================================================================
    # QUẢN LÝ VIDEO & CANVAS PREVIEW
    # =================================================================

    def _browse_local_video(self):
        fpath = filedialog.askopenfilename(
            title="Chọn file video",
            filetypes=[("Video files", "*.mp4;*.mkv;*.avi;*.mov;*.flv;*.webm"), ("Tất cả", "*.*")],
        )
        if fpath:
            self.load_video(fpath)

    def load_video(self, video_path: str):
        """Mở video bằng OpenCV, lấy thông số và hiển thị frame đầu tiên."""
        if not os.path.isfile(video_path):
            return

        if self.cap:
            self.cap.release()

        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            messagebox.showerror("Lỗi", "Không thể mở file video này.")
            return

        self.current_video_path = video_path
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.video_fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.video_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        dur_sec = self.total_frames / self.video_fps if self.video_fps > 0 else 0
        mins = int(dur_sec // 60)
        secs = int(dur_sec % 60)

        self.video_path_label.configure(
            text=f"🎬 {os.path.basename(video_path)} ({self.video_width}x{self.video_height} | {self.video_fps:.1f} fps | {mins:02d}:{secs:02d})",
            text_color="#EEEEEE",
        )

        self.seek_slider.configure(to=max(1, self.total_frames - 1))
        self.seek_slider.set(0)

        # Đặt mặc định vùng chân video 16%
        self._set_preset_roi(0.05, 0.82, 0.90, 0.16)
        self._display_frame_at(0)
        self.exec_status_label.configure(text=f"Đã nạp video: {os.path.basename(video_path)}")

    def _display_frame_at(self, frame_idx: int):
        """Đọc và hiển thị frame video lên Canvas mà không làm mờ cứng ảnh gốc."""
        if not self.cap or not self.cap.isOpened():
            return

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return

        self._current_rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self._render_canvas_image_and_roi()

        cur_sec = frame_idx / self.video_fps if self.video_fps > 0 else 0
        cur_m, cur_s = int(cur_sec // 60), int(cur_sec % 60)
        tot_sec = self.total_frames / self.video_fps if self.video_fps > 0 else 0
        tot_m, tot_s = int(tot_sec // 60), int(tot_sec % 60)
        self.frame_info_label.configure(text=f"Frame: {frame_idx}/{self.total_frames} ({cur_m:02d}:{cur_s:02d}/{tot_m:02d}:{tot_s:02d})")

    def _render_canvas_image_and_roi(self):
        """Tính toán tỷ lệ co dãn Canvas và vẽ lại ảnh kèm các điểm neo ROI."""
        if self._current_rgb_frame is None:
            return

        c_w = max(100, self.preview_canvas.winfo_width())
        c_h = max(100, self.preview_canvas.winfo_height())

        h, w, _ = self._current_rgb_frame.shape
        self._scale = min(c_w / w, c_h / h)
        self._img_w = max(1, int(w * self._scale))
        self._img_h = max(1, int(h * self._scale))

        self._off_x = (c_w - self._img_w) // 2
        self._off_y = (c_h - self._img_h) // 2

        resized = cv2.resize(self._current_rgb_frame, (self._img_w, self._img_h), interpolation=cv2.INTER_AREA)
        pil_img = Image.fromarray(resized)
        self._tk_img = ImageTk.PhotoImage(pil_img)

        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(
            self._off_x + self._img_w // 2,
            self._off_y + self._img_h // 2,
            image=self._tk_img,
            anchor="center",
            tags="video_frame",
        )

        self._redraw_roi_elements()

    def _redraw_roi_elements(self):
        """Vẽ lại hình chữ nhật ROI, 8 điểm neo co giãn và thẻ thông tin trên Canvas."""
        self.preview_canvas.delete("roi_element")

        if self.video_width <= 0 or self.video_height <= 0 or self.roi_w <= 0 or self.roi_h <= 0:
            return

        cx1 = self._off_x + int(self.roi_x * self._scale)
        cy1 = self._off_y + int(self.roi_y * self._scale)
        cx2 = self._off_x + int((self.roi_x + self.roi_w) * self._scale)
        cy2 = self._off_y + int((self.roi_y + self.roi_h) * self._scale)

        # 1. Vùng làm mờ bóng mờ mờ (Translucent fill)
        self.preview_canvas.create_rectangle(
            cx1, cy1, cx2, cy2,
            outline="#00FF88",
            width=2,
            fill="#00ADB5",
            stipple="gray25",
            tags="roi_element",
        )

        # 2. Vẽ 8 điểm neo co giãn (Resize Handles)
        handles = self._calculate_handle_coords(cx1, cy1, cx2, cy2)
        r = 5
        for _, (hx, hy) in handles.items():
            self.preview_canvas.create_rectangle(
                hx - r, hy - r, hx + r, hy + r,
                fill="#00FF88",
                outline="#111111",
                width=1.5,
                tags="roi_element",
            )

        # 3. Huy hiệu thông số kích thước nổi phía trên hộp chọn
        pct_h = (self.roi_h / self.video_height) * 100 if self.video_height > 0 else 0
        badge_text = f"✂️ Vùng làm mờ: {self.roi_w}x{self.roi_h} (X:{self.roi_x}, Y:{self.roi_y}) | {pct_h:.0f}% video"
        badge_y = max(16, cy1 - 12)
        badge_x = (cx1 + cx2) // 2

        self.preview_canvas.create_rectangle(
            badge_x - 130, badge_y - 9, badge_x + 130, badge_y + 9,
            fill="#1B262C",
            outline="#00ADB5",
            width=1,
            tags="roi_element",
        )
        self.preview_canvas.create_text(
            badge_x, badge_y,
            text=badge_text,
            fill="#FFFFFF",
            font=("Arial", 9, "bold"),
            tags="roi_element",
        )

    def _calculate_handle_coords(self, cx1: int, cy1: int, cx2: int, cy2: int):
        """Tính tọa độ 8 điểm neo: 4 góc và 4 điểm giữa cạnh."""
        mid_x = (cx1 + cx2) // 2
        mid_y = (cy1 + cy2) // 2
        return {
            "nw": (cx1, cy1),
            "n": (mid_x, cy1),
            "ne": (cx2, cy1),
            "e": (cx2, mid_y),
            "se": (cx2, cy2),
            "s": (mid_x, cy2),
            "sw": (cx1, cy2),
            "w": (cx1, mid_y),
        }

    # =================================================================
    # TƯƠNG TÁC CHUỘT: KÉO THẢ, DI CHUYỂN & CO GIÃN 8 HƯỚNG
    # =================================================================

    def _get_handle_under_mouse(self, mx: int, my: int) -> str | None:
        """Kiểm tra chuột có nằm trên một trong 8 điểm neo co giãn không."""
        if self.roi_w <= 0 or self.roi_h <= 0:
            return None

        cx1 = self._off_x + int(self.roi_x * self._scale)
        cy1 = self._off_y + int(self.roi_y * self._scale)
        cx2 = self._off_x + int((self.roi_x + self.roi_w) * self._scale)
        cy2 = self._off_y + int((self.roi_y + self.roi_h) * self._scale)

        handles = self._calculate_handle_coords(cx1, cy1, cx2, cy2)
        for name, (hx, hy) in handles.items():
            if abs(mx - hx) <= 8 and abs(my - hy) <= 8:
                return name
        return None

    def _is_inside_box(self, mx: int, my: int) -> bool:
        """Kiểm tra chuột có nằm bên trong vùng chữ nhật ROI không."""
        cx1 = self._off_x + int(self.roi_x * self._scale)
        cy1 = self._off_y + int(self.roi_y * self._scale)
        cx2 = self._off_x + int((self.roi_x + self.roi_w) * self._scale)
        cy2 = self._off_y + int((self.roi_y + self.roi_h) * self._scale)
        return min(cx1, cx2) <= mx <= max(cx1, cx2) and min(cy1, cy2) <= my <= max(cy1, cy2)

    def _on_canvas_motion(self, event):
        """Thay đổi con trỏ chuột linh hoạt khi di chuột qua điểm neo hoặc thân hộp."""
        if self._drag_mode:
            return  # Đang kéo thả thì giữ nguyên con trỏ

        handle = self._get_handle_under_mouse(event.x, event.y)
        if handle in ["nw", "se"]:
            self.preview_canvas.config(cursor="size_nw_se")
        elif handle in ["ne", "sw"]:
            self.preview_canvas.config(cursor="size_ne_sw")
        elif handle in ["n", "s"]:
            self.preview_canvas.config(cursor="size_ns")
        elif handle in ["w", "e"]:
            self.preview_canvas.config(cursor="size_we")
        elif self._is_inside_box(event.x, event.y):
            self.preview_canvas.config(cursor="fleur")  # Con trỏ di chuyển 4 chiều
        else:
            self.preview_canvas.config(cursor="crosshair")  # Con trỏ vẽ vùng mới

    def _on_canvas_press(self, event):
        """Bắt đầu thao tác: Co giãn điểm neo, Di chuyển vùng hoặc Vẽ vùng mới."""
        if self.video_width <= 0 or self.video_height <= 0:
            return

        handle = self._get_handle_under_mouse(event.x, event.y)
        if handle:
            # Chế độ co giãn bằng điểm neo
            self._drag_mode = "resize"
            self._active_handle = handle
            self._drag_start_x = event.x
            self._drag_start_y = event.y
            self._orig_roi = (self.roi_x, self.roi_y, self.roi_w, self.roi_h)
        elif self._is_inside_box(event.x, event.y):
            # Chế độ di chuyển cả hộp
            self._drag_mode = "move"
            self._active_handle = None
            self._drag_start_x = event.x
            self._drag_start_y = event.y
            self._orig_roi = (self.roi_x, self.roi_y, self.roi_w, self.roi_h)
        else:
            # Nhấp chuột bên ngoài -> Tạo vùng chọn mới từ vị trí này
            self._drag_mode = "create"
            self._active_handle = None
            vx = max(0, min(self.video_width, int((event.x - self._off_x) / self._scale)))
            vy = max(0, min(self.video_height, int((event.y - self._off_y) / self._scale)))
            self._drag_start_vx = vx
            self._drag_start_vy = vy
            self.roi_x = vx
            self.roi_y = vy
            self.roi_w = 10
            self.roi_h = 10
            self._sync_roi_to_entries()
            self._redraw_roi_elements()

    def _on_canvas_drag(self, event):
        """Thực hiện co giãn hoặc di chuyển mượt mà theo chuyển động chuột."""
        if not self._drag_mode or self.video_width <= 0 or self.video_height <= 0:
            return

        if self._drag_mode == "move":
            dx = int((event.x - self._drag_start_x) / self._scale)
            dy = int((event.y - self._drag_start_y) / self._scale)
            ox, oy, ow, oh = self._orig_roi

            new_x = max(0, min(self.video_width - ow, ox + dx))
            new_y = max(0, min(self.video_height - oh, oy + dy))

            self.roi_x = new_x
            self.roi_y = new_y
            self._sync_roi_to_entries()
            self._redraw_roi_elements()

        elif self._drag_mode == "resize":
            ox, oy, ow, oh = self._orig_roi
            cur_vx = max(0, min(self.video_width, int((event.x - self._off_x) / self._scale)))
            cur_vy = max(0, min(self.video_height, int((event.y - self._off_y) / self._scale)))
            h_name = self._active_handle or "se"

            left = ox
            top = oy
            right = ox + ow
            bottom = oy + oh

            if "w" in h_name:
                left = min(cur_vx, right - 10)
            if "e" in h_name:
                right = max(cur_vx, left + 10)
            if "n" in h_name:
                top = min(cur_vy, bottom - 10)
            if "s" in h_name:
                bottom = max(cur_vy, top + 10)

            self.roi_x = max(0, left)
            self.roi_y = max(0, top)
            self.roi_w = min(self.video_width - self.roi_x, right - left)
            self.roi_h = min(self.video_height - self.roi_y, bottom - top)
            self._sync_roi_to_entries()
            self._redraw_roi_elements()

        elif self._drag_mode == "create":
            cur_vx = max(0, min(self.video_width, int((event.x - self._off_x) / self._scale)))
            cur_vy = max(0, min(self.video_height, int((event.y - self._off_y) / self._scale)))

            left = min(self._drag_start_vx, cur_vx)
            right = max(self._drag_start_vx, cur_vx)
            top = min(self._drag_start_vy, cur_vy)
            bottom = max(self._drag_start_vy, cur_vy)

            self.roi_x = max(0, left)
            self.roi_y = max(0, top)
            self.roi_w = max(10, min(self.video_width - self.roi_x, right - left))
            self.roi_h = max(10, min(self.video_height - self.roi_y, bottom - top))
            self._sync_roi_to_entries()
            self._redraw_roi_elements()

    def _on_canvas_release(self, _event):
        """Kết thúc thao tác kéo thả."""
        self._drag_mode = None
        self._active_handle = None
        self._sync_roi_to_entries()
        self._redraw_roi_elements()

    def _on_canvas_configure(self, _event):
        """Khi cửa sổ thay đổi kích thước, tự động vẽ lại Canvas chuẩn tỷ lệ."""
        self._render_canvas_image_and_roi()

    def _sync_roi_to_entries(self):
        """Đồng bộ giá trị từ chuột vào 4 ô nhập số tọa độ."""
        for entry, val in [
            (self.roi_x_entry, self.roi_x),
            (self.roi_y_entry, self.roi_y),
            (self.roi_w_entry, self.roi_w),
            (self.roi_h_entry, self.roi_h),
        ]:
            entry.delete(0, "end")
            entry.insert(0, str(int(val)))

    def _on_entry_changed(self, _event):
        """Khi người dùng sửa số trực tiếp bằng bàn phím, cập nhật ngay hộp Canvas."""
        try:
            self.roi_x = int(self.roi_x_entry.get().strip() or "0")
            self.roi_y = int(self.roi_y_entry.get().strip() or "0")
            self.roi_w = int(self.roi_w_entry.get().strip() or "0")
            self.roi_h = int(self.roi_h_entry.get().strip() or "0")
            self._redraw_roi_elements()
        except ValueError:
            pass

    def _set_preset_roi(self, px: float, py: float, pw: float, ph: float):
        """Thiết lập vùng ROI theo tỷ lệ phần trăm video chuẩn."""
        if self.video_width > 0 and self.video_height > 0:
            self.roi_x = int(self.video_width * px)
            self.roi_y = int(self.video_height * py)
            self.roi_w = int(self.video_width * pw)
            self.roi_h = int(self.video_height * ph)
            self._sync_roi_to_entries()
            self._redraw_roi_elements()

    def _on_seek_slider(self, val):
        frame_idx = int(val)
        self._display_frame_at(frame_idx)

    # =================================================================
    # QUY TRÌNH THỰC THI PIPELINE (EXECUTION ENGINE)
    # =================================================================

    def _start_execution_pipeline(self):
        """Bắt đầu chạy quy trình đã chọn khi người dùng bấm nút THỰC THI."""
        if not self.current_video_path or not os.path.isfile(self.current_video_path):
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn hoặc tải một video trước khi thực thi!")
            return

        mode = self.exec_mode.get()
        self.execute_btn.configure(state="disabled", text="⏳ Đang thực thi...")
        self.progress_bar.set(0.0)
        self.open_output_btn.configure(state="disabled")
        self.next_step_btn.configure(state="disabled")

        intensity_str = self.blur_intensity.get()
        intensity = "medium"
        if "Mạnh" in intensity_str:
            intensity = "heavy"
        elif "Nhẹ" in intensity_str:
            intensity = "light"

        def worker():
            base_dir = os.path.dirname(self.current_video_path)
            base_name = os.path.splitext(os.path.basename(self.current_video_path))[0]

            out_audio = os.path.join(base_dir, f"{base_name}.mp3")
            out_video = os.path.join(base_dir, f"{base_name}_blurred.mp4")
            out_srt = os.path.join(base_dir, f"{base_name}.srt")

            def prog_cb(pct, status_text):
                self.after(0, lambda: self._update_progress_ui(pct / 100.0, status_text))

            success = True
            err_msg = ""

            # BƯỚC 1: TÁCH AUDIO MP3
            if mode in ["audio", "all", "full_all", "srt"]:
                prog_cb(15.0, "Đang trích xuất audio MP3 bằng FFmpeg...")
                ok_audio = media_merger.extract_audio(self.current_video_path, out_audio)
                if ok_audio:
                    self.last_audio_file = out_audio
                else:
                    success = False
                    err_msg = "Lỗi khi trích xuất audio từ video."

            # BƯỚC 2: TỰ ĐỘNG TRÍCH XUẤT PHỤ ĐỀ SRT BẰNG AI
            if success and mode in ["srt", "full_all"]:
                prog_cb(35.0, "Đang gửi âm thanh lên Gemini AI để tự động tạo file phụ đề SRT...")
                ok_srt, srt_text, srt_path = gemini_pool.transcribe_audio_to_srt(
                    audio_path=out_audio,
                    output_srt_path=out_srt,
                    progress_callback=lambda msg: prog_cb(50.0, msg),
                )
                if ok_srt:
                    self.last_srt_file = srt_path
                else:
                    print(f"[VideoExtractTab] Cảnh báo tạo phụ đề AI: {srt_path}")
                    if mode == "srt":
                        success = False
                        err_msg = srt_path

            # BƯỚC 3: LÀM MỜ VÙNG PHỤ ĐỀ TRÊN VIDEO
            if success and mode in ["blur", "all", "full_all"]:
                prog_cb(70.0, "Đang áp dụng bộ lọc làm mờ vùng phụ đề cũ bằng FFmpeg...")
                ok_blur = media_merger.blur_subtitle_region(
                    video_path=self.current_video_path,
                    output_video_path=out_video,
                    x=self.roi_x,
                    y=self.roi_y,
                    w=self.roi_w,
                    h=self.roi_h,
                    blur_intensity=intensity,
                    progress_callback=prog_cb,
                )
                if ok_blur:
                    self.last_blurred_video = out_video
                else:
                    success = False
                    err_msg = "Lỗi khi xử lý làm mờ video bằng FFmpeg."

            def done():
                self.execute_btn.configure(state="normal", text="🚀 BẮT ĐẦU THỰC THI")
                if success:
                    self.progress_bar.set(1.0)
                    self.open_output_btn.configure(state="normal")
                    self.next_step_btn.configure(state="normal")

                    msg = "🎉 TIẾN TRÌNH THỰC THI ĐÃ HOÀN TẤT THÀNH CÔNG!\n\n"
                    if self.last_srt_file and os.path.isfile(self.last_srt_file):
                        msg += f"📝 File Phụ đề SRT: {os.path.basename(self.last_srt_file)}\n"
                    if self.last_audio_file and os.path.isfile(self.last_audio_file):
                        msg += f"🎵 File Audio: {os.path.basename(self.last_audio_file)}\n"
                    if self.last_blurred_video and os.path.isfile(self.last_blurred_video):
                        msg += f"🎬 Video đã làm mờ: {os.path.basename(self.last_blurred_video)}\n"
                    msg += "\nBạn có muốn chuyển sang Bước 2 (Dịch Thuật AI) để xem bảng phụ đề và dịch ngay bây giờ không?"

                    self.exec_status_label.configure(text="✅ Hoàn tất thành công!", text_color="#4ECCA3")
                    if messagebox.askyesno("Thành công", msg):
                        self._go_to_next_step()
                else:
                    self.exec_status_label.configure(text=f"❌ Thất bại: {err_msg}", text_color="#E84545")
                    messagebox.showerror("Thất bại", f"Không thể hoàn thành thực thi:\n\n{err_msg}")

            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _update_progress_ui(self, fraction: float, text: str):
        self.progress_bar.set(fraction)
        self.exec_status_label.configure(text=text, text_color="#EEEEEE")

    def _open_output_folder(self):
        target = self.last_blurred_video or self.last_audio_file or self.last_srt_file or self.current_video_path
        if target and os.path.exists(target):
            folder = os.path.dirname(os.path.abspath(target))
            os.system(f'explorer "{folder}"')
        else:
            messagebox.showinfo("Thông báo", "Chưa có file kết quả để mở.")

    def _go_to_next_step(self):
        if self.on_extracted_audio_cb:
            self.on_extracted_audio_cb(self.last_audio_file, self.last_srt_file)
        elif self.on_next_step_cb:
            self.on_next_step_cb()

    def _download_video_threaded(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập liên kết video!")
            return

        self.dl_btn.configure(state="disabled")
        self.exec_status_label.configure(text="Đang kết nối và tải video bằng yt-dlp...", text_color="yellow")

        def worker():
            def progress_cb(data):
                percent = data.get("percent", 0.0)
                self.after(0, lambda: self.exec_status_label.configure(text=f"Đang tải video: {percent:.1f}%"))

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
