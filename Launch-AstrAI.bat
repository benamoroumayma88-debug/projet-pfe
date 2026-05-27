@echo off
REM ─────────────────────────────────────────────────────────────────
REM  AstrAI BI — Insurance Claims Intelligence Platform
REM  One-click launcher: starts the web app and opens the browser.
REM ─────────────────────────────────────────────────────────────────

title AstrAI BI Platform

REM Change to the script's own directory (so it works from anywhere)
cd /d "%~dp0"

REM Open the browser after a 6-second delay (lets the server boot first)
start "" /B cmd /C "timeout /t 6 /nobreak >nul & start https://localhost:7247"

REM Start the ASP.NET Core app
cd InsuranceWeb
dotnet run

REM If dotnet run exits, pause so the user can see any error message
echo.
echo ─────────────────────────────────────────────────
echo  Server stopped. Press any key to close this window.
echo ─────────────────────────────────────────────────
pause >nul
