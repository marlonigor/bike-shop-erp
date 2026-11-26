@echo off
setlocal
cd /d "%~dp0.."
set "PREVIOUS_HOOKS="
for /f "delims=" %%H in ('git config --get core.hooksPath') do set "PREVIOUS_HOOKS=%%H"
if defined PREVIOUS_HOOKS if not "%PREVIOUS_HOOKS%"==".githooks" (
    echo Erro: ha hooks personalizados. Integre-os antes de ativar .githooks.
    exit /b 1
)
git config --local core.hooksPath .githooks
if errorlevel 1 exit /b %errorlevel%
echo Hooks locais ativados. Commit e push exigem bin/check aprovado.
