# 🎮 Game Audio Translator

Ứng dụng desktop dịch âm thanh game sang tiếng Việt theo thời gian thực.

Ứng dụng bắt âm thanh từ game đang chạy (WASAPI loopback trên Windows), dùng [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) để nhận dạng giọng nói, sau đó dùng [Gemini API](https://aistudio.google.com) để dịch sang tiếng Việt và hiển thị trên cửa sổ nhỏ luôn nổi trên màn hình.

---

## Yêu cầu hệ thống

| | Tối thiểu |
|---|---|
| **Python** | 3.10+ |
| **OS** | Windows 10/11 (để dùng WASAPI loopback) |
| **RAM** | 2 GB trở lên (model `base` dùng ~150 MB) |

> **macOS / Linux:** Ứng dụng vẫn chạy được nhưng chỉ bắt được âm thanh từ micro, không bắt được âm thanh hệ thống. Phù hợp để phát triển và kiểm thử.

---

## Cài đặt

### 1. Clone hoặc tải source code

```bash
git clone <repo-url>
cd game-audio-translator
```

### 2. Tạo môi trường ảo (khuyến nghị)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Cài đặt dependencies

**Trên Windows:**
```bash
pip install -r requirements.txt
```

**Trên macOS / Linux** (bỏ qua `pyaudiowpatch` không tương thích):
```bash
pip install faster-whisper google-generativeai pyaudio webrtcvad numpy python-dotenv
```

> Nếu gặp lỗi cài `pyaudio` trên macOS, hãy cài PortAudio trước:
> ```bash
> brew install portaudio
> pip install pyaudio
> ```

### 4. Cấu hình API key

```bash
cp .env.example .env
```

Mở file `.env` và điền Gemini API key:

```
GEMINI_API_KEY=AIza...
```

---

## Lấy Gemini API key (miễn phí)

1. Truy cập [aistudio.google.com](https://aistudio.google.com)
2. Đăng nhập bằng tài khoản Google
3. Nhấn **"Get API key"** → **"Create API key"**
4. Copy key và dán vào file `.env`

> Gói miễn phí cho phép khoảng 15 request/phút và 1 triệu token/ngày — đủ dùng cho mục đích cá nhân.

---

## Cách chạy

```bash
python main.py
```

1. Chọn thiết bị âm thanh từ dropdown (trên Windows sẽ thấy các thiết bị loopback)
2. Nhấn **▶ Bắt đầu**
3. Chơi game — bản dịch sẽ hiện tự động khi có lời thoại
4. Nhấn **■ Dừng** để tắt

---

## Các model Whisper

Cấu hình trong `.env` qua `WHISPER_MODEL`:

| Model | VRAM / RAM | Tốc độ | Độ chính xác |
|-------|-----------|--------|--------------|
| `tiny` | ~75 MB | Rất nhanh | Thấp |
| `base` | ~150 MB | Nhanh | Trung bình (**mặc định**) |
| `small` | ~500 MB | Trung bình | Tốt |

Khuyến nghị bắt đầu với `base`. Nếu nhận dạng không chính xác với tiếng Anh có accent, thử `small`.

---

## Cấu hình nâng cao

Tất cả cài đặt đều có thể thay đổi trong file `.env`:

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `GEMINI_API_KEY` | _(bắt buộc)_ | API key từ Google AI Studio |
| `WHISPER_MODEL` | `base` | Model nhận dạng giọng nói |
| `TARGET_LANGUAGE` | `Vietnamese` | Ngôn ngữ đích để dịch |
| `VAD_AGGRESSIVENESS` | `2` | Độ nhạy phát hiện giọng nói (0–3, 3 = nhạy nhất) |
| `SAMPLE_RATE` | `16000` | Tần số lấy mẫu (Hz) |
| `CHUNK_DURATION_MS` | `30` | Độ dài mỗi chunk âm thanh (ms) |

---

## Cấu trúc dự án

```
game-audio-translator/
├── main.py              # Entry point
├── requirements.txt
├── .env.example
├── .env                 # (tự tạo, không commit)
└── src/
    ├── config.py        # Đọc cấu hình từ .env
    ├── audio/
    │   ├── capture.py   # WASAPI loopback (Windows) / mic (macOS/Linux)
    │   └── vad.py       # Phát hiện giọng nói với webrtcvad
    ├── ai/
    │   ├── transcriber.py  # STT với faster-whisper
    │   └── translator.py   # Dịch với Gemini API
    └── ui/
        └── window.py    # Giao diện tkinter
```

---

## Xử lý sự cố thường gặp

**Không thấy thiết bị âm thanh (Windows)**
- Đảm bảo đã cài `pyaudiowpatch` (không phải `pyaudio` thông thường)
- Kiểm tra trong Device Manager xem sound card có hoạt động không

**Lỗi `GEMINI_API_KEY is not set`**
- Kiểm tra file `.env` đã tồn tại và có key hợp lệ

**Whisper nhận dạng sai hoặc bỏ sót**
- Thử model `small` thay vì `base`
- Tăng `VAD_AGGRESSIVENESS` lên `3` nếu bỏ sót nhiều
- Giảm xuống `1` nếu nhận nhầm tiếng ồn

**Dịch chậm**
- Gemini API free tier bị giới hạn tốc độ — ứng dụng tự động retry 1 lần
