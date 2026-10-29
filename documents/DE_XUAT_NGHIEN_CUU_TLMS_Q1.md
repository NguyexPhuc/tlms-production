# DE XUAT NGHIEN CUU VA KHUNG BAI BAO Q1 TU HE THONG TLMS

> Phien ban: 1.0  
> Ngay doi chieu he thong va tai lieu: 28/10/2026  
> Trang thai: de cuong nghien cuu, chua phai ban thao da co ket qua thuc nghiem  
> Nguyen tac: khong tuyen bo Q1 neu chua doi chieu Scopus/JCR tai nam nop bai.

## 1. Ten de tai de xuat

### Tieng Viet

Khung hoc tap thich nghi va danh gia minh chung bang AI cho dao tao ky nang cong nghe thong tin trong phong lab.

### Tieng Anh

**An Adaptive AI-Orchestrated Learning and Evidence Assessment Framework for Laboratory-Based Software Engineering Training**

Ten ngan de tham khao:

- TLMS-AI: Adaptive Quest Generation and Evidence-Aware Assessment;
- AQUEST: Adaptive Quest and Evidence Scoring for Software Engineering Training;
- Human-Governed AI Assessment in Lab-Based Technical Learning.

## 2. Canh bao ve muc tieu Q1

Mot san pham phan mem hoat dong tot chua du de thanh bai bao Q1. Dong gop phai duoc bien thanh cau hoi nghien cuu, thuat toan co the lap lai, bo du lieu, doi chung, thuc nghiem, phan tich thong ke, danh gia fairness va thao luan gioi han.

Quartile thay doi theo:

- nam danh gia;
- co so du lieu Scopus/SJR hay Web of Science/JCR;
- category cua tap chi;
- loai tai lieu va thoi diem nop.

Truoc khi nop, tac gia phai kiem tra lai Scopus Sources va Clarivate Journal Citation Reports bang ISSN. Khong dua vao mot trang tong hop duy nhat.

## 3. Khoang trong nghien cuu

Cac LMS truyen thong thuong tach roi bon van de:

1. giao nhiem vu ca nhan hoa;
2. danh gia minh chung thuc hanh;
3. cap nhat mo hinh nang luc sau moi hoat dong;
4. duy tri dong luc va ky luat trong dao tao lab.

TLMS co the duoc nghien cuu nhu mot vong lap kin:

`learner state -> adaptive task/question -> evidence -> AI/human assessment -> state update -> next intervention`.

Khoang trong co the khai thac:

- thieu nghien cuu thuc dia ve LLM tao micro-task dua tren learner state trong dao tao software engineering;
- diem AI cho minh chung thuong thieu co che confidence, fallback va human oversight;
- gamification hay duoc danh gia rieng le, it gan voi adaptive assessment va attendance;
- du lieu private don vi nho kho tai lap, can protocol va schema de so sanh da co so;
- can danh gia khong chi do chinh xac diem, ma ca learning gain, workload, fairness va calibration.

## 4. Dong gop khoa hoc co the cong bo

### C1. Mo hinh dieu phoi hoc tap thich nghi da tin hieu

Mo hinh ket hop level, XP, lich su task, ky nang, baseline, lo trinh va do kho muc tieu de chon quest/cau hoi tiep theo. Diem moi khong nam o viec goi LLM, ma o pipeline co rang buoc, fallback va learner-state update.

### C2. Danh gia minh chung lai AI-rule-human

De xuat co che cham gom:

- LLM semantic/rubric scoring;
- rule fallback khi provider loi;
- confidence va nguong auto-pass;
- mentor review cho truong hop quan trong/khong chac chan;
- audit trail cho score va feedback.

Dong gop can duoc danh gia bang agreement voi nhieu giam khao con nguoi, calibration va subgroup fairness.

### C3. Chon cau hoi thich nghi dua tren nang luc va diem yeu

Sau 5 cau baseline, he thong uoc luong do kho muc tieu va xep hang cau hoi theo:

1. ky nang yeu nhat;
2. khoang cach giua do kho item va do kho muc tieu;
3. thoi gian tao de tie-break.

Co the nang thanh mo hinh IRT/Bayesian Knowledge Tracing trong nghien cuu mo rong va so sanh voi heuristic hien tai.

