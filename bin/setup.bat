@echo off
setlocal enabledelayedexpansion

docker compose version >nul 2>&1
if %errorlevel% equ 0 (
    set COMPOSE=docker compose
) else (
    set COMPOSE=docker-compose
)

echo Setting up Bike Shop ERP environment...

if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env >nul
)

echo Building web container...
%COMPOSE% build web

echo Starting database service...
%COMPOSE% up -d db

echo Running migrations...
%COMPOSE% run --rm web python manage.py migrate

echo Setup completed successfully.
