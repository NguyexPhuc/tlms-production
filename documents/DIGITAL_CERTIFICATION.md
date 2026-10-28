# TLMS Digital Certification Platform

## Tổng quan

Module chứng nhận số được tích hợp trực tiếp vào FastAPI, PostgreSQL và Next.js hiện tại. Điểm thi được tính ở backend; frontend không gửi điểm, đáp án đúng hoặc trạng thái đạt. Khi kết quả đạt ngưỡng, cùng transaction sẽ tạo duy nhất một chứng chỉ, QR thật và PDF A4 lưu trong private storage.

## Kiến trúc

- `Question` hiện có tiếp tục là ngân hàng câu hỏi.
- `Course` nhóm nội dung, kỹ năng và template chứng chỉ.
- `CourseEnrollment` lưu đăng ký và tiến độ của từng người học; bài thi chỉ mở sau khi đăng ký.
- `Lesson` là nội dung có thứ tự, trạng thái nháp/công bố trong khóa học.
- `Exam` cấu hình thời gian, điểm đạt, số lượt và thời hạn.
- `ExamAttempt` khóa từng lượt thi; `ExamAnswer` lưu câu trả lời.
- `ExamResult` là kết quả do backend chấm.
- `Certificate` chỉ được tạo từ một `ExamResult.passed = true`.
- `CertificateTemplate` lưu nhận diện và version của mẫu.
- `CertificateAuditLog` ghi cấp và thu hồi.
- `CertificateVerificationLog` ghi mọi lần xác minh, chỉ lưu fingerprint token/IP.

Các unique constraint trên `exam_results.attempt_id` và `certificates.exam_result_id` ngăn chấm/cấp trùng khi có request đồng thời. Endpoint submit khóa dòng attempt bằng `SELECT ... FOR UPDATE`.

## Biến môi trường

```env
PUBLIC_WEB_URL=https://quangphuc.id.vn
CERTIFICATE_STORAGE_DIR=/app/private/certificates
CERTIFICATE_ISSUER_NAME=T&A Lab
CERTIFICATE_VERIFY_RATE_LIMIT=30
```

- `PUBLIC_WEB_URL`: origin công khai được nhúng vào QR.
- `CERTIFICATE_STORAGE_DIR`: vùng private, không mount bằng `StaticFiles`.
- `CERTIFICATE_ISSUER_NAME`: tên mặc định của đơn vị phát hành.
- `CERTIFICATE_VERIFY_RATE_LIMIT`: số lần xác minh tối đa mỗi IP/phút trên một backend instance.

Khi chạy nhiều backend replica, thay limiter trong bộ nhớ bằng Redis và dùng object storage private (S3/MinIO) với signed URL ngắn hạn.

## API người học

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| GET | `/api/v1/courses` | Khóa học đã công bố |
| POST | `/api/v1/courses/{course_id}/enroll` | Đăng ký khóa học, idempotent |
| GET | `/api/v1/courses/enrollments/my` | Danh sách đăng ký của người học |
| GET | `/api/v1/courses/{course_id}/lessons` | Bài học đã công bố |
| GET | `/api/v1/exams` | Bài thi đã công bố và số lượt của user |
| POST | `/api/v1/exams/{exam_id}/start` | Bắt đầu/tiếp tục lượt thi |
| POST | `/api/v1/exam-attempts/{attempt_id}/submit` | Nộp đáp án để backend chấm |
| GET | `/api/v1/exam-attempts/{attempt_id}/result` | Xem kết quả có kiểm tra chủ sở hữu |
| GET | `/api/v1/certificates/my` | Chứng chỉ của tài khoản |
| GET | `/api/v1/certificates/{id}/download` | Tải PDF riêng tư |

## API công khai

`GET /api/v1/certificates/verify/{token}` trả một trong bốn trạng thái:

- `VALID`: hợp lệ.
- `EXPIRED`: đã hết hạn.
- `REVOKED`: đã thu hồi.
- `NOT_FOUND`: token không tồn tại.

Trang web tương ứng là `https://quangphuc.id.vn/verify/{token}`. Trạng thái luôn được đọc từ database, không suy ra từ nội dung QR.

## API quản trị

| Method | Endpoint | Mục đích |
| --- | --- | --- |
| GET/POST | `/api/v1/admin/courses` | Danh sách/tạo khóa học |
| PATCH | `/api/v1/admin/courses/{id}` | Gán template hoặc cập nhật khóa học |
| GET/POST | `/api/v1/admin/courses/{id}/lessons` | Danh sách/tạo bài học |
| GET/POST | `/api/v1/admin/exams` | Danh sách/tạo bài thi |
| GET | `/api/v1/admin/exam-results` | Kết quả thi toàn hệ thống |
| GET | `/api/v1/admin/exam-answers/pending` | Câu tự luận chờ chấm |
| POST | `/api/v1/admin/exam-answers/{id}/review` | Chấm câu tự luận |
| GET | `/api/v1/admin/certificates` | Danh sách chứng chỉ |
| POST | `/api/v1/admin/certificates/{id}/revoke` | Thu hồi và ghi audit |
| GET | `/api/v1/admin/certificate-statistics` | Thống kê tổng quan |
| GET/POST | `/api/v1/admin/certificate-templates` | Danh sách/tạo template |
| POST | `/api/v1/admin/certificate-templates/{id}/assets/{logo\|background}` | Upload ảnh template, tối đa 5 MB |

Tất cả route `/admin` yêu cầu role `admin`; chấm tự luận cho phép `mentor` hoặc `admin`.

## Giao diện

- `/certifications`: danh sách bài thi và chứng chỉ của người học.
- `/certifications/exams/{id}`: làm bài có countdown và chống nộp thiếu.
- `/verify/{token}`: xác minh công khai, responsive.
- `/admin/certifications`: thống kê, chứng chỉ, thu hồi và template.
- `/admin/certifications/setup`: tạo course, lesson, exam và gán template.
- `/admin/questions`: ngân hàng câu hỏi một đáp án, nhiều đáp án, Đúng/Sai và tự luận.
- `/admin/certifications/templates/new`: editor màu sắc, font, logo, nền, vị trí chữ ký/QR và preview A4.

## Cài đặt và deploy

```bash
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m pytest -q -p no:cacheprovider
```

Reverse proxy cần chuyển `/api/*` về backend và các route còn lại về frontend. TLS phải được bật cho `quangphuc.id.vn`; không public volume `certificate_storage`. Sao lưu đồng thời PostgreSQL và volume này để dữ liệu chứng chỉ và PDF nhất quán.

## Kiểm thử thủ công

1. Admin mở `/admin/questions`, tạo câu hỏi thật; đáp án đúng không xuất hiện trong API người học.
2. Admin mở `/admin/certifications/setup`, tạo course, lesson và exam rồi chọn template.
3. Candidate mở `/certifications`, đăng ký khóa học, xem lesson, bắt đầu và nộp bài.
4. Xác nhận điểm không thể sửa từ DevTools vì payload chỉ chứa đáp án.
5. Khi đạt, tải PDF và quét QR bằng iPhone/Android.
6. Admin thu hồi; mở lại cùng QR phải thấy `REVOKED`.
7. Thử tải PDF bằng tài khoản khác phải nhận `403`.

PDF hiện dùng vector text và font DejaVu Sans để hỗ trợ tên tiếng Việt dài. QR xác minh trạng thái database; nếu cần bảo đảm tính toàn vẹn mật mã của chính file PDF, bước production tiếp theo là ký số PDF bằng chứng thư số của đơn vị phát hành.