### C4. Co che gamification co dieu kien hoc tap

XP, level, badge, quest va cup duoc gan voi learning evidence va chuyen can. Cup khong duoc nhan truc tiep: nguoi hoc phai dat chuyen can >=80%, lam bai 20 cau trong thu 6; xep hang theo diem, sau do thoi gian.

### C5. Learning analytics cho dao tao lab 8 tuan

TLMS tao du lieu doc theo thoi gian ve task completion, score, attendance, discipline, reliability, skill mastery va promotion. Dong gop co the la mo hinh du bao nguy co cham tien do hoac kha nang thang cap, neu co du lieu du lon va tranh data leakage.

### C6. Kien truc trien khai an toan va co the tai lap

Tai lieu hoa schema, event log, feature flag, scheduler, webhook idempotency va privacy boundary giup nghien cuu co the lap lai tai nhieu lab. Day la dong gop engineering ho tro, khong nen la dong gop chinh duy nhat cua bai Q1.

## 5. Kien truc he thong

### 5.1 Thanh phan

| Lop | Cong nghe | Trach nhiem |
|---|---|---|
| Web client | Next.js App Router, TypeScript, Tailwind, Axios | UI theo role, dashboard, quest, assessment |
| API | FastAPI | REST, RBAC, orchestration, validation |
| Domain/service | Python services | quest, question, grading, development, cup, badge, certification |
| Persistence | PostgreSQL, SQLAlchemy async, Alembic | user, task, quest, answer, event, audit |
| AI provider | Gemini/OpenAI/Anthropic adapter | sinh JSON quest, cham cau tra loi/minh chung |
| Scheduler | background job/GitHub Actions callback | reset quest, Zalo dispatch, expiry |
| External | S4H, LHU, Zalo OA | auth, lich/MSSV, thong bao/quiz |
| Storage | local hoac S3-compatible private bucket | anh minh chung va PDF chung chi |

### 5.2 Bien he thong nghien cuu

Learner state tai thoi diem `t`:

```text
S_t = {level, XP, skill_mastery[], confidence[], completed_tasks,
       answer_history, attendance, discipline, roadmap_position}
```

Can thiep:

```text
I_t = {quest_set, question_set, feedback, XP, badge/cup signal}
```

Ket qua quan sat:

```text
O_t = {score, completion, time_on_task, evidence_quality,
       next_mastery, retention, attendance}
```

Vong lap cap nhat:

```text
S_(t+1) = Update(S_t, O_t, assessment_confidence)
```

## 6. Thuat toan 1 - Sinh Daily Quest co rang buoc

### Input

- user `u` co role candidate/member;
- level, XP;
- task va ky nang da hoan thanh;
- roadmap hien tai;
- quest trong cua so reset;
- limit theo role/level, mac dinh `N=5`;
- thoi gian Viet Nam va reset hour;
- AI provider/model/key.

### Process

1. Xac thuc role hoc vien.
2. Tinh `[start_at, reset_at)` theo `Asia/Ho_Chi_Minh`.
3. Danh dau `expired` cho quest active co `expires_at <= now`.
4. Lay quest hien co trong cua so.
5. Tinh `active_count` va `slots = min(N-existing_today, N-active_count)`.
6. Neu `slots <= 0`, tra bo hien co.
7. Tao context tu learner state va roadmap.
8. Goi LLM, yeu cau JSON schema co title, description, difficulty, XP.
9. Chuan hoa do kho, cat do dai, gioi han XP tu 5 den 100.
10. Neu AI loi/JSON sai/thieu item, chen template fallback.
11. Ghi quest pending voi cung `reset_at`, tao notification va commit.

### Output

- toi da `N` Daily Quest trong cua so;
- moi quest co title, description, difficulty, XP, status, expiry;
- thong tin limit: max, active, completed, expired;
- notification cho nguoi hoc.

### Pseudocode

