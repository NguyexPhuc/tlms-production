# TLMS - Zalo Daily Task Quiz

## 1. Pham vi module

Module cho phep thanh vien:

- Tu nguyen lien ket tai khoan TLMS voi Zalo OA va bat/tat nhan thong bao.
- Nhan mot cau hoi A/B/C/D tai mot thoi diem, tra loi bang ky tu A, B, C hoac D.
- Duoc cham diem quyet dinh theo `correct_option`, luu dap an, cap nhat skill profile va XP bang service cau hoi hien co.
- Nhan cau tiep theo sau khi tra loi; tin nhan luon kem lien ket Web App TLMS.

Admin co the bat/tat module, chon mock/OA, cau hinh gio gui, gio nhac, so cau, thoi han va so lan retry tai `/admin/zalo`.

## 2. Ket qua phan tich TLMS

- Backend: FastAPI, SQLAlchemy async, PostgreSQL, Alembic, APScheduler.
- Frontend: Next.js App Router, TypeScript, Tailwind CSS, Axios.
- Authentication: JWT cua S4H, co local development fallback; RBAC duoc tai su dung qua `get_current_user` va `require_admin`.
- Ngan hang cau hoi: `Question`; dap an va logic XP hien co: `UserQuestionAnswer` va `QuestionService`.
- Scheduler: APScheduler chay theo gio Viet Nam; job Zalo kiem tra cau hinh runtime moi phut.

## 3. File duoc them

- `backend/app/models/zalo.py`
- `backend/app/schemas/zalo.py`
- `backend/app/services/zalo_adapter.py`
- `backend/app/services/zalo_quiz.py`
- `backend/app/api/routes/zalo.py`
- `backend/alembic/versions/024_zalo_daily_task_quiz.py`
- `backend/tests/test_zalo_quiz.py`
- `frontend/src/types/zalo.ts`
- `frontend/src/app/zalo/page.tsx`
- `frontend/src/app/admin/zalo/page.tsx`
- `documents/ZALO_DAILY_TASK_QUIZ.md`

## 4. File bat buoc da chinh sua

- `backend/app/models/development.py`: bo sung options va correct option cho cau trac nghiem.
- `backend/app/models/__init__.py`: dang ky model Zalo cho SQLAlchemy.
- `backend/app/schemas/question.py`: mo rong schema cau hoi trac nghiem.
- `backend/app/services/question.py`: seed ngan hang A/B/C/D va tai su dung logic dap an/XP.
- `backend/app/api/routes/__init__.py`: gan router `/api/v1/zalo`.
- `backend/app/services/background_tasks.py`: them job dispatch, nhac, het han va retry.
- `backend/app/core/config.py`, `.env.example`, `backend/.env.example`, `docker-compose.yml`: khai bao bien moi truong.
- `backend/requirements.txt`: dependency test.
- `frontend/src/lib/api.ts`: API client Zalo.
- `frontend/src/app/dashboard/page.tsx`: lien ket den trang thanh vien va trang admin Zalo.

## 5. Database

Migration `024_zalo_daily_quiz` chi them cot/bang, khong xoa du lieu cu:

- `questions.options`, `questions.correct_option`
- `zalo_integration_configs`
- `zalo_user_links`
- `zalo_quiz_sessions`
- `zalo_quiz_items`
- `zalo_notification_logs`
- `zalo_webhook_events`

Webhook chi luu hash sender va digest payload de chong trung; khong luu raw webhook co du lieu ca nhan.

## 6. Doi chieu Zalo OA

Implementation hien tai chi dung cac thanh phan duoc mo ta trong tai lieu OA chinh thuc:

- Gui tin tu van dang van ban: `POST https://openapi.zalo.me/v3.0/oa/message/cs`, token trong header, body gom `recipient.user_id` va `message.text`.
- Webhook xac thuc `X-ZEvent-Signature` bang SHA-256 cua app ID, raw JSON, timestamp va OA secret key.
- Refresh token tai OAuth v4, secret key nam trong header.
- Dieu kien gui duoc kiem tra theo consent, trang thai lien ket va lan tuong tac gan nhat. Quyen gui that van phu thuoc goi dich vu, phe duyet va chinh sach hien hanh cua OA.

Module khong gia dinh OA co interactive button. Cau hoi duoc gui duoi dang text A/B/C/D, kem URL Web App, la dinh dang an toan nhat de mock va doi chieu quyen OA thuc te.

