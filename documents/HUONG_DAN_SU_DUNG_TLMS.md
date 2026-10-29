# HUONG DAN SU DUNG VA VAN HANH TLMS

> Phien ban tai lieu: 1.0  
> Ngay kiem tra gan nhat: 28/10/2026  
> Pham vi: TLMS production va moi truong local hien tai  
> Luu y: tai lieu nay khong chua mat khau, API key, access token hay du lieu ca nhan.

## 1. Tong quan

TLMS (T&A Lab Management System) ho tro quan ly va phat trien thanh vien lab thong qua:

- tai khoan va phan quyen mot vai tro chinh;
- bai danh gia nang luc dau vao va cau hoi thich nghi;
- lo trinh hoc tap, task, Daily Quest va Limit Quest;
- AI tao Daily Quest va cham minh chung;
- lich hoc/lich lam, diem chuyen can va tien do thanh vien;
- XP, level, thanh tich, huy hieu, bang xep hang va tranh cup;
- khoa hoc, bai thi va chung chi so co trang xac minh cong khai;
- ket noi Zalo OA theo feature flag (mac dinh co the tat hoac chay mock).

## 2. Dia chi truy cap

### Production dang hoat dong

| Thanh phan | Dia chi |
|---|---|
| Web TLMS | <https://tlms-production.vercel.app> |
| Dang nhap | <https://tlms-production.vercel.app/login> |
| Backend API | <https://tlms-api.onrender.com> |
| Swagger | <https://tlms-api.onrender.com/docs> |
| OpenAPI JSON | <https://tlms-api.onrender.com/openapi.json> |
| Health check | <https://tlms-api.onrender.com/health> |

Ten mien du kien:

- Web: `https://quangphuc.id.vn`
- API: `https://api.quangphuc.id.vn`

Hai ten mien tren chi hoat dong sau khi DNS tai nha cung cap ten mien duoc tro dung ve Vercel va Render. Trong thoi gian DNS chua cap nhat, dung URL `vercel.app` va `onrender.com` trong bang tren.

### Local

| Thanh phan | Dia chi |
|---|---|
| Frontend | <http://localhost:3000> |
| Backend | <http://localhost:8000> |
| Swagger | <http://localhost:8000/docs> |
| ReDoc | <http://localhost:8000/redoc> |
| PostgreSQL tu may host | `localhost:5434` |

## 3. Khoi dong va dung local

Tai thu muc goc `P:\tlms`:

```powershell
docker compose up -d --build
docker compose ps
docker compose logs --tail 200 backend
docker compose logs --tail 100 frontend
```

Chay migration:

```powershell
docker compose exec backend alembic upgrade head
```

Dung he thong, khong xoa du lieu:

```powershell
docker compose down
```

Khong them `-v` neu muon giu database va tep trong Docker volume.

## 4. Dang ky va dang nhap

### Dang ky

1. Mo trang `/register`.
2. Nhap email hop le, mat khau toi thieu 6 ky tu, so dien thoai, ho va ten.
3. Gui dang ky.
4. Sau khi dich vu S4H chap nhan, quay ve `/login` de dang nhap.

So dien thoai la bat buoc. Thong bao `Phone cannot be empty` co nghia form hoac request khong gui truong `phone`.

### Dang nhap

1. Mo `/login`.
2. Nhap email va mat khau cua tai khoan S4H.
3. TLMS gui thong tin dang nhap den S4H Auth va dong bo user ve PostgreSQL.
4. Neu dang nhap thanh cong, he thong dieu huong den dashboard phu hop voi vai tro.

Tai khoan seed local chi dang nhap duoc khi quan tri vien bat `DEV_AUTH_FALLBACK_ENABLED` va cau hinh mat khau fallback. Khong dung fallback nhu co che dang nhap cong khai lau dai.

## 5. Vai tro va quyen

Moi tai khoan chi duoc co **mot vai tro chinh**:

| Vai tro | Muc dich | Quyen chinh |
|---|---|---|
| `candidate` | Thuc tap sinh | Lam baseline, Daily Quest, task, xem lo trinh |
| `member` | Thanh vien | Lam task, quest, phat trien thanh vien, cup, chung chi |
| `mentor` | Nguoi huong dan | Tao/quan ly task, xem bai nop, theo doi thanh vien |
| `admin` | Quan tri vien | Quan ly user, phan quyen, Limit Quest, cau hinh he thong |

Quy tac quan trong:

- candidate/member khong duoc tu chuyen sang mentor/admin;
- mentor/admin khong tham gia tranh cup cua nguoi hoc;
- admin phan vai tro tai `/admin/users`, chi chon mot quyen roi luu;
- thay doi role phai duoc kiem tra o backend, khong chi dua vao giao dien;
- level duoc tinh tu XP, khong duoc nhap tay de tao level 99 khong hop le.

## 6. Luong dau tien cua candidate/member

### Buoc 1: Hoan thanh baseline

1. Mo `/candidate/questions`.
2. He thong uu tien toi da 5 cau baseline chua tra loi.
3. Tra loi bang noi dung cua minh hoac chon dap an neu la trac nghiem.
4. Ket qua duoc cham va ghi vao ho so ky nang.

Sau baseline, he thong phan loai do kho muc tieu:

- diem trung binh duoi 50: do kho muc tieu khoang 3/10;
- tu 50 den duoi 80: khoang 5/10;
- tu 80 tro len: khoang 7.5/10.

He thong sau do uu tien cau hoi gan do kho muc tieu va thuoc nhom ky nang yeu.

### Buoc 2: Xem dashboard

Tai `/dashboard`, nguoi dung xem:

- level va tien do len cap;
- XP hien tai;
- diem ky luat/chuyen can;
- vai tro duy nhat;
- Daily Task hom nay;
- score thanh vien, reliability va thong bao;
- lien ket den nhiem vu, phat trien thanh vien va cac module khac.

### Buoc 3: Cap nhat ho so

Tai `/profile`, kiem tra ten, email, MSSV, minh chung va thong tin cong khai. MSSV chi dong bo lich LHU khi:

- MSSV ton tai va dung dinh dang;
- backend co quyen truy cap API/co so du lieu LHU;
- mang hoac VPN noi bo cho phep ket noi;
- tai khoan LHU khop voi thanh vien TLMS.

## 7. Lo trinh hoc tap va quest

Mo `/candidate`. Cac tab chinh gom:

### Daily Quest

- Mac dinh toi da 5 quest trong mot cua so ngay.
- Reset luc 00:00 theo gio Viet Nam neu `DAILY_QUEST_RESET_HOUR=0`.
- Quest cu chua dat se het han, khong cong XP.
- He thong khong sinh them neu da du gioi han hoac da hoan thanh ca bo trong ngay.
- Noi dung duoc sinh tu level, XP, task/ky nang da hoan thanh va lo trinh.
- Neu AI loi, he thong dung quest template de khong de danh sach rong.

Cach nop:

1. Bam vao o quest de xem chi tiet.
2. Doc tieu de, mo ta, do kho, XP va han nop.
3. Nhap ghi chu, link va/hoac tai anh minh chung.
4. Bam `Nop minh chung`.
5. Cho AI tra diem, phan hoi va trang thai.

Nguong dat mac dinh la 70/100. Neu dat, quest chuyen `completed`, XP chi cong mot lan va level duoc tinh lai.

### Limit Quest

- Chi admin tao va giao cho candidate/member.
- Dung cho coaching 1:1, hop offline hoac su kien gioi han.
- Bat buoc co anh minh chung.
- Co deadline rieng va XP rieng.
- AI cham minh chung theo noi dung quest; khong dat thi can nop minh chung ro hon.

### Co the lam

Day la task phu hop role, level va pham vi nguoi dung. Task opt-in can bam nhan truoc khi bat dau; task bat buoc co the duoc giao truc tiep.

### Tasks cua toi

Hien thi task da nhan/duoc giao, trang thai, tien do, minh chung, AI score, manager score va final score neu co.

## 8. AI cham diem

### Quest

AI nhan cac thong tin:

- loai quest, tieu de, mo ta, do kho, XP va nguong dat;
- level, XP va role cua nguoi nop;
- ghi chu, link, URL anh va co/khong co anh.

AI tra JSON gom `score`, `feedback`, `passed`. Backend ep diem vao 0-100 va chi cho qua khi diem dat nguong. Neu provider tam loi, backend co rule fallback; phan hoi se noi ro da dung fallback.

### Cau hoi tu luan

AI cham theo dap an mong doi va cac nhom khai niem chap nhan, tra:

- diem 0-100;
- nhan xet;
- diem tin cay;
- breakdown: correctness, understanding, reasoning, application;
- y manh va y con thieu.

Khi AI khong san sang, bo cham local dua tren do phu khai niem duoc dung voi confidence thap. Ket qua AI nen la danh gia hinh thanh; bai quan trong can co mentor/admin xem lai.

## 9. Task thuong

### Nguoi hoc

1. Mo task trong `Co the lam` hoac `Tasks cua toi`.
2. Nhan task neu task cho phep opt-in.
3. Bat dau va cap nhat tien do.
4. Nop ghi chu, link va minh chung.
5. Xem AI score/feedback.
6. Cho mentor/manager duyet neu task yeu cau review.