```text
function GENERATE_DAILY_QUESTS(user, now):
    require user.role in {candidate, member}
    start, reset = RESET_WINDOW(now, VN_TIMEZONE)
    EXPIRE(user, now)
    existing = QUESTS_IN_WINDOW(user, start, reset)
    N = RESOLVE_LIMIT(user.role, user.level, default=5)
    active = COUNT_ACTIVE(user, now)
    slots = min(max(0, N - len(existing)), max(0, N - active))
    if slots == 0:
        return existing
    context = BUILD_CONTEXT(user)
    generated = LLM_GENERATE_JSON(context, slots)
    valid = VALIDATE_NORMALIZE(generated)
    items = TAKE(valid + FALLBACK(context), slots)
    persist items with expires_at = reset
    return existing + items
```

### Tinh chat

- Idempotency theo cua so: goi lai khong vuot limit.
- Safety: enum/status/XP duoc backend validate.
- Availability: AI loi van co fallback.
- Do phuc tap DB: phu thuoc so quest cua user; logic dem/xep hang xap xi `O(q)` sau truy van.

## 7. Thuat toan 2 - Chon 5 cau hoi thich nghi

### Input

- ngan hang cau hoi co skill key va numeric difficulty;
- 5 cau baseline;
- lich su cau tra loi va final/AI score;
- skill profile: mastery, confidence, current difficulty.

### Process

1. Neu baseline chua du 5 cau, tra cac baseline chua lam, toi da 5.
2. Tinh diem baseline trung binh `B`.
3. Anh xa `B` sang do kho nang luc `D`:

```text
B < 50      => D = 3.0
50 <= B <80 => D = 5.0
B >= 80     => D = 7.5
```

4. Sap xep skill profile tang dan theo mastery; neu chua co, dung database/backend/frontend/problem solving.
5. Voi moi cau hoi, tinh do kho muc tieu:

```text
D_target(skill) = 0.6 * D + 0.4 * current_difficulty(skill)
gap = |question_difficulty - D_target|
```

6. Xep theo `(weak_skill_rank, gap, created_at)` va lay 5 cau chua lam.

### Output

- toi da 5 cau hoi phu hop nang luc va uu tien skill yeu;
- moi cau co objective, difficulty, points va rubric/concept.

### Gia thuyet nghien cuu

Adaptive selection se tang learning gain va giam ty le cau qua de/qua kho so voi random/static selection.

## 8. Thuat toan 3 - Cham cau tra loi va cap nhat skill

### Input

- question, expected answer, accepted concept groups;
- answer text;
- learner profile;
- AI provider.

### Process AI

1. Yeu cau AI tra JSON: score, feedback, strengths, missing, confidence va breakdown.
2. Clamp score vao `[0,100]`, confidence vao `[0,1]`.
3. Chuan hoa breakdown thanh correctness, understanding, reasoning, application.
4. Luu AI score va mac dinh final score = AI score.

### Process fallback

Neu AI loi:

1. Chuan hoa Unicode, bo dau, dua ve token.
2. Mot concept duoc match neu:
   - concept mot token: overlap 100%;
   - concept nhieu token: overlap >=60%.
3. Neu co `G` nhom concept va `M` nhom match:

```text
coverage = M / G
score = 20 + 80 * coverage
```

4. Cau tra loi duoi 4 tu bi cap score toi da 55.
5. Fallback confidence = 0.45.

### Cap nhat mastery

He thong hien tai dung buoc cap nhat:

```text
delta = (score - previous_mastery) * clamp(confidence, 0.2, 1.0) * 0.18
mastery_new = clamp(previous_mastery + delta, 0, 100)
confidence_new = min(1.0, max(old_confidence, confidence) + 0.03)
```

Neu `score >=85` va confidence >=0.55, do kho co the tang; neu score <50 va confidence >=0.55, do kho co the giam.

### Output

- score, feedback, confidence, breakdown;
- answer status;
- skill mastery/confidence/difficulty moi;
- du lieu cho chon cau tiep theo.

## 9. Thuat toan 4 - Cham minh chung Quest

### Input

- quest type, title, description, difficulty, XP, auto-pass threshold;
- learner level/XP/role;
- proof text, link, image URL va flag co anh.

### Process

1. Kiem tra quest thuoc user, chua completed, chua expired.
2. Daily Quest can it nhat mot minh chung; Limit Quest bat buoc anh.
3. Chuyen status sang `submitted`.
4. Goi LLM voi rubric va JSON schema `{score, feedback, passed}`.
5. Clamp score vao `[0,100]`.
6. `passed = AI_passed AND score >= auto_pass_score`.
7. Neu AI loi, fallback score:

