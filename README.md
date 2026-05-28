# VSmartPay AI Support Agent

Vietnamese RAG-based Customer Support Agent for Fintech Wallet.

---

## 📌 Phase 1: Codebase Cleanup

Dự án hiện tại vừa thực hiện pha dọn dẹp (cleanup) codebase cũ từ Mini Wallet backend để chuẩn bị refactor sang chatbot support agent.

### Những việc đã thực hiện trong pha này:
- Xóa bỏ các modules nghiệp vụ ví điện tử không liên quan (`users`, `wallets`, `ledger`, `risk`, `transactions`, `analytics`, `agents`).
- Xóa bỏ các scripts liên quan đến Kaggle / PaySim / sandbox seed data.
- Loại bỏ các integration tests cũ và cập nhật lại tests cơ bản.
- Sửa đổi config, dọn dẹp `constants.py` và đơn giản hóa `app/main.py`.
- Tích hợp thêm endpoint GET `/health` mới phục vụ hệ thống AI Support Agent.

> [!NOTE]
> Phase này mới chỉ dừng lại ở bước dọn dẹp hệ thống cũ, các thành phần RAG, Vector Database (nếu có) và Chatbot logic sẽ được bổ sung và phát triển trong các phase tiếp theo.

---

## 🛠️ Technology Stack (Mục tiêu & Cơ bản)

* **Language**: Python 3.10+
* **Web Framework**: FastAPI (Uvicorn làm ASGI server)
* **Database**: MongoDB (via `motor` asynchronous driver & `pymongo`)
* **Validation & Settings**: Pydantic v2 & Pydantic Settings
* **Testing**: pytest & pytest-asyncio

---

## 📂 Project Structure Hiện tại

```text
vsmartpay-ai-support-agent/
├── app/
│   ├── main.py            # Main application entrypoint
│   ├── config.py          # Configuration & environment variables reader
│   ├── database.py        # Asynchronous MongoDB (Motor) connection manager
│   │
│   └── common/            # Shared utilities, exceptions, & helpers
│       ├── constants.py   # App constants
│       ├── exceptions.py  # Global application exceptions
│       ├── response.py    # Unified API response helpers
│       └── utils.py       # Cryptography & ID helpers
│
├── tests/                 # Unit & basic test suites
│   ├── conftest.py
│   └── test_common.py
│
├── requirements.txt       # Dependencies
├── .env                   # Environment configurations
└── .env.example           # Example environment template
```

---

## ⚙️ Quick Start

### 1. Cài đặt môi trường
Đảm bảo bạn đã cài đặt Python 3.10 trở lên và MongoDB.

Tạo môi trường ảo và cài đặt thư viện:
```bash
# Tạo virtual environment
# Với python 3.14 (ví dụ trên Windows):
& "D:\New folder\python.exe" -m venv venv

# Kích hoạt virtual environment
# Trên Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Trên macOS/Linux:
source venv/bin/activate

# Cài đặt requirements
pip install -r requirements.txt
```

### 2. Cấu hình .env
Copy `.env.example` thành `.env` và tùy chỉnh các tham số kết nối MongoDB Atlas/Local của bạn.

### 3. Khởi chạy phát triển
Chạy ứng dụng:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Các URL quan trọng:
* **Base URL**: `http://127.0.0.1:8000`
* **Health Check**: `http://127.0.0.1:8000/health`
* **Swagger API Docs**: `http://127.0.0.1:8000/docs`

### 4. Kiểm thử
Chạy bộ unit test:
```bash
pytest
```
