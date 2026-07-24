# 🚀 FinPulse — Project Start Guide

Complete guide and commands to run the **FinPulse** project (Backend + Frontend + Database) locally.

---

## 📋 Prerequisites

1. **Docker Desktop** installed and running on your system.
2. **Node.js** (v18+) installed.
3. **Python** (v3.10+) installed.

---

## ⚡ Quick Start Overview

| Service | Technology | Port | Command to Run |
|---|---|---|---|
| **Database** | PostgreSQL (Docker) | `5434` | `docker compose up -d` |
| **Backend API** | FastAPI + Uvicorn | `8005` | `uvicorn app.main:app --reload --host 0.0.0.0 --port 8005` |
| **Frontend App** | React + Vite | `5173` | `npm run dev` |

---

## 🛠️ Step-by-Step Commands

### 1️⃣ Terminal 1: Backend Setup (`finpulse-backend`)

Open a terminal window and navigate to `finpulse-backend`:

```powershell
cd finpulse-backend
```

#### Step 1A: Start Database Container (Docker)
```powershell
docker compose up -d
```

#### Step 1B: Activate Virtual Environment
```powershell
.\venv\Scripts\activate
```

#### Step 1C: Run Database Migrations
```powershell
alembic upgrade head
```

#### Step 1D: Start Backend FastAPI Server
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8005
```

> **Backend Access Links**:
> - API Root / Base: [http://localhost:8005](http://localhost:8005)
> - Swagger UI Docs: [http://localhost:8005/docs](http://localhost:8005/docs)
> - ReDoc Docs: [http://localhost:8005/redoc](http://localhost:8005/redoc)

---

### 2️⃣ Terminal 2: Frontend Setup (`finpulse-frontend`)

Open a second terminal window and navigate to `finpulse-frontend`:

```powershell
cd finpulse-frontend
```

#### Step 2A: Install Dependencies (First time only)
```powershell
npm install
```

#### Step 2B: Start React / Vite Development Server
```powershell
npm run dev
```

> **Frontend Access Link**:
> - Web Application: [http://localhost:5173](http://localhost:5173)

---

## 💡 Shortcut: 1-Click Backend Startup Script

Inside `finpulse-backend`, you can also run the automated startup script:

**PowerShell**:
```powershell
.\start.ps1
```

**CMD**:
```cmd
start.bat
```

*(This script automatically checks `.env`, starts Docker container, runs Alembic migrations, and launches Uvicorn on port 8005)*.

---

## 🛑 How to Stop Services

- **Stop Servers**: Press `Ctrl + C` in the respective terminal windows.
- **Stop Docker Database**:
  ```powershell
  cd finpulse-backend
  docker compose down
  ```
