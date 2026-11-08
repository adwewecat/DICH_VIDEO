# -*- coding: utf-8 -*-
"""
Module Gemini Translation Pool (Quản lý Luân phiên & Gọi Google Gemini API)
Dự án: DICH_VIDEO (100% Mã nguồn sạch, không mã độc, không DRM)

Mục đích:
- Gọi trực tiếp Google Gemini API qua thư viện chính thức `google-genai` (SDK 2026).
- Quản lý Pool nhiều API Key: tự động chuyển sang Key tiếp theo (Key Rotation) khi gặp lỗi Rate Limit (HTTP 429) hoặc hết hạn ngạch (Quota Exceeded).
- Hỗ trợ cơ chế dịch 2 lượt (Two-Pass Translation with Audio Context):
    + Lượt 1: Tải audio lên File API để Gemini "nghe" toàn bộ ngữ cảnh, phân biệt cảm xúc và xưng hô.
    + Lượt 2: Dịch phụ đề SRT kèm theo ngữ cảnh từ Lượt 1.
- Dịch song song hoặc dịch từng đoạn phụ đề với prompt tối ưu cho văn phong lồng tiếng Việt Nam.
"""

from __future__ import annotations
import json
import os
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

from .config import config
from .subtitle_parser import SubtitleEntry


# =====================================================================
# SYSTEM PROMPT CHUYÊN DỤNG CHO DỊCH PHỤ ĐỀ VIDEO & LỒNG TIẾNG
# =====================================================================

DEFAULT_SYSTEM_PROMPT = """Bạn là một dịch giả và biên kịch lồng tiếng phim chuyên nghiệp.
Nhiệm vụ của bạn là dịch danh sách phụ đề video được cung cấp sang TIẾNG VIỆT tự nhiên, sống động, chuẩn xác ngữ cảnh và phù hợp với văn phong nói đời thường.

QUY TẮC BẮT BUỘC:
1. Giữ nguyên định dạng đánh số từng dòng tương ứng: "1. Câu dịch 1", "2. Câu dịch 2",... Không được bỏ sót, gộp hay tự ý tách dòng.
2. Xưng hô tự nhiên, linh hoạt theo mối quan hệ của nhân vật (anh - em, mày - tao, tôi - bạn, sếp - em, bố - con,...).
3. Tuyệt đối không dịch kiểu máy móc từ-nối-từ (word-by-word) kiểu "Google Dịch". Hãy diễn đạt mượt mà theo khẩu ngữ tiếng Việt hiện đại.
4. Đối với các thuật ngữ, tên riêng, tiếng lóng, thành ngữ: dịch nghĩa thoát ý hoặc giữ nguyên nếu tên riêng quốc tế.
5. Độ dài câu dịch phải tương đương với câu gốc để khi lồng tiếng bằng giọng đọc AI có thể khớp khẩu hình và thời lượng video.
6. CHỈ trả về danh sách các câu đã dịch theo định dạng đánh số, không thêm bất kỳ lời chào hỏi, mở đầu hay giải thích nào khác.
"""

AUDIO_CONTEXT_PROMPT = """Hãy nghe toàn bộ đoạn âm thanh của video này và tóm tắt ngắn gọn:
1. Thể loại nội dung (phim ảnh, hài kịch, phóng sự tài liệu, tin tức, vlog, game,...).
2. Danh sách các nhân vật tham gia nói và mối quan hệ giữa họ để xác định đại từ xưng hô phù hợp nhất trong tiếng Việt.
3. Tông giọng và cảm xúc chủ đạo (vui vẻ, gay gắt, xúc động, nghiêm túc,...).
4. Các thuật ngữ hoặc tên riêng đặc biệt xuất hiện trong video.
Bản tóm tắt này sẽ được dùng làm bộ nhớ ngữ cảnh để dịch phụ đề chuẩn xác nhất."""


