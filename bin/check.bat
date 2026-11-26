@echo off
setlocal
cd /d "%~dp0.."
docker compose version >nul 2>&1
if %errorlevel% equ 0 (
    set COMPOSE=docker compose
) else (
    set COMPOSE=docker-compose
)

echo Validando build e tipos estritos...
%COMPOSE% build web
if errorlevel 1 exit /b %errorlevel%
%COMPOSE% run --rm web mypy
if errorlevel 1 exit /b %errorlevel%
%COMPOSE% run --rm web python manage.py check
if errorlevel 1 exit /b %errorlevel%
call bin\test.bat %*
exit /b %errorlevel%