### Mentor

1. Mo `/mentor/tasks` de xem danh sach task.
2. Mo `/mentor/tasks/create` de tao task moi.
3. Chon loai task, pham vi, do kho, XP, level toi thieu va doi tuong.
4. Kiem tra task da xuat hien cho dung member.
5. Mo bai nop de danh gia, nhap manager score va feedback.

Khi tao task, can chon dung pham vi:

- bat buoc cho toan bo doi tuong;
- dang ky/opt-in;
- rieng tu cho user duoc chi dinh.

## 10. Lich va chuyen can

Mo `/schedule`:

1. Kiem tra MSSV.
2. Bam cap nhat/dong bo LHU khi can.
3. Chuyen tuan bang nut mui ten.
4. Xem ca sang, chieu, toi va trang thai nghi.

Manager xem tong quan tai `/manager/overview` va lich tung nguoi. Neu lich rong:

- kiem tra khoang ngay dang xem;
- kiem tra MSSV;
- kiem tra bien `LHU_API_BASE_URL` va credential LHU;
- kiem tra VPN/mang noi bo;
- xem log backend de phan biet `401/403`, timeout hay du lieu rong.

## 11. Phat trien thanh vien

Mo `/member/development` hoac dashboard manager tuong ung. He thong tong hop:

- lo trinh 8 tuan;
- task va tien do theo ngay/tuan;
- diem bai nop;
- attendance, discipline, reliability;
- kha nang thang cap.

Promotion chi nen duoc duyet khi cac nguong da dat va manager xac nhan. Khong su dung mot chi so duy nhat de quyet dinh.

## 12. Thanh tich va huy hieu

Mo `/achievements`. Moi huy hieu hien:

- ten ngan;
- mo ta dieu kien;
- gia tri hien tai/muc tieu;
- phan tram tien do;
- trang thai khoa/mo;
- thoi diem dat neu da mo.

Huy hieu duoc tinh tu XP, level, task, Core Task, baseline, cau hoi, Daily Quest, Limit Quest, minh chung va chuyen can.

## 13. Tranh cup thu 6

Mo `/cups`.

Quy tac:

- co 8 cup duy nhat, moi cup chi trao mot lan;
- su kien mo thu 6 theo gio Viet Nam;
- diem chuyen can/ky luat toi thieu 80%;
- candidate/member du dieu kien lam bai trac nghiem 20 cau;
- xep hang theo diem giam dan;
- neu bang diem, nguoi hoan thanh nhanh hon xep tren;
- neu van bang, thoi diem nop som hon duoc uu tien;
- cup chi trao sau khi cua so su kien dong.

Khong co nut nhan cup truoc thu 6. Neu giao dien hien su kien chua mo, cho dong ho den dung thoi gian.

## 14. Bang xep hang

Tai `/leaderboard`, xem XP, level, discipline va thu hang. Bang xep hang la cong cu tao dong luc, khong thay the danh gia chuyen mon cua mentor.

## 15. Khoa hoc, bai thi va chung chi

Nguoi hoc:

1. Mo `/certifications`.
2. Dang ky khoa hoc/bai thi dang cong khai.
3. Bat dau bai thi trong so lan cho phep.
4. Tra loi va nop truoc khi het thoi gian.
5. Xem ket qua sau khi cac cau tu luan duoc review.
6. Tai/xem chung chi neu dat nguong.

Admin:

- cau hinh khoa hoc, bai hoc va bai thi;
- duyet cau tu luan;
- quan ly mau chung chi;
- xem thong ke, thu hoi chung chi khi co ly do;
- dung audit log de truy vet thay doi.

Trang `/verify/{token}` cho phep xac minh cong khai ma chung chi, co rate limit de han che lam dung.

## 16. Zalo Daily Task Quiz

Module Zalo co feature flag. Khi `ZALO_INTEGRATION_ENABLED=false`, TLMS van hoat dong binh thuong.

Nguoi dung tai `/zalo`:

1. Tao yeu cau lien ket.
2. Lam theo huong dan cua OA.
3. Dong y hoac tu choi nhan thong bao.
4. Tra loi A/B/C/D khi co phien quiz.
5. Dung link Web App de xem them task va tien do.

Admin tai `/admin/zalo`:

- bat/tat tich hop;
- xem provider `mock` hoac OA that;
- cau hinh lich gui/nhac;
- xem session va delivery log;
- retry thong bao loi theo chinh sach;
- theo doi token OA het han.