class GeminiTranslationPool:
    """Quản lý danh sách API Key và thực hiện các yêu cầu dịch thuật bằng Google Gemini."""

    def __init__(self, api_keys: Optional[List[str]] = None, model_name: str = "gemini-2.5-flash"):
        self.lock = threading.Lock()
        self.api_keys: List[str] = api_keys if api_keys is not None else config.get_gemini_keys()
        self.current_key_index: int = 0
        self.model_name: str = model_name or config.get("gemini_model", "gemini-2.5-flash")
        self.clients_cache: Dict[str, Any] = {}

    def set_keys(self, keys: List[str]) -> None:
        """Cập nhật danh sách API Keys trong pool."""
        with self.lock:
            self.api_keys = [k.strip() for k in keys if k.strip()]
            self.current_key_index = 0
            self.clients_cache.clear()

    def get_current_key(self) -> Optional[str]:
        """Lấy API Key đang được chọn hiện tại."""
        with self.lock:
            if not self.api_keys:
                return None
            return self.api_keys[self.current_key_index % len(self.api_keys)]

    def rotate_key(self) -> Optional[str]:
        """Chuyển sang API Key tiếp theo trong pool (khi key hiện tại bị limit)."""
        with self.lock:
            if not self.api_keys:
                return None
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            next_key = self.api_keys[self.current_key_index]
            print(f"[GeminiPool] Đã xoay vòng sang API Key thứ {self.current_key_index + 1}/{len(self.api_keys)}")
            return next_key

    def _get_client_for_key(self, api_key: str) -> Any:
        """Tạo hoặc tái sử dụng client Google GenAI cho một key cụ thể."""
        if genai is None:
            raise RuntimeError("Thư viện 'google-genai' chưa được cài đặt. Hãy chạy: pip install google-genai")

        if api_key not in self.clients_cache:
            self.clients_cache[api_key] = genai.Client(api_key=api_key)
        return self.clients_cache[api_key]

    # Danh sách các mô hình ổn định cao dự phòng khi mô hình người dùng chọn bị lỗi (404/503)
    STABLE_FALLBACK_MODELS = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-flash-lite-latest",
        "gemini-3.8-flash",
    ]

    def test_key(self, api_key: str, model_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Kiểm tra tính hợp lệ của một API Key đơn lẻ.
        Tự động fallback thông minh nếu mô hình đã bị Google khai tử (404) hoặc máy chủ quá tải (503).
        """
        if not api_key:
            return False, "API Key rỗng."
        target_model = model_name or self.model_name
        try:
            client = self._get_client_for_key(api_key)
            response = client.models.generate_content(
                model=target_model,
                contents="Xin chào, hãy trả lời 'OK' để kiểm tra kết nối.",
            )
            if response and response.text:
                return True, f"Kết nối thành công tới mô hình '{target_model}'! Phản hồi: {response.text.strip()}"
            return False, f"Không nhận được phản hồi từ mô hình {target_model}."
        except Exception as e:
            err_str = str(e)
            # Nếu gặp 404 (model đã bị Google khai tử) hoặc 503 (server Google quá tải), tự động thử fallback sang model ổn định
            if "404" in err_str or "503" in err_str or "unavailable" in err_str.lower() or "not found" in err_str.lower():
                print(f"[GeminiPool] Mô hình '{target_model}' gặp lỗi ({err_str[:60]}...). Đang tự động kiểm tra mô hình ổn định...")
                for fallback in self.STABLE_FALLBACK_MODELS:
                    if fallback == target_model:
                        continue
                    try:
                        fb_resp = client.models.generate_content(
                            model=fallback,
                            contents="Xin chào, kiểm tra kết nối.",
                        )
                        if fb_resp and fb_resp.text:
                            # Cập nhật lại model_name sang fallback ổn định
                            self.model_name = fallback
                            return True, (
                                f"Key hoàn toàn hợp lệ! (Lưu ý: Mô hình '{target_model}' tạm thời quá tải hoặc đã cũ (404/503), "
                                f"hệ thống đã tự động chuyển sang mô hình ổn định nhất: '{fallback}')"
                            )
                    except Exception:
                        continue
            return False, f"Lỗi kết nối ({target_model}): {err_str}"

    def test_all_keys(self) -> Dict[str, Tuple[bool, str]]:
        """Kiểm tra toàn bộ danh sách API Keys trong pool."""
        results = {}
        for key in self.api_keys:
            masked = key[:6] + "..." + key[-4:] if len(key) > 10 else key
            success, msg = self.test_key(key)
            results[masked] = (success, msg)
        return results

    def fetch_available_models(self, api_key: Optional[str] = None) -> List[str]:
        """
        Truy vấn trực tiếp danh sách các mô hình Gemini khả dụng từ Google API.
        Giúp người dùng cập nhật ngay lập tức các mô hình mới nhất (Gemini 3.8 Flash, 3.0 Flash, 2.5 Flash...).
        """
        key = api_key or self.get_current_key()
        if not key:
            return []
        try:
            client = self._get_client_for_key(key)
            models = client.models.list()
            model_names = []
            for m in models:
                name = getattr(m, "name", "") or ""
                if name.startswith("models/"):
                    name = name[len("models/"):]
                if any(x in name.lower() for x in ["gemini", "flash", "pro", "gemma"]):
                    model_names.append(name)
            if model_names:
                return sorted(list(set(model_names)), reverse=True)
        except Exception as e:
            print(f"[GeminiPool] Lỗi khi truy vấn danh sách models từ API: {e}")
        return []

    def translate_chunk(
        self,
        texts: List[str],
        context_memory: str = "",
        system_instruction: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.3,
        max_retries: int = 5,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> List[str]:
        """
        Dịch một danh sách các chuỗi văn bản (tương ứng từng câu phụ đề).
        Tự động định dạng số thứ tự:
          1. Câu 1
          2. Câu 2
        và phân tích kết quả trả về để ghép đúng từng câu.
        """
        if not texts:
            return []

        if not self.api_keys:
            raise RuntimeError("Chưa cấu hình Google Gemini API Key! Hãy vào phần Cài đặt API để nhập key.")

        # Xây dựng nội dung gửi lên
        prompt_lines = [f"{i + 1}. {t.replace(chr(10), ' ')}" for i, t in enumerate(texts)]
        input_payload = "\n".join(prompt_lines)

        user_content = ""
        if context_memory.strip():
            user_content += f"[BỘ NHỚ NGỮ CẢNH CỦA VIDEO]:\n{context_memory.strip()}\n\n"
        user_content += f"[DANH SÁCH CÂU CẦN DỊCH]:\n{input_payload}"

        last_error = None
        for attempt in range(max_retries):
            current_key = self.get_current_key()
            if not current_key:
                raise RuntimeError("Không có API Key nào khả dụng.")

            if progress_callback:
                progress_callback(f"Đang gửi {len(texts)} câu lên Gemini (Thử lần {attempt + 1})...")

            try:
                client = self._get_client_for_key(current_key)
                
                # Cấu hình config cho mô hình
                config_params = {
                    "temperature": temperature,
                    "system_instruction": system_instruction,
                }
                
                # Thử gọi với mô hình hiện tại; nếu gặp lỗi 404/503 thì tự động fallback sang mô hình khả dụng
                response = None
                models_to_try = [self.model_name] + [m for m in self.STABLE_FALLBACK_MODELS if m != self.model_name]
                for candidate in models_to_try:
                    try:
                        response = client.models.generate_content(
                            model=candidate,
                            contents=user_content,
                            config=config_params,
                        )
                        if response and response.text:
                            if candidate != self.model_name:
                                print(f"[GeminiPool] Đã tự động đổi sang mô hình {candidate} do mô hình trước không phản hồi.")
                                self.model_name = candidate
                            break
                    except Exception as mod_err:
                        m_err_str = str(mod_err)
                        if "404" in m_err_str or "503" in m_err_str or "unavailable" in m_err_str.lower():
                            print(f"[GeminiPool] Model {candidate} lỗi ({m_err_str[:40]}...), thử model tiếp theo...")
                            continue
                        raise mod_err

                if response and response.text:
                    translated_map = self._parse_numbered_response(response.text, len(texts))
                    # Ghép lại danh sách kết quả theo đúng thứ tự ban đầu
                    results = []
                    for i in range(len(texts)):
                        idx = i + 1
                        # Nếu câu dịch có thì lấy, nếu không fallback về câu gốc
                        results.append(translated_map.get(idx, texts[i]))
                    return results

            except Exception as e:
                err_str = str(e)
                last_error = e
                print(f"[GeminiPool] Lỗi khi gọi Gemini với Key hiện tại: {err_str}")

                # Nếu lỗi 429 (Rate limit) hoặc Quota -> Xoay vòng key
                if "429" in err_str or "quota" in err_str.lower() or "resource_exhausted" in err_str.lower():
                    if progress_callback:
                        progress_callback("Gặp giới hạn tốc độ (Rate Limit), đang đổi sang API Key tiếp theo...")
                    self.rotate_key()
                    time.sleep(1.5)
                else:
                    # Lỗi mạng khác -> Đợi và thử lại
                    time.sleep(2.0 * (attempt + 1))

        raise RuntimeError(f"Không thể dịch sau {max_retries} lần thử. Lỗi cuối cùng: {last_error}")

    def _parse_numbered_response(self, text: str, expected_count: int) -> Dict[int, str]:
        """Phân tích văn bản phản hồi dạng đánh số '1. Câu dịch' thành dict {1: 'Câu dịch'}."""
        result = {}
        lines = text.strip().split("\n")
        line_regex = re.compile(r"^(\d+)[\.\:\-\)]\s*(.*)$")

        current_idx = None
        current_lines = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            m = line_regex.match(line_str)
            if m:
                # Lưu câu trước đó nếu có
                if current_idx is not None and current_lines:
                    result[current_idx] = " ".join(current_lines).strip()
                current_idx = int(m.group(1))
                current_lines = [m.group(2).strip()]
            else:
                if current_idx is not None:
                    current_lines.append(line_str)

        # Lưu câu cuối cùng
        if current_idx is not None and current_lines:
            result[current_idx] = " ".join(current_lines).strip()

        return result

    def analyze_audio_context(self, audio_path: str) -> str:
        """
        Lượt 1 (Pass 1): Tải file âm thanh MP3 lên Gemini File API để phân tích ngữ cảnh,
        xác định cảm xúc nhân vật và phong cách xưng hô.
        """
        if not os.path.isfile(audio_path):
            return ""

        current_key = self.get_current_key()
        if not current_key:
            return ""

        try:
            client = self._get_client_for_key(current_key)
            print(f"[GeminiPool] Đang tải audio '{audio_path}' lên Gemini File API...")
            
            # Tải file lên Gemini
            uploaded_file = client.files.upload(file=audio_path)
            
            # Đợi file ở trạng thái sẵn sàng (ACTIVE)
            for _ in range(30):
                file_info = client.files.get(name=uploaded_file.name)
                if file_info.state.name == "ACTIVE":
                    break
                time.sleep(1.0)

            # Gọi mô hình phân tích audio
            response = client.models.generate_content(
                model=self.model_name,
                contents=[uploaded_file, AUDIO_CONTEXT_PROMPT],
            )

            # Xóa file trên server sau khi xử lý xong
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass

            if response and response.text:
                print(f"[GeminiPool] Đã trích xuất ngữ cảnh audio thành công ({len(response.text)} ký tự)")
                return response.text.strip()

        except Exception as e:
            print(f"[GeminiPool] Cảnh báo: Không thể phân tích audio qua Gemini File API ({e})")

        return ""


# Singleton instance dùng chung
gemini_pool = GeminiTranslationPool()

