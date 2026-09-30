@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title AwowMusic - Instalacion

echo.
echo  ===============================================
echo    AwowMusic - Instalacion
echo  ===============================================
echo.

set "NEED_RESTART="

rem --- Python 3.12 --------------------------------------------------------
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo [..] No se encontro Python 3.12. Instalando con winget...
    winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
    set "NEED_RESTART=1"
)

rem --- Node.js -----------------------------------------------------------
where npm >nul 2>&1
if errorlevel 1 (
    echo [..] No se encontro Node.js. Instalando con winget...
    winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements
    set "NEED_RESTART=1"
)

rem --- ffmpeg ------------------------------------------------------------
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo [..] No se encontro ffmpeg. Instalando con winget...
    winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
    set "NEED_RESTART=1"
)

if defined NEED_RESTART (
    echo.
    echo [!] Se instalaron programas nuevos. Cierra esta ventana y vuelve a
    echo     ejecutar setup.bat para que Windows reconozca las rutas nuevas.
    goto :end
)

rem --- GPU ---------------------------------------------------------------
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo [AVISO] No se detecto una GPU NVIDIA. La separacion funcionara en CPU, mucho mas lenta.
) else (
    for /f "tokens=*" %%g in ('nvidia-smi --query-gpu^=name^,memory.total --format^=csv^,noheader') do echo [OK] GPU: %%g
)

rem --- Backend -----------------------------------------------------------
if not exist backend\.venv\Scripts\python.exe (
    echo [..] Creando entorno virtual de Python...
    py -3.12 -m venv backend\.venv || goto :fail
)
echo [..] Instalando dependencias del backend (PyTorch CUDA pesa ~3 GB la primera vez)...
backend\.venv\Scripts\python -m pip install --upgrade pip --quiet || goto :fail
backend\.venv\Scripts\python -m pip install -r backend\requirements-dev.txt || goto :fail

backend\.venv\Scripts\python -c "import torch; ok = torch.cuda.is_available(); print('[OK] PyTorch', torch.__version__, '- CUDA:', torch.cuda.get_device_name(0) if ok else 'no disponible (se usara CPU)')" || goto :fail

rem --- Frontend ----------------------------------------------------------
echo [..] Instalando dependencias del frontend...
pushd frontend
call npm install --no-fund --no-audit
if errorlevel 1 ( popd & goto :fail )
popd

echo.
echo  [OK] Instalacion completa. Ejecuta iniciar.bat para abrir la app.
goto :end

:fail
echo.
echo  [ERROR] La instalacion fallo. Revisa el mensaje de arriba.
pause
exit /b 1

:end
echo.
pause
