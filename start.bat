@echo off
echo 🚀 Starting FinPulse Backend on Port 8005...

if not exist .env (
    echo 📄 Copying .env.example -> .env
    copy .env.example .env
)

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

echo 📦 Starting PostgreSQL database in Docker...
docker compose up -d
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Docker failed to start! Make sure Docker Desktop is open and running.
    pause
    exit /b %ERRORLEVEL%
)

echo ⚡ Running Database Migrations...
alembic upgrade head

echo 🔥 Starting FastAPI Server on http://localhost:8005...
uvicorn app.main:app --reload --host 0.0.0.0 --port 8005
