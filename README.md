# RAGcoon

ระบบถาม–ตอบเอกสาร **โครงงานจบ Computer Engineering** แบบ RAG (Retrieval-Augmented Generation)  
Frontend: React + Vite · Backend: FastAPI · DB: PostgreSQL (+ pgvector) · Vector: Qdrant Cloud · LLM: Ollama (ค่าเริ่มต้น) / Gemini / OpenAI

คำศัพท์และ architecture locks ดูที่ [`CONTEXT.md`](./CONTEXT.md)

### สำคัญ — ขอบเขตของโปรเจกต์

RAGcoon เป็น **case study / การทดลอง (experimental)** เพื่อศึกษาและสาธิตแนวทาง RAG กับคลังเอกสารโครงงานจบ — **ไม่ใช่ระบบพร้อมใช้ในงานจริงหรือ production**

- ผลลัพธ์จากแชท คุณภาพการค้นคืน และตัวเลข/รายงาน evaluation ใน repo เป็นผลจากการทดลองภายใต้เงื่อนไขที่กำหนดเท่านั้น
- **เกณฑ์การวัดและคะแนนประเมินจำนวนมากใช้ AI เป็นผู้ประเมิน** (เช่น LLM-as-judge / automated scoring) จึงอาจมีอคติ ความคลาดเคลื่อน หรือไม่สอดคล้องกับมุมมองมนุษย์
- **แนะนำให้ผู้ใช้และผู้วิจัยประเมินซ้ำด้วยมนุษย์ (human evaluation)** ก่อนนำผลไปอ้างอิง ตัดสินใจ หรือสรุปเชิงวิชาการ/เชิงปฏิบัติ

---

## Quick start (แนะนำ — Docker ทั้งก้อน)

### สิ่งที่ต้องมี

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac) หรือ Docker Engine + Compose (Linux)
- RAM พอสมควร (แนะนำ 8GB+ เพราะมี Ollama + embedding)
- **Qdrant Cloud** URL + API key (จำเป็นสำหรับ chat/RAG ที่ต้องค้นเอกสาร)

### วิธีรัน

**Windows — กดรัน**

1. ดับเบิลคลิก `start.bat`  
   หรือใน PowerShell: `.\start.ps1`  
   หรือ: `npm run stack:start`
2. รอจนสคริปต์เปิดเบราว์เซอร์ที่ http://localhost:5173

**Mac / Linux**

```bash
chmod +x start.sh stop.sh scripts/start.sh scripts/stop.sh
./start.sh
```

**คำสั่งอย่างเดียว (ทุก OS)**

```bash
cp .env.example .env
cp .env.example backend/.env
# แก้ backend/.env ให้ใส่ QDRANT_URL และ QDRANT_API_KEY

docker compose -p ragcoon up -d --build
```

### สคริปต์ start ทำอะไรบ้าง

1. เช็ค/สตาร์ท Docker
2. สร้าง `.env` และ `backend/.env` จาก `.env.example` **เฉพาะตอนยังไม่มี** (ไม่ทับของเดิม)
3. เตือนถ้า Qdrant/JWT ยังเป็นค่า placeholder
4. `docker compose -p ragcoon up -d --build`
5. รอ backend + frontend พร้อม แล้วเปิด http://localhost:5173

### หยุดระบบ

| OS | วิธี |
|----|------|
| Windows | ดับเบิลคลิก `stop.bat` / `.\stop.ps1` / `npm run stack:stop` |
| Mac/Linux | `./stop.sh` |
| ทุก OS | `docker compose -p ragcoon down` หรือ `npm run docker:down` |

ข้อมูลใน volume (Postgres / Ollama) จะถูกเก็บไว้  
ลบ volume ด้วย: `docker compose -p ragcoon down -v`

---

## URLs & พอร์ต

| บริการ | URL / พอร์ต |
|--------|-------------|
| Frontend (Vite) | http://localhost:5173 |
| Backend API docs | http://localhost:8000/docs |
| Backend health (DB) | http://localhost:8000/health/db |
| pgAdmin | http://localhost:8080 |
| Ollama | http://localhost:11434 |
| PostgreSQL | `localhost:5432` |

---

## ตั้งค่า `.env`

ไฟล์หลักที่ backend อ่าน: **`backend/.env`**  
ไฟล์ root **`.env`** ใช้ให้ Docker Compose แทนค่า `${POSTGRES_*}` / pgAdmin

