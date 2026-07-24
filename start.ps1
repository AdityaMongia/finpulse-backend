# ==============================================================================
# FinPulse Backend — One-Click Startup Script (PowerShell)
# ==============================================================================

Write-Host "🚀 Starting FinPulse Backend on Port 8005..." -ForegroundColor Cyan

# 1. Ensure .env exists
if (-not (Test-Path ".env")) {
    Write-Host "📄 Copying .env.example -> .env..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

# 2. Check Virtual Environment & Dependencies
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "🐍 Activating virtual environment..." -ForegroundColor Green
    & ".\venv\Scripts\Activate.ps1"
} else {
    Write-Host "⚠️ Virtual environment not found. Creating 'venv'..." -ForegroundColor Yellow
    python -m venv venv
    & ".\venv\Scripts\Activate.ps1"
    pip install -r requirements.txt
}

# 3. Start Database via Docker
Write-Host "📦 Starting PostgreSQL database in Docker..." -ForegroundColor Cyan
docker compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ Docker failed to start!" -ForegroundColor Red
    Write-Host "👉 Please make sure Docker Desktop application is OPEN and RUNNING on your PC." -ForegroundColor Yellow
    exit 1
}

# 4. Run Migrations
Write-Host "⚡ Running Database Migrations..." -ForegroundColor Cyan
alembic upgrade head

# 5. Launch FastAPI Backend Server on Port 8005
Write-Host "🔥 Starting Uvicorn Server on http://localhost:8005..." -ForegroundColor Green
uvicorn app.main:app --reload --host 0.0.0.0 --port 8005
