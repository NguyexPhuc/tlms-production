# TLMS - T&A Lab Management System

Hệ thống quản lý Lab T&A với gamification, theo dõi hiệu suất và ePortfolio.

## Yêu cầu

- Docker & Docker Compose

## Cấu trúc dự án

```
TLMS/
├── backend/          # FastAPI Backend
│   ├── app/
│   │   ├── api/      # API routes
│   │   ├── core/     # Config, database, exceptions
│   │   ├── models/   # SQLAlchemy models
│   │   ├── schemas/  # Pydantic schemas
│   │   └── services/ # Business logic
│   ├── alembic/      # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/         # Next.js Frontend
│   ├── src/
│   │   ├── app/      # Pages (App Router)
│   │   ├── contexts/ # React Contexts
│   │   ├── lib/      # API client
│   │   └── types/    # TypeScript types
│   ├── Dockerfile
│   └── package.json
├── documents/        # Tài liệu đặc tả
├── docker-compose.yml
└── .env.example
```

## Khởi chạy

### 1. Cấu hình môi trường

```bash
cp .env.example .env
# Chỉnh sửa .env với các giá trị phù hợp
```

### 2. Build và chạy với Docker Compose

```bash
# Build và khởi động tất cả services
docker compose up -d --build

# Xem logs
docker compose logs -f

# Dừng services
docker compose down
```

### 3. Truy cập ứng dụng

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Tính năng Authentication

Hệ thống sử dụng **Proxy Authentication Pattern** với S4H Auth Service:

1. **Đăng nhập:** `/api/v1/auth/login`
2. **Đăng ký:** `/api/v1/auth/register`
3. **Làm mới token:** `/api/v1/auth/refresh`
4. **Đăng xuất:** `/api/v1/auth/logout`
5. **Thông tin user:** `/api/v1/auth/me`

**Lưu ý:** Password không được lưu trong hệ thống TLMS, chỉ forward đến S4H Auth.

## Database Migrations

```bash
# Chạy trong container backend
docker compose exec backend alembic revision --autogenerate -m "Initial migration"
docker compose exec backend alembic upgrade head
```

## Tech Stack

### Backend
- Python 3.12
- FastAPI
- SQLAlchemy (async)
- PostgreSQL
- Alembic (migrations)

### Frontend
- Next.js 14 (App Router)
- React 18
- TypeScript
- Tailwind CSS
- Axios

## Roles (RBAC)

| Role | Mô tả |
|------|-------|
| `candidate` | Thực tập sinh - Quyền hạn chế |
| `member` | Thành viên chính thức |
| `mentor` | Người hướng dẫn - Quyền review |
| `admin` | Quản trị viên - Quyền cao nhất |

## Gamification

- **XP (Experience Points):** Điểm kinh nghiệm từ hoàn thành task
- **Level:** Cấp độ tính từ XP
- **Discipline Score:** Điểm kỷ luật (chuyên cần)
- **Promotion:** Thăng cấp khi đạt "Tam giác vàng"

## License

© 2026 T&A Lab. All rights reserved.
