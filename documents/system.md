# TÀI LIỆU ĐẶC TẢ KỸ THUẬT HỆ THỐNG QUẢN LÝ T&A LAB (TLMS)

**Dự án:** T&A Lab Management System (TLMS)
**Phiên bản:** 1.0
**Trạng thái:** Bản thảo thiết kế (Draft Design)
**Mục tiêu cốt lõi:** Chuyển đổi số toàn diện quy trình vận hành Lab, bao gồm: Tự động hóa Onboarding, Quản trị hiệu suất theo thời gian thực (Real-time Performance), và Số hóa hồ sơ năng lực thành viên (Dynamic ePortfolio).

---

## I. KIẾN TRÚC TỔNG THỂ (SYSTEM ARCHITECTURE)

Hệ thống được xây dựng dựa trên mô hình **Client-Server** kết hợp với kiến trúc **Modular Monolith** (hoặc Micro-services tùy quy mô), ưu tiên tính tách biệt giữa giao diện và xử lý nghiệp vụ để đảm bảo khả năng bảo trì (Maintainability) và mở rộng (Scalability).

### 1. Client Side (Frontend)

* **Web Portal (SPA - ReactJS/VueJS):** Cổng thông tin tập trung.
* *Admin Dashboard:* Quản trị dữ liệu nguồn (Master Data) và cấu hình hệ thống.
* *Mentor View:* Công cụ chấm điểm, review code và duyệt task.
* *Candidate/Member View:* Theo dõi lộ trình (Roadmap), bảng xếp hạng và đăng ký lịch.


* **Mobile View (Responsive Design):** Giao diện được tối ưu hóa theo phương pháp "Mobile-First", đảm bảo sinh viên truy cập nhanh chóng, mượt mà trên thiết bị di động.

### 2. Server Side (Backend)

* **Core API (NodeJS/GoLang/Python):** RESTful API xử lý toàn bộ logic nghiệp vụ, xác thực và phân quyền.
* **Background Workers (Cron Jobs):** Các tác vụ chạy ngầm định kỳ:
* Quét dữ liệu chấm công (Check-in logs).
* Tính toán điểm kinh nghiệm (XP) và cập nhật Level.
* Kích hoạt các trigger gửi thông báo tự động.



### 3. Integration Layer (Tầng tích hợp)

* **Identity Service:** Tích hợp OAuth 2.0, đồng bộ xác thực với hệ thống Check-in hiện hữu (Single Sign-On).
* **Notification Service:** Kết nối đa kênh (Omni-channel), trọng tâm là **Zalo OA API** qua cơ chế Webhook để tương tác hai chiều.

---

## II. PHÂN HỆ CHỨC NĂNG (CORE MODULES)

### 1. Phân hệ Quản lý Định danh & Phân quyền (IAM)

* **Authentication:** Sử dụng cơ chế Federated Login (OAuth) từ hệ thống cũ. Không phát sinh tài khoản mới, định danh dựa trên UserID đồng bộ.
* **RBAC (Role-Based Access Control):** Phân quyền chặt chẽ theo vai trò:
* **Candidate (Thực tập sinh):** Quyền hạn chế (Xem lộ trình, nhận task, đăng ký lịch).
* **Member (Thành viên chính thức):** Quyền truy cập tài nguyên nội bộ, thư viện tài liệu.
* **Mentor (Người hướng dẫn):** Quyền phê duyệt (Approve/Reject), đánh giá (Review) và xem báo cáo tiến độ Mentee.
* **Admin:** Quyền quản trị cao nhất (System Configuration).



### 2. Phân hệ Lộ trình & Gamification (LMS Engine)

Đây là "trái tim" của hệ thống, giúp duy trì động lực và định hướng phát triển.

* **Task Management (Quản lý nhiệm vụ):**
* *Dependency Logic:* Áp dụng cơ chế khóa/mở (Unlock) theo điều kiện tiên quyết (Prerequisite). Ví dụ: Hoàn thành "Core Task 1" mới mở "Core Task 2".
* *Task Types:*
* **Core Tasks:** Nhiệm vụ bắt buộc (Onboarding, Văn hóa, Quy trình thiết bị).
* **Bounty Tasks:** Nhiệm vụ thử thách/Dự án (Coding, Research, Design) - Nguồn thu thập XP chính.




* **XP & Leveling System:**
* Công thức tính Level: 

* **Leaderboard:** Bảng xếp hạng thi đua cập nhật thời gian thực (Real-time).


* **Promotion Engine (Cơ chế thăng cấp tự động):** Worker quét dữ liệu hàng đêm, tự động gắn thẻ "Ready to Promote" nếu thỏa mãn bộ tiêu chí "Tam giác vàng":
1. Core Task Progress = **100%**.
2. Total XP  **Target XP** (ví dụ: 1000).
3. Discipline Score (Điểm kỷ luật)  **80/100**.



### 3. Phân hệ Lịch trình & Kiểm soát tuân thủ (Scheduler & Compliance)

* **Weekly Registration:** Cổng đăng ký slot làm việc (Sáng/Chiều/Tối) mở vào đầu tuần.
* **Attendance Reconciliation (Thuật toán đối soát):** So khớp giữa *Lịch đăng ký* và *Log Check-in thực tế*.
* *Logic chấm điểm:*
* Đúng lịch + Có mặt  **+Điểm chuyên cần**.
* Đúng lịch + Vắng mặt  **-Điểm kỷ luật** (Kèm cảnh báo Zalo).
* Không lịch + Có mặt  **+Điểm thưởng** (Extra Effort/Overtime).





