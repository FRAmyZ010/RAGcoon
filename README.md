## 📁 Project Structure

```text
RAGCOON/
├── backend/                # 🐍 Python FastAPI Backend
│   ├── data/               # เก็บไฟล์เอกสารดิบ (PDF, TXT)
│   ├── rag/                # หัวใจของระบบ RAG (Logic, Engine)
│   ├── services/           # บริการเสริมต่างๆ (เช่น การต่อ Database)
│   ├── .env                # ไฟล์เก็บความลับ (API Keys) - ห้ามแชร์!
│   ├── .env.example        # ไฟล์ตัวอย่างการตั้งค่า Environment
│   ├── main.py             # จุดเริ่มต้นการรัน Server FastAPI
│   └── requirements.txt    # รายการ Library ที่ต้องติดตั้ง
│
├── frontend/               # ⚛️ React Frontend
│   ├── pages/              # หน้าหลักต่างๆ ของเว็บไซต์
│   ├── public/             # ไฟล์ Static (index.html, Favicon)
│   │   └── index.html      # ไฟล์ Entry point ของหน้าเว็บ
│   ├── src/                # ซอร์สโค้ดหลักของ Frontend
│   │   ├── components/     # ชิ้นส่วน UI (ChatBox, Navbar, Button)
│   │   ├── icon/           # ไฟล์ไอคอนต่างๆ ที่ใช้ในเว็บ
│   │   ├── img/            # ไฟล์รูปภาพประกอบ
│   │   ├── services/       # ส่วนเชื่อมต่อ API (Axios, Fetch)
│   │   └── styles/         # ไฟล์จัดการความสวยงาม (CSS/SCSS)
│   ├── .env                # การตั้งค่าฝั่งหน้าบ้าน
│   └── .env.example        # ตัวอย่างการตั้งค่าฝั่งหน้าบ้าน
│
├── .gitignore              # ไฟล์บอก Git ว่าไม่ต้องเอาไฟล์ไหนขึ้น GitHub
└── README.md               # เอกสารอธิบายโปรเจกต์ (ไฟล์นี้)
```

## 🚀 การตั้งค่าโปรเจกต์ (Project Setup)

### 1. การเตรียม Environment Variables
สร้างไฟล์ `.env` ในโฟลเดอร์ `backend/` และ `frontend/` โดยอ้างอิงตามตัวอย่างในไฟล์ `.env.example`

### 2. การตั้งค่า Backend
#### 2.1 เข้าไปที่ Folder backend:
```bash
cd backend
```
#### 2.2 สร้างและเปิดใช้งาน Virtual Environment:
```bash
# สร้าง venv
python -m venv venv

# การเปิดใช้งาน
# สำหรับ Windows:
.\venv\Scripts\activate
# สำหรับ Mac/Linux:
source venv/bin/activate

# การปิดใช้งาน
deactivate
```

#### 2.3 ติดตั้ง Dependencies:
```bash
pip install -r requirements.txt
``` 

### 3. การตั้งค่า Frontend
เปิด terminal อีกหน้าต่างและรันคำสั่งดังนี้
#### 3.1 เข้าไปที่ Folder frontend
```bash
cd frontend
```
#### 3.2 ติดตั้ง Dependencies และ Library ที่จำเป็น:
```bash
npm init -y
npm install axios lucide-react bcrypted
```