Tai lieu tham khao:

- https://docs.zaloplatforms.com/docs/OA
- https://docs.zaloplatforms.com/docs/OA/tin-nhan/tin-tu-van/gui-tin-tu-van-dang-van-ban
- https://oa.zalo.me/home/documents/vie/guides/tong-quan-cac-loai-tin-nhan-tren-zalo-official-account-_3651713298729094511

## 7. Bien moi truong

```env
ZALO_INTEGRATION_ENABLED=false
ZALO_PROVIDER=mock
ZALO_APP_ID=
ZALO_APP_SECRET=
ZALO_OA_ID=
ZALO_OA_SECRET_KEY=
ZALO_OA_ACCESS_TOKEN=
ZALO_OA_REFRESH_TOKEN=
ZALO_OA_SEND_URL=https://openapi.zalo.me/v3.0/oa/message/cs
ZALO_OA_TOKEN_URL=https://oauth.zaloapp.com/v4/oa/access_token
ZALO_WEB_APP_URL=https://quangphuc.id.vn
ZALO_LINK_TOKEN_MINUTES=15
ZALO_WEBHOOK_MAX_SKEW_SECONDS=300
```

Secret/token chi dien trong `.env` cua server hoac secret manager. Khong commit `.env`.

## 8. Chay mock

```powershell
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m pytest -q -p no:cacheprovider tests/test_zalo_quiz.py
```

1. Dat `ZALO_INTEGRATION_ENABLED=true`, `ZALO_PROVIDER=mock` trong `.env` va recreate backend.
2. Admin mo `/admin/zalo`, bat cau hinh va bam `Gui ngay`.
3. Thanh vien mo `/zalo`, dong y va tao lien ket. Mock se lien ket ngay.
4. Admin co the goi endpoint `POST /api/v1/zalo/admin/mock-message` de gia lap dap an.

## 9. Chuyen sang Zalo OA that

1. Tao/xac minh Zalo OA va ung dung tren Zalo for Developers.
2. Lien ket ung dung voi OA va xin dung cac API tin nhan can thiet.
3. Dien credentials vao secret store cua server.
4. Cau hinh callback HTTPS: `https://quangphuc.id.vn/api/v1/zalo/webhook`.
5. Dang ky su kien tin nhan nguoi dung gui den OA.
6. Dat `ZALO_PROVIDER=zalo_oa`, recreate backend, sau do doi Provider va bat module tai `/admin/zalo`.
7. Thu voi mot tai khoan noi bo: vao `/zalo`, nhan ma, quan tam OA va gui `TLMS LINK <ma>`.
8. Kiem tra `Lich su gui`, log backend va quota/quyen gui tren trang quan tri OA truoc khi mo rong.

Adapter se refresh access token mot lan khi gap loi token va dua loi gui vao hang retry. Token moi chi duoc giu trong memory; khi van hanh lau dai nen cap nhat token da rotate vao secret manager cua he thong trien khai.

## 10. Cau hinh domain

`quangphuc.id.vn` can tro DNS toi may chu/reverse proxy dang chay TLMS. Reverse proxy can:

- Terminate HTTPS bang certificate hop le.
- Forward `/api/*` va `/uploads/*` qua Next.js proxy hien co, hoac forward truc tiep dung path toi backend.
- Forward cac header webhook nguyen ven, dac biet `X-ZEvent-Signature`.
- Khong cache `POST /api/v1/zalo/webhook`.

Sau khi DNS va HTTPS hoat dong, xac nhan:

```text
https://quangphuc.id.vn/zalo
https://quangphuc.id.vn/admin/zalo
https://quangphuc.id.vn/api/v1/zalo/webhook
```

## 11. An toan va rollback

- Tat ngay module: dat `ZALO_INTEGRATION_ENABLED=false` va recreate backend, hoac tat `Trang thai` tai trang admin.
- Khong dung Zalo ca nhan, automation browser hoac endpoint khong chinh thuc.
- One-time link code duoc hash va het han; mot Zalo UID khong the lien ket voi hai user active.
- Delivery va webhook co idempotency key de tranh gui/xu ly trung.
- Session het han khong nhan dap an/XP; completion bonus chi ap dung mot lan.
- Migration downgrade chi xoa cac bang/cot cua module; production can backup truoc khi downgrade.
