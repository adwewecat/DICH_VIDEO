# -*- coding: utf-8 -*-
"""
Cửa Sổ Chính Của Ứng Dụng (Main Window)
Dự án: DICH_VIDEO (100% Mã nguồn sạch, không mã độc, không DRM)

Mục đích:
- Điều phối giao diện tập trung với Sidebar điều hướng hiện đại.
- Kết nối thông suốt dữ liệu giữa 4 Tab chức năng:
    + Tab 1 tách audio -> tự động gửi sang Tab 2 làm audio ngữ cảnh.
    + Tab 2 dịch xong -> tự động chuyển tiếp sang Tab 3 để lồng tiếng.
    + Tab 4 hỗ trợ chỉnh sửa, chuyển đổi định dạng và tối ưu phụ đề.
- Tích hợp nút Cài đặt Gemini API Key trực quan.
"""

from __future__ import annotations
import tkinter as tk
import customtkinter as ctk

from ..core.config import config
from .dialog_api_settings import ApiSettingsDialog
from .tab_dubbing import DubbingTab
from .tab_text_conversion import TextConversionTab
from .tab_translation import TranslationTab
from .tab_video_extract import VideoExtractTab


class MainWindow(ctk.CTk):
    """Cửa sổ chính của ứng dụng DICH_VIDEO."""

    def __init__(self):
        super().__init__()

        # Thiết lập chủ đề giao diện
        ctk.set_appearance_mode(config.get("appearance_mode", "dark"))
        ctk.set_default_color_theme(config.get("color_theme", "blue"))

        self.title("DICH_VIDEO - Hệ Thống Dịch Video & Lồng Tiếng AI (Clean Edition)")
        self.geometry("1180x760")
        self.minsize(980, 640)

        self._build_ui()

    def _build_ui(self):
        # 1. Sidebar bên trái (Navigation Bar)
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.pack(side="left", fill="y", padx=0, pady=0)

        # Logo & Tên ứng dụng
        app_title = ctk.CTkLabel(
            self.sidebar_frame,
            text="🎬 DICH_VIDEO",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        app_title.pack(padx=20, pady=(24, 4))

        app_sub = ctk.CTkLabel(
            self.sidebar_frame,
            text="AI Subtitle & Dubbing\n100% Mã Nguồn Sạch",
            font=ctk.CTkFont(size=11),
            text_color="#00ADB5",
        )
        app_sub.pack(padx=20, pady=(0, 24))

        # Các nút chuyển Tab trên Sidebar
        self.nav_buttons = {}
        tabs = [
            ("tab1", "1️⃣ Bước 1: Trích Xuất Video", self._show_tab1),
            ("tab2", "2️⃣ Bước 2: Dịch Thuật AI", self._show_tab2),
            ("tab3", "3️⃣ Bước 3: Lồng Tiếng AI", self._show_tab3),
            ("tab4", "4️⃣ Bước 4: Xử Lý Phụ Đề", self._show_tab4),
        ]

        for tab_id, tab_label, tab_cmd in tabs:
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=tab_label,
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
                height=42,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                command=tab_cmd,
            )
            btn.pack(fill="x", padx=10, pady=3)
            self.nav_buttons[tab_id] = btn

        # Khung cài đặt phía đáy Sidebar
        bottom_nav = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        bottom_nav.pack(side="bottom", fill="x", padx=12, pady=16)

        api_btn = ctk.CTkButton(
            bottom_nav,
            text="🔑 Cài Đặt Gemini API",
            command=self._open_api_settings,
            fg_color="#2b7a78",
            hover_color="#17252a",
            height=36,
        )
        api_btn.pack(fill="x", pady=(0, 8))

        # Đổi giao diện Sáng / Tối
        self.theme_switch = ctk.CTkSwitch(
            bottom_nav,
            text="Chế độ Tối (Dark)",
            command=self._toggle_theme,
        )
        if config.get("appearance_mode", "dark") == "dark":
            self.theme_switch.select()
        self.theme_switch.pack(pady=4)

        # 2. Vùng chứa nội dung chính (Main Container)
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.pack(side="right", fill="both", expand=True)

        # 2.1. THANH QUY TRÌNH TỪNG BƯỚC NỔI BẬT PHÍA TRÊN (TOP STEP WIZARD BAR)
        self.top_wizard_frame = ctk.CTkFrame(self.main_container, height=44, corner_radius=0, fg_color=("#E5E5E5", "#1E1E1E"))
        self.top_wizard_frame.pack(fill="x", padx=0, pady=0)

        self.step_buttons = {}
        wizard_steps = [
            ("tab1", "🎬 Bước 1: Trích Xuất & Làm Mờ", self._show_tab1),
            ("tab2", "🌐 Bước 2: Dịch Thuật AI", self._show_tab2),
            ("tab3", "🎙️ Bước 3: Lồng Tiếng AI", self._show_tab3),
            ("tab4", "📄 Bước 4: Xử Lý Phụ Đề", self._show_tab4),
        ]

        for s_id, s_title, s_cmd in wizard_steps:
            s_btn = ctk.CTkButton(
                self.top_wizard_frame,
                text=s_title,
                command=s_cmd,
                font=ctk.CTkFont(size=12, weight="bold"),
                height=34,
                corner_radius=6,
                fg_color="transparent",
                text_color=("gray20", "gray85"),
                hover_color=("gray75", "gray30"),
            )
            s_btn.pack(side="left", padx=6, pady=5)
            self.step_buttons[s_id] = s_btn

        # Vùng chứa view các tab (Tab Content Frame)
        self.tab_content_area = ctk.CTkFrame(self.main_container, corner_radius=0, fg_color="transparent")
        self.tab_content_area.pack(fill="both", expand=True)

        # Khởi tạo các Tab
        self.tab1_view = VideoExtractTab(
            self.tab_content_area,
            on_extracted_audio_cb=self._on_audio_extracted,
            on_next_step_cb=self._show_tab2,
        )
        self.tab2_view = TranslationTab(
            self.tab_content_area,
            on_send_to_dubbing_cb=self._on_subtitles_translated,
        )
        self.tab3_view = DubbingTab(self.tab_content_area)
        self.tab4_view = TextConversionTab(self.tab_content_area)

        # Mặc định mở Tab 2 (Dịch thuật) hoặc Tab 1
        self._show_tab1()

    # =================================================================
    # ĐIỀU HƯỚNG TAB
    # =================================================================

    def _hide_all_tabs(self):
        for tab in [self.tab1_view, self.tab2_view, self.tab3_view, self.tab4_view]:
            tab.pack_forget()
        for btn in self.nav_buttons.values():
            btn.configure(fg_color="transparent")
        for btn in self.step_buttons.values():
            btn.configure(fg_color="transparent", text_color=("gray20", "gray85"))

    def _highlight_tab(self, tab_key: str):
        self.nav_buttons[tab_key].configure(fg_color=("gray75", "gray25"))
        if tab_key in self.step_buttons:
            self.step_buttons[tab_key].configure(fg_color="#00ADB5", text_color="#FFFFFF")

    def _show_tab1(self):
        self._hide_all_tabs()
        self._highlight_tab("tab1")
        self.tab1_view.pack(fill="both", expand=True)

    def _show_tab2(self):
        self._hide_all_tabs()
        self._highlight_tab("tab2")
        self.tab2_view.pack(fill="both", expand=True)

    def _show_tab3(self):
        self._hide_all_tabs()
        self._highlight_tab("tab3")
        self.tab3_view.pack(fill="both", expand=True)

    def _show_tab4(self):
        self._hide_all_tabs()
        self._highlight_tab("tab4")
        self.tab4_view.pack(fill="both", expand=True)

    # =================================================================
    # LIÊN THÔNG DỮ LIỆU GIỮA CÁC TAB (SMOOTH WORKFLOW)
    # =================================================================

    def _on_audio_extracted(self, audio_path: str):
        """Khi Tab 1 trích xuất audio xong, tự động gán sang Tab 2 làm audio ngữ cảnh."""
        self.tab2_view.audio_path_entry.delete(0, "end")
        self.tab2_view.audio_path_entry.insert(0, audio_path)
        self._show_tab2()

    def _on_subtitles_translated(self, entries):
        """Khi Tab 2 dịch xong, tự động nạp phụ đề đã dịch sang Tab 3 và chuyển tab."""
        self.tab3_view.load_subtitles(entries)
        # Nếu Tab 1 đã nạp video, tự động gán video sang Tab 3 để ghép
        if self.tab1_view.current_video_path:
            self.tab3_view.video_entry.delete(0, "end")
            self.tab3_view.video_entry.insert(0, self.tab1_view.current_video_path)
        self._show_tab3()

    def _open_api_settings(self):
        ApiSettingsDialog(self)

    def _toggle_theme(self):
        if self.theme_switch.get():
            ctk.set_appearance_mode("dark")
            config.set("appearance_mode", "dark")
        else:
            ctk.set_appearance_mode("light")
            config.set("appearance_mode", "light")

