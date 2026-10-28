# User Import from MongoDB - Documentation

## Tổng quan

Tính năng cho phép import toàn bộ user từ MongoDB (S4H checkin_service) vào PostgreSQL database của TLMS.

**Cơ chế:** Selective Sync - Chỉ import user **chưa có** trong hệ thống (dựa trên `s4h_user_id`).

---

## Cấu hình Docker (Production)

### 1. Cấu hình trong docker-compose.yml

Tất cả đã được cấu hình sẵn trong `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      # MongoDB Connection (pre-configured)
      MONGODB_CONNECTION_STRING: ${MONGODB_CONNECTION_STRING}
      MONGODB_DATABASE: checkin_service
      MONGODB_USERS_COLLECTION: users
      # Secret Token (pre-configured)
      USER_IMPORT_SECRET_TOKEN: ${USER_IMPORT_SECRET_TOKEN}
```

### 2. Build và chạy Docker

```bash
# Build lại sau khi thay đổi
docker-compose build backend

# Chạy toàn bộ hệ thống
docker-compose up -d

# Xem logs
docker-compose logs -f backend
```

### 3. Secret Token (Đã được tạo sẵn)

Repository không cung cấp token mặc định. Hãy tạo token riêng trong secret manager.

⚠️ **LƯU Ý BẢO MẬT:** Đổi token này trong production bằng cách set environment variable:
```bash
USER_IMPORT_SECRET_TOKEN=your-new-super-secret-token docker-compose up -d
```

---

## API Usage

### Endpoint: Import Users

**POST** `/api/v1/admin/import-users`

#### Yêu cầu:

1. **Authentication:**
   - Header: `Authorization: Bearer <access_token>`
   - Token phải thuộc user có **Admin role**

2. **Secret Token:**
   - Header: `X-Import-Secret: <configured-import-secret>`
   - Hoặc token bạn đã cấu hình trong docker-compose.yml

#### Response Example:

```json
{
  "success": true,
  "message": "Import thành công: 150 user mới được thêm",
  "total_in_mongodb": 500,
  "imported_count": 150,
  "skipped_count": 350,
  "error_count": 0,
  "errors": []
}
```

#### Response Fields:

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Import thành công hay không |
| `message` | string | Thông báo kết quả |
| `total_in_mongodb` | integer | Tổng số user trong MongoDB |
| `imported_count` | integer | Số user mới được thêm |
| `skipped_count` | integer | Số user bỏ qua (đã tồn tại) |
| `error_count` | integer | Số lỗi gặp phải |
| `errors` | array | Danh sách lỗi (tối đa 10) |

---

### Endpoint: Check Import Status

**GET** `/api/v1/admin/import-users/status`

Kiểm tra cấu hình import (không cần secret token)

#### Response Example:

```json
{
  "mongodb_configured": true,
  "secret_token_configured": true,
  "database": "checkin_service",
  "collection": "users",
  "initiated_by": "admin@example.com"
}
```

---

## Các bước thực hiện Import

### Bước 1: Kiểm tra cấu hình

```bash
curl -X GET "http://localhost:8000/api/v1/admin/import-users/status" \
  -H "Authorization: Bearer <admin_token>"
```

Đảm bảo:
- `mongodb_configured: true`
- `secret_token_configured: true`

### Bước 2: Gọi Import

```bash
curl -X POST "http://localhost:8000/api/v1/admin/import-users" \
  -H "Authorization: Bearer <admin_token>" \
  -H "X-Import-Secret: <configured-import-secret>"
```

### Bước 3: Kiểm tra kết quả

Xem response để biết:
- Bao nhiêu user được import
- Bao nhiêu user bị skip (đã tồn tại)
- Có lỗi nào xảy ra không

---

## Bảo mật

### Lớp bảo vệ 1: Admin Role Only
- Chỉ user có `admin` role mới gọi được endpoint
- Token được validate qua middleware

### Lớp bảo vệ 2: Secret Token
- Header `X-Import-Secret` phải khớp với `USER_IMPORT_SECRET_TOKEN`
- Sử dụng constant-time comparison để chống timing attack

### Lớp bảo vệ 3: No Sensitive Logging
- Connection string không bao giờ được log
- Password không được log
- Chỉ log email user và thống kê

### Lớp bảo vệ 4: Selective Sync
- Chỉ import user chưa có
- Không overwrite dữ liệu hiện tại
- Batch processing để tránh timeout

---

## Mapping Fields

| MongoDB Field | TLMS Field | Notes |
|---------------|------------|-------|
| `userId` | `s4h_user_id` | Primary key để so sánh |
| `email` | `email` | Required field |
| `firstName` | `first_name` | Optional |
| `lastName` | `last_name` | Optional |
| `studentId` | `student_id` | Optional |
| `roles` | `roles` | Ignored (TLMS uses default 'candidate') |

**Fields không import:**
- `phone` - Không cần thiết cho TLMS
- `zaloUid` - Không cần thiết cho TLMS
- `isFollowing` - Không cần thiết cho TLMS
- `createdAt`, `updatedAt` - TLMS tự tạo timestamps

---

## Xử lý lỗi

### Lỗi: "Server chưa cấu hình secret token"
- **Nguyên nhân:** `USER_IMPORT_SECRET_TOKEN` chưa được set trong `.env`
- **Giải pháp:** Thêm token vào `.env` và restart server

### Lỗi: "Secret token không hợp lệ"
- **Nguyên nhân:** Header `X-Import-Secret` không đúng
- **Giải pháp:** Kiểm tra lại token đã cấu hình trong secret manager

### Lỗi: "Không thể kết nối MongoDB"
- **Nguyên nhân:** Connection string sai hoặc MongoDB không reachable
- **Giải pháp:** 
  - Kiểm tra connection string
  - Đảm bảo server có thể connect tới MongoDB host đã cấu hình
  - Kiểm tra firewall/network

### Lỗi: "Bạn không có quyền"
- **Nguyên nhân:** User không có admin role
- **Giải pháp:** Đăng nhập bằng admin account

---

## Best Practices

1. **Chạy vào giờ thấp điểm:** Import có thể mất thời gian nếu có nhiều user
2. **Backup database:** Luôn backup PostgreSQL trước khi import
3. **Kiểm tra trước:** Dùng endpoint `/status` để verify config
4. **Giám sát logs:** Theo dõi log trong quá trình import
5. **Token rotation:** Định kỳ thay đổi `USER_IMPORT_SECRET_TOKEN`

---

## Example Script (Python)

```python
import httpx
import asyncio

async def import_users():
    admin_token = "your-admin-access-token"
    secret_token = "<configured-import-secret>"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/admin/import-users",
            headers={
                "Authorization": f"Bearer {admin_token}",
                "X-Import-Secret": secret_token
            },
            timeout=300  # 5 minutes timeout
        )
        
        result = response.json()
        print(f"Import result: {result}")

asyncio.run(import_users())
```