```text
score = 35
if proof_text has >= 6 words: score += 20
if proof_link exists:         score += 20
if proof_image exists:
    score += 35 for Limit Quest, otherwise 20
if image is required but missing: score = 0
score = min(score, 100)
```

8. Neu dat: status `completed`, cong XP mot lan, tinh lai level.
9. Neu khong dat: status `rejected`, cho phep bo sung theo policy.
10. Luu AI feedback va tao notification.

### Output

- score 0-100, feedback, passed;
- quest status;
- XP va level sau xu ly;
- audit timestamp.

### Gioi han quan trong

Code hien tai gui metadata/URL anh cho AI, khong chung minh rang model da doc pixel anh. Bai bao khong duoc goi day la "multimodal visual verification" neu chua truyen binary/image part va danh gia thuc nghiem kha nang nhan anh.

## 10. Thuat toan 5 - Danh gia Daily Task va promotion

### Input

- user task progress va submission;
- AI/manager/final score;
- attendance;
- discipline va reliability;
- nguong cau hinh.

### Process

- reconcile task theo ngay;
- phan loai complete/partial/missed;
- cong/tru discipline va reliability theo policy;
- tinh task completion rate, quality, attendance va discipline;
- tong hop member score theo trong so mac dinh:

```text
member_score = 0.40 * task_completion
             + 0.25 * quality
             + 0.20 * attendance
             + 0.15 * discipline
```

- promotion can dat cac nguong attendance, completion va score, sau do manager quyet dinh.

### Output

- daily report;
- discipline/reliability/member score;
- promotion progress va eligibility;
- dashboard 8 tuan.

## 11. Thuat toan 6 - Cup thu 6

### Input

- 8 cup definitions;
- lich Viet Nam, thu mo `4` khi Monday=0;
- 20 cau IT A/B/C/D;
- discipline score;
- answer map va thoi gian.

### Process

1. Chon cup chua tung duoc gan su kien.
2. Tao cua so thu 6 theo gio Viet Nam.
3. Chi candidate/member, khong phai mentor/admin, discipline >=80 duoc thi.
4. Moi user chi co mot attempt moi event.
5. Score = so dap an dung tren 20.
6. Duration = submitted_at - started_at.
7. Sau khi event dong, xep:

```text
ORDER BY score DESC, duration_seconds ASC, submitted_at ASC
```

8. Trao cup duy nhat cho hang 1.

### Output

- score, duration, rank;
- winner;
- cup award va snapshot discipline;
- remaining cups.

## 12. Cau hoi nghien cuu va gia thuyet

### RQ1 - Hieu qua hoc tap

Daily Quest va cau hoi thich nghi co tang learning gain so voi bo nhiem vu tinh khong?

`H1`: nhom adaptive co post-test da hieu chinh pre-test cao hon nhom static.

### RQ2 - Chat luong AI grading

Diem AI co dong thuan voi diem trung binh cua it nhat hai mentor khong?

`H2`: quadratic weighted kappa va ICC dat nguong chap nhan duoc; sai le tuyet doi nam trong bien equivalence dinh truoc.

### RQ3 - Tinh hieu qua

AI grading co giam thoi gian review cua mentor ma khong giam chat luong feedback khong?

`H3`: median review time giam, trong khi learner-rated feedback usefulness khong giam dang ke.

### RQ4 - Engagement

Quest, badge va cup co tang ty le hoan thanh, retention 8 tuan va attendance khong?

### RQ5 - Fairness va calibration

Sai so diem va ty le auto-pass co khac biet theo baseline ability, domain, ngon ngu, gioi tinh hoac nhom kinh nghiem khong?

### RQ6 - Ablation

Bo learner context, confidence update hoac fallback co lam giam ket qua khong?

## 13. Thiet ke thuc nghiem de du kha nang Q1

### 13.1 Thiet ke uu tien

Randomized controlled trial hoac stepped-wedge cluster trial tai nhieu lop/lab, toi thieu 8 tuan.

Nhom:

- Control: task/cau hoi tinh, mentor cham;
- Adaptive: TLMS chon quest/cau hoi thich nghi, AI formative grading co human oversight.

