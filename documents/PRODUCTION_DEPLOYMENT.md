# TLMS Production Deployment

Tai lieu nay mo ta cau hinh production da duoc chuan bi cho `quangphuc.id.vn`.
Khong dat gia tri secret vao repository, issue, pull request hoac chat.

## Kien truc

- Frontend: Next.js tren Vercel, domain `https://quangphuc.id.vn` va `https://www.quangphuc.id.vn`.
- Backend: FastAPI Docker Free Web Service tren Render, domain `https://api.quangphuc.id.vn`.
- Scheduler: GitHub Actions goi endpoint noi bo co khoa rieng, timezone `Asia/Ho_Chi_Minh`.
- Database: Neon PostgreSQL Free, connection TLS va scale-to-zero.
- Object storage: Cloudflare R2 private bucket qua S3 API. Backend proxy anh minh chung va kiem soat tai certificate.
- CI/CD: `.github/workflows/ci.yml`; Render chi deploy khi checks pass, Vercel deploy tu GitHub Actions sau CI.

Khong phat hien WebSocket trong source hien tai. Upload file vat ly hien co gom anh minh chung quest,
certificate PDF, logo va background cua certificate template. Cac truong avatar/tai lieu khac hien chi luu URL,
khong co upload binary rieng trong backend.

## Lenh da xac minh

```bash
# Local Docker
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m pytest -q

# Frontend
cd frontend
npm ci
npm run lint
npm run build

# Backend container commands
/app/entrypoint.sh              # migrate, then start Uvicorn with $PORT
python -m app.worker            # dedicated scheduler process
```

## Environment checklist

### Vercel

- Root Directory: `frontend`
- Framework: Next.js
- Install: `npm ci`
- Build: `npm run build`
- Production branch: `main`
- `NEXT_PUBLIC_API_URL=/api`
- `BACKEND_URL=https://api.quangphuc.id.vn`

GitHub Actions secrets: `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`.
Sau khi ba secret da san sang, tao repository variable `PRODUCTION_DEPLOY_ENABLED=true`.
Tat Git auto-deploy cua Vercel de tranh deploy truoc CI; workflow se build va deploy production.

### Render Free

Import Blueprint tu `render.yaml`. Cac gia tri co `sync: false` phai nhap trong Render Dashboard:

- `DATABASE_URL`: pooled connection string cua Neon Free
- `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`
- `S4H_AUTH_BASE_URL`
- `LHU_MYSQL_HOST`, `LHU_MYSQL_USER`, `LHU_MYSQL_PASSWORD`, `LHU_MYSQL_DATABASE`
- `MONGODB_CONNECTION_STRING`
- Mot trong cac AI key phu hop provider: `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `AI_API_KEY`
- Zalo credentials neu bat tich hop: `ZALO_APP_ID`, `ZALO_APP_SECRET`, `ZALO_OA_ID`,
  `ZALO_OA_SECRET_KEY`, `ZALO_OA_ACCESS_TOKEN`, `ZALO_OA_REFRESH_TOKEN`

`DEV_AUTH_FALLBACK_ENABLED=false` tren production. Khong dat mat khau local lam co che dang nhap production.
Blueprint tu tao `DEV_AUTH_SECRET_KEY`, `USER_IMPORT_SECRET_TOKEN` va `WEBHOOK_API_KEY`.
Blueprint cung tao `SCHEDULER_API_KEY`; sao chep gia tri nay vao GitHub Actions secret cung ten.

### GitHub scheduled jobs

- Repository variable: `TLMS_API_BASE_URL=https://api.quangphuc.id.vn`
- Repository secret: `SCHEDULER_API_KEY`, trung voi gia tri tren Render
- Workflow: `.github/workflows/scheduled-jobs.yml`
- Daily Quest: 00:07 moi ngay
- Dong bo lich: 00:13 thu Hai
- Weekly Cup: 00:19 thu Sau
- Zalo poll/retry: moi 15 phut

Endpoint scheduler khong hien trong Swagger va yeu cau header `X-Scheduler-Key`.

### Cloudflare R2

1. Tao private Standard bucket, vi du `tlms-production`.
2. Tao API token chi co Object Read/Write tren dung bucket.
3. Lay S3 endpoint chinh xac tu R2 Dashboard va dien cac bien `S3_*` tren Render.
4. Khong bat public development URL cho bucket. File duoc doc qua backend.
5. Cau hinh lifecycle/retention theo chinh sach du lieu cua lab.

## Neon Free database va du lieu

Blueprint khong drop/reset schema. Web service chay `alembic upgrade head` truoc khi khoi dong API.
Neon connection string duoc chuyen an toan sang SQLAlchemy asyncpg va bat TLS.

Neu can mang database local len production:

1. Dung ghi du lieu trong mot cua so bao tri ngan.
2. Tao `pg_dump` dang custom va ma hoa ban backup.
3. Restore vao Neon database rong bang connection string duoc tao rieng.
4. Chay `alembic upgrade head`.
5. Doi soat count cac bang quan trong: users, tasks, user_tasks, daily_quests, schedules,
   notifications, courses, exams, certificates.
