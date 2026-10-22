@echo off
setlocal enabledelayedexpansion

echo Setting up Bike Shop ERP environment...

if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env >nul
)

echo Building web container...
docker-compose build web

echo Starting database service...
docker-compose up -d db

echo Running migrations...
docker-compose run --rm web python manage.py migrate

echo Setup completed successfully.
