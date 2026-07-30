@echo off
echo 🚀 Starting FinPulse Backend on Port 8005...

if not exist .env (
    echo 📄 Copying .env.example -> .env
    copy .env.example .env
)

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

echo 📦 Ensure local PostgreSQL service is running on port 5432...

echo ⚡ Running Database Migrations...
alembic upgrade head

echo 🔥 Starting FastAPI Server on http://localhost:8005...
uvicorn app.main:app --reload --host 0.0.0.0 --port 8005