### 4. Phân hệ Hồ sơ năng lực động (Dynamic ePortfolio)

* **Skill Matrix Automation:** Tự động ánh xạ (Mapping) kết quả Task vào kỹ năng tương ứng.
* *Ví dụ:* Task "Database Design" hoàn thành  Skill "SQL" tăng +10 điểm.


* **Project History:** Lưu vết "Digital Footprint" của thành viên (Task đã làm, người review, link sản phẩm).
* **Export Capability:** Xuất hồ sơ dưới dạng PDF hoặc Public Link (CV Online) phục vụ tuyển dụng.

### 5. Phân hệ Thông báo & Tương tác (Notification Center - Zalo Bot)

* **Event Triggers:**
* Nhắc lịch (Reminder): Gửi trước phiên làm việc 30 phút.
* Kết quả Review: Thông báo ngay khi Mentor chấm điểm.
* Cảnh báo vắng mặt (Inactivity Alert): Kích hoạt sau 3 ngày không đăng nhập.


* **Interactive Action:** Tích hợp Zalo Mini App cho phép Mentor thao tác "Duyệt nhanh" ngay trên giao diện chat.

---

## III. THIẾT KẾ CƠ SỞ DỮ LIỆU (DATABASE SCHEMA)

Sử dụng CSDL Quan hệ (RDBMS) để đảm bảo tính toàn vẹn dữ liệu. Các thực thể chính bao gồm:

| Tên Bảng | Vai trò & Mô tả |
| --- | --- |
| **Users** | Lưu trữ hồ sơ người dùng, trạng thái (Active/Inactive), Role, Current XP, Discipline Score. |
| **Tasks** | Danh mục nhiệm vụ: `type` (Core/Bounty), `xp_reward`, `skill_tag`, `min_level_req`. |
| **User_Tasks** | **Bảng Transaction cốt lõi**. Lưu trạng thái làm việc: `status` (Pending/Reviewing/Completed/Rejected), `proof_link`, `mentor_comment`. |
| **Schedules** | Lưu lịch đăng ký và kết quả đối soát check-in: `shift`, `checkin_time`, `status` (Present/Absent/Late). |
| **Skills & User_Skills** | Hệ thống kỹ năng và điểm số kỹ năng tích lũy của từng User (phục vụ ePortfolio). |

---

## IV. HÀNH TRÌNH NGƯỜI DÙNG (USER JOURNEY MAP)

**Kịch bản tiêu chuẩn: Từ Candidate đến Official Member (Fast-track)**

1. **Giai đoạn Onboarding (Day 1):**
* User đăng nhập qua OAuth. Hệ thống định danh Role: **Candidate**.
* **Zalo Bot:** Gửi lời chào và kích hoạt nhiệm vụ đầu tiên: *"Đọc nội quy Lab & Cập nhật Profile"*.
* User hoàn thành  Hệ thống ghi nhận, cộng **10 XP** khởi động.


2. **Giai đoạn Grinding (Day 2 - Day 30):**
* **Đăng ký:** Đầu tuần, User vào Web Portal đăng ký lịch (T3, T5, T7).
* **Thực thi:**
* User đến Lab, Check-in vân tay  Hệ thống ghi nhận trạng thái "Present".
* User nhận Task *"Fix bug giao diện Web"* (50 XP) trên bảng Bounty.


* **Nộp bài & Đánh giá:**
* User submit link Github lên hệ thống.
* Mentor nhận thông báo Zalo  Review code  Bấm **Approve**.
* Hệ thống: Cộng **50 XP** cho User, tăng chỉ số Skill **"Web Dev"** trong ePortfolio.




3. **Giai đoạn Promotion (Day 45):**
* User đạt ngưỡng **1200 XP** và hoàn thành 100% Core Task.
* Hệ thống gửi đề xuất thăng cấp cho Admin.
* Admin phê duyệt  User chuyển Role: **Member**.
* Zalo Bot gửi thiệp chúc mừng Official Member.



---

## V. ĐỀ XUẤT CÔNG NGHỆ (TECH STACK)

Lựa chọn công nghệ dựa trên tiêu chí: **Hiện đại - Ổn định - Dễ chuyển giao (Knowledge Transfer)**.

* **Backend:** **NestJS (TypeScript)** hoặc **Python (FastAPI)**.
* *Lý do:* Cấu trúc rõ ràng, cộng đồng lớn, dễ dàng cho sinh viên thế hệ sau tiếp cận và bảo trì.


* **Database:** **PostgreSQL**.
* *Lý do:* Mạnh mẽ, mã nguồn mở, hỗ trợ tốt các truy vấn phức tạp và kiểu dữ liệu JSON (cho cấu hình linh động).


* **Frontend:** **Next.js (React Framework)**.
* *Lý do:* Hiệu năng cao, hỗ trợ Server-Side Rendering (SSR) giúp SEO tốt cho trang ePortfolio cá nhân.


* **Bot Platform:** **Zalo Official Account (Zalo OA)**.
* *Lý do:* Phổ biến tại Việt Nam, độ trễ thấp, trải nghiệm người dùng tự nhiên.


* **Infrastructure:** **Docker & Docker Compose**.
* *Lý do:* Đóng gói môi trường, dễ dàng triển khai (Deploy) trên bất kỳ máy chủ nào mà không lo xung đột cấu hình.


