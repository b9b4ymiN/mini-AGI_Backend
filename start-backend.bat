@echo off
REM =============================================================================
REM Mini-AGI Backend - Windows Startup Script (Backend Only)
REM =============================================================================
REM Quick deployment script for Windows users
REM
REM Usage:
REM   start-backend.bat          Start backend
REM   start-backend.bat stop     Stop backend
REM   start-backend.bat logs     View logs
REM =============================================================================

setlocal enabledelayedexpansion

REM Colors (using PowerShell for colored output)
set "GREEN=[32m"
set "RED=[31m"
set "YELLOW=[33m"
set "NC=[0m"

if "%1"=="stop" goto STOP
if "%1"=="logs" goto LOGS
if "%1"=="restart" goto RESTART
if "%1"=="test" goto TEST
if "%1"=="help" goto HELP

:START
echo.
echo ========================================
echo   Mini-AGI Backend - Starting
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running!
    echo.
    echo Please start Docker Desktop first.
    echo.
    pause
    exit /b 1
)

echo [OK] Docker is running
echo.

REM Check if .env exists
if not exist .env (
    echo [INFO] .env file not found. Creating from template...
    if exist .env.backend-only.example (
        copy .env.backend-only.example .env
        echo.
        echo [IMPORTANT] Please edit .env file with your configuration!
        echo.
        echo For Z.AI: Add your ZAI_API_KEY
        echo For Ollama: Set OLLAMA_URL to your Ollama server
        echo.
        pause
    ) else (
        echo [ERROR] .env.backend-only.example not found!
        pause
        exit /b 1
    )
)

echo [INFO] Starting backend container...
docker-compose -f docker-compose.backend-only.yml up -d

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start backend!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Backend Started Successfully!
echo ========================================
echo.
echo   Backend API: http://localhost:8000
echo   API Docs:    http://localhost:8000/docs
echo   Health:      http://localhost:8000/health
echo.
echo ========================================
echo.

REM Wait a bit for backend to start
timeout /t 3 /nobreak >nul

REM Test health endpoint
echo [INFO] Testing backend health...
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Backend may not be ready yet. Check logs: start-backend.bat logs
) else (
    echo [OK] Backend is healthy!
)

echo.
echo Commands:
echo   start-backend.bat stop     - Stop backend
echo   start-backend.bat logs     - View logs
echo   start-backend.bat test     - Test endpoints
echo   start-backend.bat restart  - Restart backend
echo.
pause
exit /b 0

:STOP
echo.
echo [INFO] Stopping backend...
docker-compose -f docker-compose.backend-only.yml down
echo.
echo [OK] Backend stopped
echo.
pause
exit /b 0

:LOGS
echo.
echo [INFO] Viewing backend logs (Ctrl+C to exit)...
echo.
docker-compose -f docker-compose.backend-only.yml logs -f
pause
exit /b 0

:RESTART
echo.
echo [INFO] Restarting backend...
docker-compose -f docker-compose.backend-only.yml restart
echo.
echo [OK] Backend restarted
echo.
pause
exit /b 0

:TEST
echo.
echo ========================================
echo   Testing Backend Endpoints
echo ========================================
echo.

echo [1] Health Check:
curl -s http://localhost:8000/health
echo.
echo.

echo [2] LLM Info:
curl -s http://localhost:8000/llm/info
echo.
echo.

echo [3] Personas:
curl -s http://localhost:8000/personas
echo.
echo.

echo ========================================
echo   Tests Complete
echo ========================================
echo.
pause
exit /b 0

:HELP
echo.
echo Mini-AGI Backend - Windows Startup Script
echo.
echo Usage:
echo   start-backend.bat          Start backend
echo   start-backend.bat stop     Stop backend
echo   start-backend.bat logs     View logs
echo   start-backend.bat restart  Restart backend
echo   start-backend.bat test     Test endpoints
echo   start-backend.bat help     Show this help
echo.
pause
exit /b 0
