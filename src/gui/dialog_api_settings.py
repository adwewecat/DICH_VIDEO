# -*- coding: utf-8 -*-
"""
Hộp thoại Cài đặt API Google Gemini (API Settings Dialog)
Dự án: DICH_VIDEO (100% Mã nguồn sạch, không mã độc, không DRM)

Mục đích:
- Cho phép người dùng nhập 1 hoặc nhiều API Key của Google Gemini (lấy miễn phí tại AI Studio).
- Hỗ trợ nút Test kết nối ngay tại giao diện.
- Lựa chọn mô hình Gemini mặc định (gemini-2.5-flash, gemini-2.0-flash, gemini-1.5-pro,...).
- Hoàn toàn an toàn: API Key lưu trữ cục bộ trên máy người dùng, KHÔNG gửi đi bất kỳ server bên thứ 3 nào.
"""

from __future__ import annotations
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from ..core.config import config
from ..core.gemini_pool import gemini_pool


class ApiSettingsDialog(ctk.CTkToplevel):
    """Hộp thoại quản lý danh sách API Key và cấu hình Google Gemini."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Cài đặt Google Gemini API Keys")
        self.geometry("620x520")
        self.resizable(False, False)

        # Đặt trên cùng và khóa focus
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_current_settings()

    def _build_ui(self):
        # Tiêu đề
        title_label = ctk.CTkLabel(
            self,
            text="🔑 Cấu hình Google Gemini AI (Miễn phí & Không giới hạn)",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        title_label.pack(pady=(16, 8))

        guide_label = ctk.CTkLabel(
            self,
            text="Nhập mỗi API Key trên một dòng. Hệ thống sẽ tự động xoay vòng (Rotate Keys)\n"
                 "khi gặp giới hạn Rate Limit (429) để quá trình dịch không bị gián đoạn.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        guide_label.pack(pady=(0, 12))

        # Khung nhập danh sách Keys
        key_frame = ctk.CTkFrame(self)
        key_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        ctk.CTkLabel(key_frame, text="Danh sách API Keys (Lấy tại aistudio.google.com):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 4))

        self.keys_textbox = ctk.CTkTextbox(key_frame, height=160, font=ctk.CTkFont(family="Consolas", size=12))
        self.keys_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Lựa chọn mô hình Gemini
        model_frame = ctk.CTkFrame(self)
        model_frame.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(model_frame, text="Mô hình AI:").pack(side="left", padx=10, pady=10)
        self.model_combo = ctk.CTkComboBox(
            model_frame,
            values=[
                "gemini-3.8-flash",
                "gemini-3.0-flash",
                "gemini-2.5-flash",
                "gemini-2.5-pro",
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
                "gemini-2.0-flash-thinking-exp",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
            ],
            width=230,
        )
        self.model_combo.pack(side="left", padx=5, pady=10)

        # Nút lấy danh sách models live từ Google API
        self.fetch_models_btn = ctk.CTkButton(
            model_frame,
            text="🔄 Quét Models",
            width=95,
            command=self._fetch_models_threaded,
            fg_color="#393E46",
            hover_color="#222831",
        )
        self.fetch_models_btn.pack(side="left", padx=4, pady=10)

        # Nút kiểm tra kết nối
        self.test_btn = ctk.CTkButton(
            model_frame,
            text="Kiểm tra kết nối",
            command=self._test_connection_threaded,
            fg_color="#2b7a78",
            hover_color="#17252a",
        )
        self.test_btn.pack(side="right", padx=10, pady=10)

        # Trạng thái test
        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12))
        self.status_label.pack(pady=(0, 8))

        # Nút Lưu và Đóng
        btn_box = ctk.CTkFrame(self, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(0, 16))

        save_btn = ctk.CTkButton(btn_box, text="Lưu Cấu Hình", command=self._save_settings, width=140)
        save_btn.pack(side="right", padx=(10, 0))

        cancel_btn = ctk.CTkButton(btn_box, text="Đóng", command=self.destroy, fg_color="gray", width=100)
        cancel_btn.pack(side="right")

    def _load_current_settings(self):
        saved_keys = config.get_gemini_keys()
        self.keys_textbox.delete("1.0", "end")
        if saved_keys:
            self.keys_textbox.insert("1.0", "\n".join(saved_keys))

        saved_model = config.get("gemini_model", "gemini-2.5-flash")
        self.model_combo.set(saved_model)

    def _fetch_models_threaded(self):
        """Truy vấn trực tiếp danh sách mô hình từ Google API bằng Key đầu tiên."""
        keys_text = self.keys_textbox.get("1.0", "end").strip()
        keys = [k.strip() for k in keys_text.split("\n") if k.strip()]
        if not keys:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập API Key để quét danh sách mô hình từ Google.")
            return

        self.fetch_models_btn.configure(state="disabled")
        self.status_label.configure(text="Đang quét danh sách mô hình từ Google API...", text_color="yellow")

        def worker():
            models = gemini_pool.fetch_available_models(keys[0])

            def update_ui():
                self.fetch_models_btn.configure(state="normal")
                if models:
                    self.model_combo.configure(values=models)
                    self.status_label.configure(text=f"✅ Đã tìm thấy {len(models)} mô hình từ Google API!", text_color="#4ECCA3")
                    messagebox.showinfo("Thành công", f"Đã nạp thành công {len(models)} mô hình khả dụng từ tài khoản Google của bạn!")
                else:
                    self.status_label.configure(text="⚠️ Không lấy được danh sách (sử dụng danh sách mặc định).", text_color="orange")

            self.after(0, update_ui)

        threading.Thread(target=worker, daemon=True).start()

    def _test_connection_threaded(self):
        """Kiểm tra kết nối trên luồng phụ để không bị đơ giao diện."""
        keys_text = self.keys_textbox.get("1.0", "end").strip()
        keys = [k.strip() for k in keys_text.split("\n") if k.strip()]
        if not keys:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập ít nhất một API Key để kiểm tra.")
            return

        self.test_btn.configure(state="disabled")
        self.status_label.configure(text="Đang kiểm tra kết nối tới Google Gemini...", text_color="yellow")

        def worker():
            first_key = keys[0]
            gemini_pool.model_name = self.model_combo.get().strip()
            success, msg = gemini_pool.test_key(first_key)

            def update_ui():
                self.test_btn.configure(state="normal")
                if success:
                    self.status_label.configure(text=f"✅ {msg}", text_color="#4ECCA3")
                    messagebox.showinfo("Thành công", f"Kết nối Gemini API thành công!\n\nModel: {gemini_pool.model_name}")
                else:
                    self.status_label.configure(text="❌ Kết nối thất bại!", text_color="#E84545")
                    messagebox.showerror("Lỗi kết nối", f"Không thể kết nối tới Gemini API:\n\n{msg}")

            self.after(0, update_ui)

        threading.Thread(target=worker, daemon=True).start()

    def _save_settings(self):
        keys_text = self.keys_textbox.get("1.0", "end").strip()
        keys = [k.strip() for k in keys_text.split("\n") if k.strip()]
        selected_model = self.model_combo.get().strip()

        config.set_gemini_keys(keys)
        config.set("gemini_model", selected_model)
        gemini_pool.set_keys(keys)
        gemini_pool.model_name = selected_model

        messagebox.showinfo("Đã lưu", f"Đã lưu thành công {len(keys)} API Key(s) và mô hình {selected_model}!")
        self.destroy()