6. Rotate password database sau khi restore neu connection string tung duoc dung ngoai dashboard bao mat.

Khong restore du lieu demo hoac tai khoan test len production. Neon Free co 1 GB storage/project,
100 CU-hours/project, scale-to-zero sau 5 phut, history 6 gio va mot manual snapshot. Free tier khong co SLA;
can tao `pg_dump` ma hoa dinh ky neu du lieu quan trong.

## DNS Mat Bao

Snapshot ngay 2026-10-27:

- Nameserver: `ns1.matbao.vn`, `ns2.matbao.vn`
- Apex A hien tai: `13.67.69.121`
- MX: `s129d209.emailserver.vn`
- SPF TXT dang ton tai va phai duoc giu nguyen

Chi cap nhat sau khi Vercel va Render da tao project/service va hien thi record can thiet:

| Host | Type | Value |
| --- | --- | --- |
| `@` | Theo Vercel Domain Inspect | Lay chinh xac tu project Vercel |
| `www` | Theo Vercel Domain Inspect | Lay chinh xac tu project Vercel |
| `api` | CNAME | Lay chinh xac tu Custom Domains cua Render |

Khong doi nameserver va khong xoa MX/TXT/SPF/DKIM/DMARC. Sau khi nhap record, kiem tra bang
`Resolve-DnsName`, dashboard cua hai provider, sau do kiem tra TLS tren ba hostname.

## CI/CD va rollback

- Moi push/PR chay Alembic tren PostgreSQL 16, 34 backend tests, ESLint va Next production build.
- Render `autoDeployTrigger: checksPass`, nen chi build release sau khi GitHub checks thanh cong.
- Vercel job chi chay tren `main`, sau hai job CI va khi `PRODUCTION_DEPLOY_ENABLED=true`.
- Workflow scheduled jobs chay doc lap voi request retry; business service phia backend van dam bao idempotent.
- Rollback frontend: Promote deployment tot truoc do trong Vercel.
- Rollback backend: Rollback deployment trong Render. Migration database chi duoc rollback sau khi
  review migration cu the va co backup; khong tu dong chay `alembic downgrade`.
- Neu release co schema moi khong backward-compatible, dung deployment, restore PITR vao database moi,
  doi connection string, kiem tra roi moi chuyen traffic.

## Chi phi free tier

Gia tham khao tai ngay 2026-10-28:

- Render Free Web Service: 0 USD trong 750 instance-hours/workspace/thang.
- Neon Free PostgreSQL: 0 USD trong gioi han free plan.
- Cloudflare R2 Standard: thuong 0 USD khi nam trong free tier 10 GB; vuot muc 0.015 USD/GB-thang
  va phi operations.
- Vercel Hobby: 0 USD, chi danh cho personal/non-commercial va ung dung quy mo nho.
- GitHub Actions tren public repository: workflow scheduler nhe, khong co worker thuong truc.
- AI, Zalo va cac external API: tinh rieng theo tai khoan/provider.

Tong hosting muc tieu: `0 USD/thang` neu khong vuot free tier va du an du dieu kien Vercel Hobby.
AI/Zalo co the phat sinh phi rieng; fallback template van hoat dong khi AI khong kha dung.

## Gioi han bat buoc cua ban free

- Render tu spin down sau 15 phut khong co request; request dau tien co the cho khoang mot phut.
- Render local filesystem bi xoa khi restart/spin down, nen moi file quan trong phai nam trong R2.
- Render Free khong co background worker. GitHub Actions thay the scheduler bang callback co khoa.
- GitHub schedule co the bi tre hoac drop khi tai cao; public repository bi tat schedule sau 60 ngay
  khong co hoat dong.
- Neon scale-to-zero sau 5 phut va khong co uptime SLA tren Free plan.
- Vercel Hobby chi cho personal/non-commercial. Neu TLMS duoc dung thuong mai phai doi goi.
- Day la ban free-tier public preview, khong duoc mo ta la production co SLA.

## Production smoke test

Chi danh dau production RUNNING sau khi tat ca muc sau pass tren domain that:

- `GET https://api.quangphuc.id.vn/health`, `/docs`, `/redoc`
- Trang login/register va role redirect
- Dashboard candidate/member/mentor/admin
- Tao task, giao task, nop va review minh chung
- Daily Quest reset, AI generation/grading va XP/level
- Lich LHU va notification
- Zalo mock/real theo feature flag va quyen OA
- Quiz, certificate PDF download va public QR verification
- Upload anh, redeploy backend, sau do doc lai anh de xac nhan persistence
- Desktop/mobile, browser console, CORS, TLS va redirect HTTP sang HTTPS

## Bao mat can xu ly

Repository truoc day tung chua credential MongoDB/LHU va import token trong file tracked. Ban source hien
tai da loai cac gia tri do, nhung Git history van co the con luu. Phai rotate toan bo credential lien quan
truoc khi production va can nhac xoa secret khoi Git history bang quy trinh co review rieng.
