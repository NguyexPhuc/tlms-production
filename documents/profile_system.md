# Profile System - Tài liệu hướng dẫn

## Tổng quan

Hệ thống Profile cho phép sinh viên:
- Xem thống kê chi tiết về giờ làm, nhiệm vụ, thành tích
- Thêm minh chứng (evidence) vào profile với links, mô tả, tags
- Tự động đăng ký lịch làm dựa trên lịch học để đủ 8h/ngày
- Tính toán rewards và điểm kỷ luật

## Cấu trúc hệ thống

### Backend

#### 1. Models (`backend/app/models/profile.py`)
- **ProfileEvidence**: Lưu trữ minh chứng của sinh viên
  - Links, mô tả, tags
  - Trạng thái: pending, verified, rejected
  - Có thể link với task hoặc tự do

#### 2. Schemas (`backend/app/schemas/profile.py`)
- **ProfileEvidenceCreate/Update**: Tạo/cập nhật minh chứng
- **ProfileStats**: Thống kê đầy đủ (work, tasks, achievements)
- **AutoScheduleRequest**: Yêu cầu tự động đăng ký lịch
- **ProfileResponse**: Response đầy đủ với user info, stats, evidence

#### 3. Service (`backend/app/services/profile.py`)
**ProfileService** cung cấp:

##### Evidence Management
```python
# Tạo minh chứng
async def create_evidence(db, user, evidence_data)

# Cập nhật minh chứng
async def update_evidence(db, user, evidence_id, evidence_data)

# Xác nhận minh chứng (Mentor/Admin only)
async def verify_evidence(db, verifier, evidence_id, verify_data)

# Xóa minh chứng
async def delete_evidence(db, user, evidence_id)

# Lấy danh sách minh chứng
async def get_user_evidence(db, user, include_pending=True)
```

##### Statistics Calculation
```python
# Thống kê giờ làm
async def calculate_work_schedule_stats(db, user)
# Returns: WorkScheduleStats with hours, attendance rate

# Thống kê nhiệm vụ
async def calculate_task_stats(db, user)
# Returns: TaskStats with completed tasks, XP, level

# Thống kê thành tích
async def calculate_achievement_summary(db, user)
# Returns: AchievementSummary with evidence, skills, discipline

# Lấy thống kê đầy đủ
async def get_profile_stats(db, user)
```

##### Auto-Schedule
```python
# Tự động đăng ký lịch làm
async def auto_register_work_schedule(db, user, request)
```

**Logic Auto-Schedule:**
1. Lấy lịch học từ database
2. Xác định các ca trống (không trùng lịch học)
3. Ưu tiên theo preference của user (morning/afternoon/evening)
4. Đăng ký tối đa 2 ca/ngày (8h) với `registration_type=AUTO`
5. Trả về kết quả và conflicts nếu có

#### 4. API Routes (`backend/app/api/routes/profile.py`)

**Evidence Endpoints:**
- `POST /api/v1/profile/evidence` - Thêm minh chứng
- `GET /api/v1/profile/evidence` - Lấy danh sách minh chứng
- `PATCH /api/v1/profile/evidence/{id}` - Cập nhật minh chứng
- `DELETE /api/v1/profile/evidence/{id}` - Xóa minh chứng
- `POST /api/v1/profile/evidence/{id}/verify` - Xác nhận (Mentor/Admin)

**Profile Endpoints:**
- `GET /api/v1/profile/me` - Lấy profile đầy đủ của user hiện tại
- `GET /api/v1/profile/stats` - Lấy thống kê profile
- `GET /api/v1/profile/user/{user_id}` - Xem profile user khác (Mentor/Admin)

**Auto-Schedule:**
- `POST /api/v1/profile/auto-schedule` - Tự động đăng ký lịch

#### 5. Database Migration (`backend/alembic/versions/008_create_profile_evidence.py`)

Tạo bảng `profile_evidence` với:
- id, user_id, task_id
- title, description, evidence_links, tags
- status, verified_by_id, verified_at, verification_notes
- is_public, is_featured
- timestamps

### Frontend

#### 1. Types (`frontend/src/types/profile.ts`)
TypeScript interfaces cho tất cả profile-related data

#### 2. API Client (`frontend/src/lib/api.ts`)
Thêm các methods:
```typescript
apiClient.getMyProfile()
apiClient.getProfileStats()
apiClient.createEvidence(data)
apiClient.updateEvidence(id, data)
apiClient.deleteEvidence(id)
apiClient.verifyEvidence(id, data)
apiClient.autoSchedule(request)
```

#### 3. Profile Page (`frontend/src/app/profile/page.tsx`)

**Components:**

1. **Header Section**
   - Avatar, tên, email, student_id
   - Roles badges
   - Button "Tự động đăng ký lịch"

