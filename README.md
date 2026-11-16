# 🌟 AYAKA API — Your API. Your Control. Your Ecosystem.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel)
![Resend](https://img.shields.io/badge/Resend-000000?style=for-the-badge&logo=resend)

**AYAKA API** adalah platform manajemen REST API profesional dengan desain **Neo Brutalism** kuning-putih. Dibangun untuk developer yang membutuhkan sistem API Key yang aman, verifikasi *Magic Link* via email, analitik *real-time*, dan perlindungan data tingkat lanjut.

> **Powered by AYAKA Sync**  
> **Owner:** OLPI STORE  
> **Admin:** Ayaka Sync (olpieditz336@gmail.com)

---

## 🔗 Tautan Penting
- **GitHub Repository:** [olpigiantara-design](https://github.com/olpigiantara-design)
- **WhatsApp Channel:** [AYAKA Sync Channel](https://whatsapp.com/channel/0029VbEbK4dHgZWWJmXFP52o)

---

## 🚀 Fitur Utama

- **🔐 API Key Management**: Generate, *revoke*, dan atur izin API Key dengan aman. Secret di-hash menggunakan SHA-256 dengan *pepper* server-side. Key asli hanya ditampilkan satu kali.
- **✨ Magic Link Premium**: Sistem aktivasi *Premium* melalui email terverifikasi. Menggunakan token *one-time* yang kedaluwarsa dalam 15 menit (terintegrasi dengan Resend).
- **🛡️ Security First**: Password di-hash dengan Argon2id, *session cookie* HttpOnly, proteksi CSRF, *rate limiting*, dan *audit log* untuk setiap tindakan sensitif.
- **📊 Real-Time Analytics**: Pantau trafik API, *success rate*, dan status *Premium* langsung dari database.
- **⚡ Interactive Playground**: Uji coba endpoint API secara langsung dari *dashboard* tanpa perlu aplikasi pihak ketiga.
- **👨‍💻 Multi-Language Docs**: Dokumentasi integrasi yang siap pakai untuk JavaScript (Fetch), PHP (cURL), dan Python (Requests).

---

## 🛠️ Teknologi yang Digunakan

- **Frontend**: HTML5, CSS3 (Neo Brutalism), Vanilla JavaScript (ES6+), Chart.js
- **Backend**: Python (FastAPI, Uvicorn)
- **Database**: PostgreSQL (Neon Tech Serverless)
- **Email Service**: Resend
- **Deployment**: Vercel
- **Security**: Argon2-cffi, itsdangerous

---

## 📂 Struktur Proyek

```text
ayaka-api/
├── api/
│   ├── index.py                  # Entry point FastAPI untuk Vercel
│   ├── auth_routes.py            # Endpoint Register, Login, Logout
│   ├── key_routes.py             # CRUD API Key
│   ├── magic_link_routes.py      # Endpoint /api/am/*
│   ├── analytics_routes.py       # Endpoint Analytics & Logs
│   ├── admin_routes.py           # Endpoint AYAKA Sync Admin Panel
│   └── deps.py                   # Dependency injection & Middleware
├── services/
│   ├── database.py               # Koneksi asyncpg + Neon Pooler
│   ├── security.py               # Hashing, Token, Session
│   ├── email_service.py          # Integrasi Resend & Template HTML
│   └── api_key_service.py        # Logika Generate & Verifikasi API Key
├── public/                       # Folder Frontend (Static Files)
│   ├── index.html                # Landing Page
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── documentation.html
│   ├── admin.html
│   ├── maintenance.html
│   ├── css/                      # File CSS (style.css, dashboard.css, dll)
│   └── js/                       # File JavaScript (app.js, auth.js, dll)
├── database/
│   └── schema.sql                # Skema Database & Migrasi
├── tests/
│   └── test_endpoints.py         # Automated testing (Pytest)
├── requirements.txt
├── vercel.json
├── .env.example
├── .gitignore
└── README.md