| ตัวแปรสำคัญ | ความหมาย |
|-------------|----------|
| `QDRANT_URL` / `QDRANT_API_KEY` | Qdrant Cloud (จำเป็นสำหรับ RAG) |
| `COLLECTION_NAME` | ชื่อ collection ใน Qdrant |
| `EMBEDDING_MODEL` | โมเดลฝังตัว (ใน Compose อาจ override เป็นรุ่นเล็กกว่าเพื่อประหยัด RAM) |
| `LLM_PROVIDER` | `ollama` / `gemini` / `openai` |
| `OLLAMA_MODEL` | ค่าเริ่มต้นใน Compose: `gemma3:4b` |
| `GEMINI_API_KEY` / `OPENAI_API_KEY` | ใช้เมื่อเปลี่ยน provider |
| `JWT_SECRET` | ลายเซ็น JWT |
| `ADMIN_*` | seed บัญชี Administrator |
| `AI_ENGINEER_*` | seed บัญชี AI Engineer (ดูตัวอย่างใน `backend/.env.example`) |

ตัวอย่างครบชุด: [`.env.example`](./.env.example) และ [`backend/.env.example`](./backend/.env.example)

---

## บทบาทผู้ใช้ (seed อัตโนมัติตอน backend สตาร์ท)

| บทบาท | ใช้ทำอะไร | ค่า default (ถ้าไม่ตั้งใน `.env`) |
|--------|-----------|-------------------------------------|
| **General User** | Chat โดยไม่ต้องล็อกอิน | — |
| **Administrator** | Documents, Dashboard, Feedback admin | `admin` / `admin123` (ดู `backend/.env.example`) |
| **AI Engineer** | หน้า AI Config / ปรับ LLM–RAG | `ai_engineer` / `ai_engineer` |

> ถ้า copy จาก root `.env.example` ค่า `ADMIN_PASSWORD` อาจเป็น `admin` — แก้ให้ตรงที่ต้องการได้ใน `backend/.env`  
> seed จะสร้าง user ครั้งแรกเท่านั้น ไม่รีเซ็ตรหัสผ่านถ้ามี user อยู่แล้ว

ประวัติแชทของ General User เก็บใน **browser `localStorage` เท่านั้น** (ไม่เรียก `GET /workspaces*`) — รายละเอียดใน `CONTEXT.md`

---

## หน้า Frontend

| Path | หน้า |
|------|------|
| `/chat` | ถาม–ตอบ RAG (ค่าเริ่มต้น) |
| `/documents` | จัดการเอกสาร PDF (ต้องล็อกอิน Admin) |
| `/dashboard` | Overview / metrics |
| `/feedback` | ส่ง/ดู feedback |
| `/ai-config` | ตั้งค่า AI / RAG (AI Engineer) |

API ฝั่ง frontend เรียกแบบ relative `/api/...` แล้วให้ Vite proxy ไป backend

---

## Backend API (หลัก)

Base: `/api/v1` · Docs: http://localhost:8000/docs

| กลุ่ม | ตัวอย่าง |
|-------|----------|
| Auth | `POST /auth/login`, `GET /auth/me` |
| Chat | `POST /chat/query-stream` (SSE; ส่ง `messages` ได้สูงสุด 3 turns) |
| Documents | upload / list / delete / file |
| Dashboard | metrics / track-visit |
| Feedback | ส่งและจัดการ feedback |
| AI Config | presets / runtime RAG–LLM settings |

---

## สิ่งที่รันใน Docker

จาก `docker-compose.yml` (โปรเจกต์ชื่อ `ragcoon`):

| Service | รายละเอียด |
|---------|------------|
| `frontend` | Vite **dev** + hot reload (bind-mount `frontend/`) |
| `backend` | FastAPI + **`--reload`** (bind-mount `backend/`) |
| `postgres` | PostgreSQL 16 + pgvector |
| `pgadmin` | UI จัดการ DB |
| `ollama` | LLM local — ดึง `gemma3:4b` ตอนสตาร์ทครั้งแรก |

ครั้งแรกอาจช้ามาก (ดาวน์โหลด image + model)

---

## คำสั่ง npm ที่ root

| Script | การทำงาน |
|--------|----------|
| `npm run stack:start` | one-click start (`scripts/start.ps1`) — Windows |
| `npm run stack:stop` | หยุด stack |
| `npm run docker:up` | `docker compose -p ragcoon up -d --build` |
| `npm run docker:down` | `docker compose -p ragcoon down` |
| `npm run docker:logs` | ดู logs ทั้ง stack |
| `npm run dev` | Hybrid: Docker infra/backend + Vite บนเครื่อง (`scripts/dev.ps1`) |
| `npm run dev:frontend` | รันเฉพาะ Vite บน host |