Neu khong random duoc, dung quasi-experiment voi propensity score va difference-in-differences.

### 13.2 Mau

- Thuc hien power analysis truoc khi thu thap.
- Bao cao inclusion/exclusion, attrition va missing data.
- Khong xem 7 tai khoan seed/dev la du lieu nghien cuu.
- Nen co nhieu cohort va nhieu mentor de giam bias theo lop/giam khao.

### 13.3 Bien ket qua

Primary:

- normalized learning gain;
- post-test score da dieu chinh pre-test;
- AI-human agreement.

Secondary:

- completion rate;
- retention va attendance;
- time-on-task;
- mentor workload;
- SUS/usability;
- feedback usefulness;
- error/fallback rate;
- fairness gap va calibration error.

### 13.4 Phan tich thong ke

- ANCOVA cho post-test voi pre-test covariate;
- mixed-effects model voi random intercept cho learner/class/mentor;
- Cohen's d/Hedges' g va 95% CI;
- ICC, quadratic weighted kappa, MAE/RMSE cho grading;
- Bland-Altman plot cho sai le diem;
- logistic mixed model cho completion/pass;
- survival analysis cho dropout neu du lieu phu hop;
- bootstrap CI khi phan phoi khong chuan;
- Holm/FDR cho multiple comparisons;
- sensitivity analysis va intention-to-treat.

### 13.5 Ablation

So sanh:

- full model;
- bo skill weakness;
- bo numeric difficulty;
- bo confidence weighting;
- template-only, khong LLM;
- LLM-only, khong rule validation;
- AI-only voi hybrid AI-human.

## 14. Protocol danh gia AI grading

1. Lay mau can bang theo domain, do kho va nhom nang luc.
2. An danh user va tron thu tu.
3. Hai mentor cham doc lap theo rubric.
4. Mentor thu ba xu ly bat dong lon.
5. AI cham ma khong biet diem mentor.
6. Khoa model, prompt, temperature va phien ban code.
7. Bao cao score agreement va pass/fail agreement.
8. Phan tich false pass, false reject va error theo subgroup.
9. Khong dung AI-only cho quyet dinh high-stakes khi chua dat validity target.

Nguong phai preregister, vi du:

- MAE <= 8 diem tren thang 100;
- QWK >= 0.75;
- false-pass <=5%;
- subgroup MAE gap <=3 diem.

Day chi la nguong de xuat, phai co co so chuyen mon va power analysis.

## 15. Du lieu can log them cho bai bao

Khong can thay code ngay trong tai lieu nay, nhung nghien cuu tuong lai can schema su kien:

```text
event_id, pseudonymous_user_id, cohort_id, timestamp_utc,
event_type, item_id, item_version, domain, difficulty,
model_provider, model_name, prompt_version, rubric_version,
score, confidence, latency_ms, token_usage, fallback_used,
human_score_1, human_score_2, final_score,
started_at, submitted_at, outcome
```

Tuyet doi khong dua email, phone, MSSV, token, raw private image vao dataset cong khai.

## 16. Dao duc, quyen rieng tu va an toan

- Xin phe duyet Hoi dong dao duc/IRB theo don vi.
- Consent ro rang va cho phep rut lui.
- Pseudonymize truoc phan tich.
- Tach du lieu van hanh khoi dataset nghien cuu.
- Co retention/deletion policy.
- Danh gia bias theo subgroup khi du mau.
- Cong khai viec dung LLM, model/version va fallback.
- Cho phep human appeal khi bi AI cham thap.
- Khong cong bo anh minh chung that.
- Bao cao conflict of interest va funding.

## 17. Tinh tai lap

Artifact package nen gom:

- data dictionary;
- prompt/rubric version da an key;
- code tinh metric va statistical analysis;
- synthetic/anonymized dataset;
- environment lockfile/container digest;
- migration revision;
- experiment protocol va preregistration;
- model name, ngay goi va tham so;
- seed cho moi buoc ngau nhien;
- limitations khi API model thay doi.

## 18. Cau truc bai bao de xuat

