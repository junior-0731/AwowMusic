@echo off
chcp 65001 >nul
cd /d "%~dp0"
title AwowMusic

if not exist backend\.venv\Scripts\python.exe (
    echo [ERROR] Falta instalar el backend. Ejecuta setup.bat primero.
    pause
    exit /b 1
)
if not exist frontend\node_modules (
    echo [ERROR] Falta instalar el frontend. Ejecuta setup.bat primero.
    pause
    exit /b 1
)

echo Iniciando backend en http://127.0.0.1:8000 ...
start "AwowMusic - backend" /D "%~dp0backend" cmd /k ".venv\Scripts\python -m uvicorn app.main:run --factory --host 127.0.0.1 --port 8000"

echo Iniciando interfaz en http://localhost:5173 ...
start "AwowMusic - interfaz" /D "%~dp0frontend" cmd /k "npm run dev"

echo Esperando a que el backend responda...
powershell -NoProfile -Command "for ($i = 0; $i -lt 90; $i++) { try { Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/health -TimeoutSec 2 | Out-Null; exit 0 } catch { Start-Sleep -Milliseconds 500 } }; exit 1"
if errorlevel 1 (
    echo [AVISO] El backend no respondio a tiempo. Revisa la ventana "AwowMusic - backend".
)

start "" http://localhost:5173
echo.
echo AwowMusic esta corriendo. Para cerrarla, cierra las ventanas "backend" e "interfaz".
timeout /t 5 >nul