Frontend อย่างเดียว:

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173 (LAN: 0.0.0.0)
npm run build
npm run lint
```

---

## Hybrid / พัฒนาบนเครื่อง (ทางเลือก)

### A) Docker ครบ (แนะนำสำหรับคน clone มาใหม่)

ใช้ `start.bat` / `./start.sh` ตาม Quick start

### B) Infra ใน Docker + Frontend บน host (Windows)

```bash
npm run dev
```

สคริปต์จะ `docker compose up` แล้วรัน Vite ที่เครื่อง — โชว์ URL localhost + LAN

### C) Backend บน host (advanced)

ต้องการ Python 3.11+, venv, Postgres/Qdrant/Ollama ที่เข้าถึงได้:

```bash
cd backend
python -m venv venv
# Windows: .\venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # แล้วแก้ค่า
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## โครงสร้างโปรเจกต์ (ปัจจุบัน)

```text
RAGcoon/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # auth, chat, documents, dashboard, feedback, ai_config
│   │   ├── core/            # config, database, security
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── rag/             # embedding, retrieval, evaluation
│   ├── alembic/
│   ├── storage/             # ไฟล์ที่อัปโหลด
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/           # Chat, Documents, Dashboard, Feedback, AIconfig, Login
│   │   ├── components/
│   │   ├── services/        # API clients (+ chatHistory localStorage)
│   │   └── Routes/
│   ├── Dockerfile
│   └── package.json
├── scripts/                 # start/stop/dev + utility scripts
├── tests/                   # pytest
├── docs/                    # sprint scope, ADR, notes
├── data/                    # ชุดข้อมูล / รายงาน evaluation บางส่วน
├── docker-compose.yml
├── start.bat / start.sh / stop.bat / stop.sh
├── .env.example
├── CONTEXT.md
└── README.md
```

---

## ทดสอบ

จาก root (ต้องมี dependencies ของ backend / ตั้งค่า env ตามที่เทสต้องการ):

```bash
# ตัวอย่าง
pytest tests/ -q
```

มีเทสครอบคลุม auth, chat contract, upload, feedback, retrieval/prescreen, dashboard ฯลฯ ในโฟลเดอร์ `tests/`

---

## เอกสารเพิ่มเติม

| ไฟล์ | เนื้อหา |
|------|---------|
| [`CONTEXT.md`](./CONTEXT.md) | คำศัพท์ + Sprint 2 P1 architecture locks |
| [`docs/sprint-2-scope.md`](./docs/sprint-2-scope.md) | ขอบเขต Sprint 2 |
| [`docs/pipeline_benchmark_comparison.md`](./docs/pipeline_benchmark_comparison.md) | บันทึก benchmark pipeline |
| `backend/app/rag/evaluation/` | สคริปต์/ผล evaluation ฝั่ง RAG |

รายงานและตัวเลขในโฟลเดอร์เหล่านี้เป็นส่วนหนึ่งของ **การทดลอง** และมักอาศัย **การประเมินด้วย AI** — ควรใช้ประกอบการศึกษาเท่านั้น และแนะนำให้มี **human evaluation** ควบคู่เสมอ

---

## Troubleshooting สั้นๆ

| อาการ | แนวทาง |
|-------|--------|
| สตาร์ทช้ามากครั้งแรก | รอ pull image + `ollama pull gemma3:4b` |
| Chat หาเอกสารไม่ได้ | เช็ค `QDRANT_URL` / `QDRANT_API_KEY` ใน `backend/.env` |
| พอร์ตชน | ปิดโปรเซสที่ใช้ 5173/8000/5432/8080/11434 หรือเปลี่ยน mapping ใน compose |
| Frontend ใน Docker ไม่ hot-reload (Windows) | Compose ตั้ง `CHOKIDAR_USEPOLLING=true` แล้ว; ลอง restart `ragcoon-frontend` |
| ชื่อ container ชน | `docker rm -f ragcoon-postgres ragcoon-pgadmin ragcoon-ollama ragcoon-backend ragcoon-frontend` แล้วรัน start ใหม่ |
| ล็อกอินไม่ได้ | ใช้ user จาก seed / ดูค่า `ADMIN_*` ใน `backend/.env` (seed ไม่รีเซ็ตรหัสถ้ามี user แล้ว) |

---

## License / โปรเจกต์

Senior project — RAGcoon (เอกสารโครงงานจบ CE + RAG Q&A)