1. **Abstract**: problem, method, sample, main quantified results, contribution.
2. **Introduction**: gap va RQ, khong mo ta san pham dai dong.
3. **Related Work**: adaptive learning, automated assessment, evidence-centered design, gamification.
4. **Conceptual Framework**: learner-state closed loop va human governance.
5. **System and Algorithms**: Input, Process, Output, pseudocode, complexity.
6. **Method**: participants, design, instruments, protocol, ethics.
7. **Results**: learning, grading, workload, engagement, fairness, ablation.
8. **Discussion**: y nghia, co che, kha nang tong quat.
9. **Limitations and Threats to Validity**.
10. **Conclusion**.
11. **Data/Code/AI-use Statements**.

## 19. Hinh va bang can chuan bi

### Hinh

- Figure 1: closed-loop architecture.
- Figure 2: data flow va trust boundary.
- Figure 3: adaptive question/quest algorithm.
- Figure 4: experimental timeline 8 tuan.
- Figure 5: AI-human Bland-Altman va calibration.
- Figure 6: learning gain/engagement theo nhom.

### Bang

- Table 1: learner state va feature definitions.
- Table 2: algorithm inputs/outputs/hyperparameters.
- Table 3: participant demographics va baseline equivalence.
- Table 4: primary/secondary outcomes.
- Table 5: AI-human agreement theo domain/subgroup.
- Table 6: ablation results.
- Table 7: failure modes, fallback va mitigation.

## 20. Tap chi muc tieu

### Lua chon 1 - IEEE Transactions on Learning Technologies

Phu hop neu bai nhan manh thuat toan, adaptive learning, assessment va thuc nghiem cong nghe hoc tap. Dung [IEEE Article Templates](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/authoring-tools-and-templates/tools-for-ieee-authors/ieee-article-templates/) va kiem tra Information for Authors tai thoi diem nop.

### Lua chon 2 - International Journal of Artificial Intelligence in Education

