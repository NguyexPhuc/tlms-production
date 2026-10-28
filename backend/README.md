# TLMS Backend

T&A Lab Management System - Backend API

## Cài đặt

### 1. Tạo môi trường ảo

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate  # Windows
```

### 2. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 3. Cấu hình môi trường

```bash
cp .env.example .env
# Chỉnh sửa .env với thông tin database và S4H Auth
```

### 4. Chạy ứng dụng

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Hoặc
python -m app.main
```

### 5. Truy cập API docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Cấu trúc thư mục

```
backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── auth.py          # Auth endpoints (login, register, etc.)
│   │   ├── __init__.py
│   │   └── deps.py              # Dependencies (auth middleware)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Settings from environment
│   │   ├── database.py          # Database connection
│   │   └── exceptions.py        # Custom exceptions
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py              # User model (local_users table)
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── auth.py              # Pydantic schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── s4h_auth.py          # S4H Auth Service integration
│   │   └── user.py              # Local user service
│   ├── __init__.py
│   └── main.py                  # FastAPI application
├── .env.example
├── requirements.txt
└── README.md
```

## API Endpoints

### Authentication

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/v1/auth/login` | Đăng nhập |
| POST | `/api/v1/auth/register` | Đăng ký |
| POST | `/api/v1/auth/refresh` | Làm mới token |
| POST | `/api/v1/auth/logout` | Đăng xuất |
| GET | `/api/v1/auth/me` | Lấy thông tin user hiện tại |

### Authentication Flow (OAuth/S4H Auth)

```
┌─────────┐     ┌──────────────┐     ┌──────────────┐
│ Client  │────▶│ TLMS Backend │────▶│  S4H Auth    │
└─────────┘     └──────────────┘     └──────────────┘
     │                 │                    │
     │ 1. Login        │                    │
     │ (email/pass)    │                    │
     │────────────────▶│                    │
     │                 │ 2. Forward to S4H  │
     │                 │───────────────────▶│
     │                 │                    │
     │                 │ 3. JWT Tokens      │
     │                 │◀───────────────────│
     │                 │                    │
     │                 │ 4. Lazy Sync User  │
     │                 │ (Create/Update)    │
     │                 │                    │
     │ 5. Return       │                    │
     │ tokens + user   │                    │
     │◀────────────────│                    │
```

## Môi trường

| Variable | Mô tả |
|----------|-------|
| `DATABASE_URL` | PostgreSQL connection string |
| `S4H_AUTH_BASE_URL` | S4H Auth Service URL |
| `CORS_ORIGINS` | Allowed CORS origins |
| `DEBUG` | Enable debug mode |

## Roles (RBAC)

- **Candidate**: Thực tập sinh - Quyền hạn chế
- **Member**: Thành viên chính thức
- **Mentor**: Người hướng dẫn - Quyền phê duyệt
- **Admin**: Quản trị viên - Quyền cao nhất
