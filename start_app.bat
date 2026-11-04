@echo off
echo =======================================================
echo   AyurLLM Hospital Platform - Full-Stack Launcher
echo =======================================================
echo Starting FastAPI Backend on http://localhost:8000 ...
start "AyurLLM Backend" cmd /k "cd backend && .venv\Scripts\python run.py"

echo Starting React + Vite Frontend on http://localhost:3000 ...
start "AyurLLM Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Both services launched!
echo Backend Docs: http://localhost:8000/api/docs
echo Frontend URL: http://localhost:3000
echo =======================================================
pause
