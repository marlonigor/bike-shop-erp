@echo off
setlocal enabledelayedexpansion

docker compose version >nul 2>&1
if %errorlevel% equ 0 (
    set COMPOSE=docker compose
) else (
    set COMPOSE=docker-compose
)

echo Running linter and format check...
%COMPOSE% run --rm web ruff check .
if errorlevel 1 exit /b %errorlevel%

%COMPOSE% run --rm web ruff format --check .
if errorlevel 1 exit /b %errorlevel%

echo Running test suite...
%COMPOSE% run --rm web pytest %*