2. **Stats Grid** (3 cards)
   - Work Stats: Giờ làm tuần/tháng/tổng, tỷ lệ điểm danh
   - Task Stats: Số task hoàn thành, Core/Bounty, XP, Level
   - Achievements: Evidence đã verify, featured, điểm kỷ luật

3. **Evidence Section**
   - Grid hiển thị tất cả evidence
   - Button "Thêm minh chứng"
   - Badge status (pending/verified/rejected)
   - Featured evidence có star icon
   - Tags và links

4. **Recent Activities** (2 columns)
   - Recent Tasks: 10 task gần nhất
   - Upcoming Schedules: Lịch làm sắp tới

5. **Add Evidence Modal**
   - Form nhập title, description
   - Thêm multiple links
   - Thêm tags
   - Checkbox is_public

## Cách sử dụng

### 1. Chạy Migration

```bash
cd backend
alembic upgrade head
```

### 2. Khởi động Backend

```bash
cd backend
uvicorn app.main:app --reload
```

### 3. Khởi động Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Truy cập Profile

1. Đăng nhập vào hệ thống
2. Từ Dashboard, click "Hồ sơ năng lực"
3. Hoặc truy cập trực tiếp: `http://localhost:3000/profile`

## Use Cases

### 1. Sinh viên thêm minh chứng

```
User Story: Sinh viên hoàn thành project, muốn thêm vào profile

1. Click "Thêm minh chứng"
2. Nhập:
   - Tiêu đề: "Hoàn thành Dashboard Analytics"
   - Mô tả: "Xây dựng dashboard với React + Chart.js"
   - Links: [Github repo, Live demo]
   - Tags: [react, typescript, chartjs]
3. Submit
4. Evidence status = "pending"
5. Chờ Mentor verify
```

### 2. Mentor xác nhận minh chứng

```
Mentor/Admin có thể:
1. Truy cập profile của sinh viên
2. Xem evidence pending
3. Verify với:
   - status: verified/rejected
   - verification_notes
   - is_featured: true (nếu xuất sắc)
```

### 3. Tự động đăng ký lịch

```
User Story: Sinh viên có lịch học, muốn tự động đăng ký lịch làm

1. Click "Tự động đăng ký lịch"
2. Hệ thống:
   - Lấy lịch học từ LHU API
   - Tìm ca trống (không trùng lịch học)
   - Đăng ký 2 ca/ngày để đủ 8h
   - Tránh conflicts
3. Hiển thị kết quả:
   - Số lịch đã tạo
   - Danh sách conflicts (nếu có)
```

### 4. Xem thống kê

Profile hiển thị real-time:
- Tổng giờ làm (tuần/tháng/tất cả)
- Tỷ lệ điểm danh
- Số task hoàn thành
- Level và XP hiện tại
- Điểm kỷ luật
- Số evidence verified
- Skill tags thu thập được

## Rewards & Gamification

### Tính điểm

Profile tự động tính:
1. **Work Stats**: Từ bảng `schedules` và `attendances`
2. **Task Stats**: Từ bảng `user_tasks` với status=COMPLETED
3. **Achievement**: Từ `profile_evidence` với status=VERIFIED

### Promotion Criteria

User đủ điều kiện thăng cấp khi:
- `core_task_progress >= 100%`
- `current_xp >= 1000`
- `discipline_score >= 80`

→ `is_ready_to_promote = true` hiển thị trong profile

## API Examples

### GET Profile
```bash
curl -X GET "http://localhost:8000/api/v1/profile/me" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Create Evidence
```bash
curl -X POST "http://localhost:8000/api/v1/profile/evidence" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Web Dashboard Project",
    "description": "Built analytics dashboard",
    "evidence_links": ["https://github.com/..."],
    "tags": ["react", "typescript"],
    "is_public": true
  }'
```

### Auto Schedule
```bash
curl -X POST "http://localhost:8000/api/v1/profile/auto-schedule" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "week_start_date": "2026-02-03",
    "target_hours_per_day": 8,
    "prefer_afternoon": true
  }'
```

## Troubleshooting

### Evidence không hiển thị
- Kiểm tra `is_public = true`
- Kiểm tra user_id đúng

### Auto-schedule không tạo lịch
- Kiểm tra user có `student_id`
- Kiểm tra đã có lịch học trong database
- Xem conflicts trong response

### Stats không chính xác
- Stats được tính real-time từ database
- Kiểm tra dữ liệu trong `schedules`, `user_tasks`, `profile_evidence`

## Future Enhancements

1. **Public Profile URL**: Share profile với employer
2. **PDF Export**: Xuất profile thành CV/Portfolio PDF
3. **Skill Graph**: Visualize skill tags
4. **Achievement Badges**: System badges tự động
5. **Profile Templates**: Customizable profile themes