Khong dung Zalo ca nhan hay cong cu gui tin khong chinh thuc.

## 17. Quan tri nguoi dung

Tai `/admin/users`:

1. Tim user theo ten/email.
2. Loc theo role va trang thai.
3. Bam `Sua`.
4. Chon dung **mot** role.
5. Chon trang thai tai khoan.
6. Chon cap thanh vien neu nghiep vu yeu cau.
7. Luu va tai lai danh sach de xac nhan.

Khong cap admin cho tai khoan hoc vien chi de thu giao dien. Dung tai khoan test rieng va thu hoi quyen sau khi kiem tra.

## 18. Xu ly su co

### Web khong vao duoc

1. Mo truc tiep URL Vercel.
2. Kiem tra `https://tlms-api.onrender.com/health`.
3. Doi 30-90 giay neu Render free vua ngu dong.
4. Tai lai trang mot lan.
5. Kiem tra Vercel Deployment va Render Deploy status.

### Dang nhap 401

- kiem tra email/mat khau S4H;
- kiem tra S4H co truy cap duoc tu Render;
- khong mac dinh password local giong production;
- xem backend log de phan biet sai credential va S4H timeout.

### AI khong tao/cham quest

- kiem tra `AI_PROVIDER=gemini`;
- kiem tra `GEMINI_API_KEY` ton tai tren Render;
- kiem tra model `gemini-2.5-flash`;
- kiem tra quota/billing va HTTP `401/403/429`;
- xac nhan deploy moi da `live` sau khi thay env;
- xem feedback co noi he thong dang dung fallback hay khong.

### Upload mat sau deploy

Render free dung filesystem tam thoi. Neu `STORAGE_BACKEND=local`, file upload co the mat sau restart/deploy. Can bat bucket S3-compatible/R2 va cau hinh cac bien `S3_*` truoc khi dung production that.

### Domain chua hoat dong

Kiem tra DNS:

- apex `@` tro ve IP Vercel duoc cap;
- `www` CNAME ve target Vercel;
- `api` CNAME ve `tlms-api.onrender.com`;
- giu nguyen NS/MX/TXT neu khong co yeu cau thay doi;
- cho DNS propagate va kiem tra SSL tren hai nen tang.

## 19. Bao mat va du lieu

- Khong commit `.env`, API key, database URL co password hoac token.
- Khong gui key trong chat, anh chup, issue hay tai lieu.
- Key cu da tung lo qua anh nen phai rotate sau khi kiem tra on dinh.
- Chi admin/mentor duoc xem du lieu dung cho cong viec cua ho.
- Minh chung co du lieu ca nhan can private storage va signed URL.
- Log khong duoc ghi password, token day du hay noi dung nhay cam.
- Du lieu nghien cuu phai pseudonymize va co consent/IRB phu hop.

## 20. Checklist van hanh hang ngay

- [ ] Frontend va backend health tra 200.
- [ ] Deploy moi nhat o trang thai `live`/`ready`.
- [ ] Scheduler noi bo chay thanh cong.
- [ ] Daily Quest reset dung 00:00 GMT+7.
- [ ] Khong co dot bien HTTP 5xx.
- [ ] Gemini khong bi 401/403/429.
- [ ] Database migration dung revision mong doi.
- [ ] Storage persistent hoat dong truoc khi nhan file that.
- [ ] Sao luu database va thu phuc hoi dinh ky.

## 21. Ket qua kiem tra ngay 28/10/2026

| Hang muc | Ket qua |
|---|---|
| Frontend production | HTTP 200 |
| Backend health/docs/OpenAPI | HTTP 200 |
| Render deploy | Live, commit `02f3996` |
| Gemini key tren Render | Da cau hinh va goi `gemini-2.5-flash` thanh cong |
| Truy van DB cong khai | Endpoint verify tra 404 dung ky vong voi token gia, khong co 5xx |
| Backend tests | 34 passed |
| Frontend production build | Thanh cong, 31 route |
| TypeScript | Thanh cong |
| ESLint | 0 error, 102 warning |
| Local runtime log | Khong thay traceback/HTTP 5xx trong mau log kiem tra |

Ton tai can theo doi, chua sua do yeu cau khong thay doi code:

1. Pydantic dung `class Config` cu, tao deprecation warning khi nang len Pydantic v3.
2. Frontend con warning `any`, React Hook dependency, unused import/variable va `<img>`.
3. File upload production dang can object storage persistent.
4. Dang nhap seed local khong phai credential production; bai test 401 khong ket luan S4H bi loi.
5. Custom domain can hoan tat DNS.
6. Render free co cold start; request dau tien co the cham.

