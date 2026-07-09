@echo off
chcp 65001 >nul
title Automyx 2.5 - Build
color 0B

echo.
echo  +=========================================+
echo  ^|   AUTOMYX 2.5 -- Windows Build Tool    ^|
echo  +=========================================+
echo.
echo  Genera: dist\AutomyxSetup.exe
echo  (instalador completo, sin dependencias externas)
echo.
echo  Esto puede tardar 5-10 minutos...
echo.

python build_windows.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] El build fallo. Revisa los mensajes arriba.
    pause
    exit /b 1
)

echo.
echo  Abriendo carpeta dist\...
pause >nul
explorer dist
