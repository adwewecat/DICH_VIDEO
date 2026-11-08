# -*- coding: utf-8 -*-
"""
Điểm Khởi Chạy Ứng Dụng (Main Entry Point)
Dự án: DICH_VIDEO (100% Mã nguồn sạch, không mã độc, không DRM)

Cách sử dụng:
    python main.py
"""

from __future__ import annotations
import os
import sys
from pathlib import Path

# Đảm bảo thư mục gốc dự án luôn nằm trong sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def main():
    """Khởi động ứng dụng giao diện người dùng DICH_VIDEO."""
    try:
        from src.gui.main_window import MainWindow

        app = MainWindow()
        app.mainloop()

    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        print(f"[Fatal Error] Lỗi khởi động ứng dụng:\n{err_msg}", file=sys.stderr)

        # Thử hiển thị hộp thoại lỗi nếu Tkinter khả dụng
        try:
            import tkinter.messagebox as mb
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            mb.showerror("Lỗi Khởi Động", f"Không thể khởi động ứng dụng:\n\n{e}\n\nVui lòng kiểm tra requirements.txt!")
            root.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    main()
