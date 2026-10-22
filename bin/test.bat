@echo off
echo Running linter and format check...
docker-compose run --rm web ruff check .
if errorlevel 1 exit /b %errorlevel%

docker-compose run --rm web ruff format --check .
if errorlevel 1 exit /b %errorlevel%

echo Running test suite...
docker-compose run --rm web pytest %*