Phu hop neu co learner model, AI assessment, ly thuyet hoc tap va empirical validation manh. Dung [Springer Nature journal templates](https://support.springernature.com/en/support/solutions/articles/6000081241-templates-and-style-files-for-journal-article-preparation) va huong dan rieng cua journal.

### Lua chon 3 - Computers & Education

Muc tieu rat cao. Bai phai co y nghia giao duc rong va ket qua co kha nang tong quat, khong chi la danh gia mot phan mem tai mot lab. Xem [journal page](https://shop.elsevier.com/journals/computers-and-education/0360-1315) va [Elsevier manuscript preparation](https://www.elsevier.com/publishing/publish-in-a-journal/manuscript-preparation).

### Lua chon 4 - Education and Information Technologies

Phu hop hon neu bai can bang system design va empirical educational outcomes. Xem [Springer journal page](https://doi.org/10.1007/10639.1573-7608).

Trang metrics cong khai cho thay cac journal tren co the nam Q1 o mot so category/nam, nhung tac gia phai xac minh lai trong Scopus/JCR truoc submission.

## 21. Mau bai bao chinh thuc tren Internet

- IEEE Word/LaTeX: [IEEE Template Selector](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/authoring-tools-and-templates/tools-for-ieee-authors/ieee-article-templates/).
- IEEE quy trinh nop: [IEEE Article Submission Process](https://journals.ieeeauthorcenter.ieee.org/submit-your-article-for-peer-review/the-ieee-article-submission-process/).
- Springer Word/LaTeX: [Templates and style files](https://support.springernature.com/en/support/solutions/articles/6000081241-templates-and-style-files-for-journal-article-preparation).
- Springer LaTeX: [LaTeX author support](https://www.springernature.com/de/authors/campaigns/latex-author-support).
- Elsevier LaTeX/elsarticle: [LaTeX instructions](https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions).
- Elsevier template policy: [Journal Article Publishing Support](https://service.elsevier.com/app/answers/detail/a_id/5955/supporthub/publishing/~/is-there-a-template-available-for-my-manuscript-file%3F/).

Khong copy template cua bai da xuat ban. Tai template chinh thuc cua publisher sau khi chot journal.

## 22. Bai lien quan de hoc cach lap luan

Khong sao chep noi dung; chi dung de xay related work va thiet ke validation:

- Tobler, **Smart grading: A generative AI-based tool for knowledge-grounded answer evaluation**, DOI [10.1016/j.mex.2023.102531](https://doi.org/10.1016/j.mex.2023.102531). Bai nhan manh rubric/sample solution, agreement va rui ro AI-only grading.
- **Assessing students' DRIVE**, DOI [10.1016/j.caeai.2025.100497](https://doi.org/10.1016/j.caeai.2025.100497). Vi du ve framework, taxonomy va validation voi learner traces.
- Triantafyllou et al., **Gamification in education and training: A literature review**, DOI [10.1007/s11159-024-10111-8](https://doi.org/10.1007/s11159-024-10111-8). Co so de tranh tuyen bo gamification luon hieu qua.
- **How does leveraging artificial intelligence in assessments impact student outcomes?**, DOI [10.1016/j.cosrev.2026.100929](https://doi.org/10.1016/j.cosrev.2026.100929). Tong quan gap ve du lieu private, validation va outcome.

## 23. Abstract khung, chua dien ket qua

```text
Adaptive learning systems increasingly employ large language models to generate
learning activities and formative feedback, yet evidence regarding learning
effectiveness, grading validity, fairness, and teacher workload remains limited.
This study introduces TLMS-AI, a human-governed framework that combines learner
state modelling, constrained daily quest generation, adaptive question selection,
evidence-aware scoring, and engagement mechanisms for laboratory-based software
engineering training. We evaluate the framework in an [DESIGN] study involving
[N] learners over eight weeks, comparing it with [BASELINE]. Primary outcomes are
learning gain and agreement between AI and human assessors; secondary outcomes
include completion, attendance, review time, usability, calibration, and subgroup
fairness. [INSERT QUANTIFIED RESULTS WITH 95% CI.] The findings show [RESULT], while
error analysis identifies [LIMITATION]. The study contributes a reproducible
closed-loop architecture, a hybrid assessment protocol, and empirical evidence
for responsible AI-supported technical training.
```

Khong dien ket qua gia dinh. Chi hoan thien abstract sau khi khoa dataset va phan tich.

## 24. Ke hoach cong bo

### Giai doan 1 - Readiness

- chot RQ va primary outcome;
- preregister protocol;
- phe duyet dao duc;
- dong bang rubric va model config;
- bo sung research event schema va anonymization;
- power analysis.

### Giai doan 2 - Pilot

- pilot 10-20 nguoi de sua instrument;
- kiem tra agreement mentor-mentor;
- kiem tra logging, missing data va fallback;
- khong gop pilot vao confirmatory result neu protocol khong cho phep.

### Giai doan 3 - Main study

- chay toi thieu 8 tuan;
- theo doi attrition va protocol deviation;
- khoa data, codebook va analysis plan truoc khi mo ket qua.

### Giai doan 4 - Manuscript

- viet bang tieng Anh hoc thuat;
- bao cao effect size va CI, khong chi p-value;
- co failure analysis va threats to validity;
- dua artifact/data statement;
- chon journal truoc khi format.

## 25. Danh gia muc san sang hien tai

| Thanh phan | Muc san sang | Can bo sung cho bai Q1 |
|---|---|---|
| He thong chay | Tot | Theo doi production dai han |
| Adaptive heuristic | Co | Baseline manh hon, ablation, formalization |
| AI grading | Co | Gold-standard human labels, fairness, calibration |
| Quest generation | Co | Prompt/version log, quality rubric, duplicate metric |
| Gamification | Co | Controlled evaluation, mediation analysis |
| Du lieu | Chua du | Cohort that, consent, multi-site neu co the |
| Reproducibility | Trung binh | Research log, frozen environment, anonymized artifact |
| Ethics | Chua ghi nhan | IRB/consent/data governance |
| Q1 claim | Chua du | Empirical result va doi chieu journal nam nop |

## 26. Ket luan

Dong gop manh nhat cua TLMS khong phai danh sach tinh nang, ma la **vong lap hoc tap thich nghi co quan tri con nguoi**, noi quest/cau hoi duoc chon tu learner state, minh chung duoc cham bang pipeline AI-rule-human, va ket qua quay lai cap nhat nang luc. De dat chuan Q1, du an can chuyen tu "system implementation" sang "theory-driven, preregistered, reproducible empirical study" voi doi chung, hieu ung dinh luong, AI-human agreement, fairness va phan tich failure.

