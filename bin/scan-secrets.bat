@echo off
setlocal

set "GITLEAKS_IMAGE=ghcr.io/gitleaks/gitleaks:v8.30.1"

docker version >nul 2>&1
if errorlevel 1 (
    echo Erro: Docker nao encontrado.
    exit /b 1
)

echo Obtendo o scanner de segredos fixado...
powershell -NoProfile -Command "$process = Start-Process -FilePath 'docker' -ArgumentList @('pull', '%GITLEAKS_IMAGE%') -PassThru -NoNewWindow; if (-not $process.WaitForExit(120000)) { $process.Kill(); exit 124 }; exit $process.ExitCode"
if errorlevel 1 exit /b %errorlevel%

echo Verificando segredos no historico Git...
docker run --rm --volume "%CD%:/repo:ro" --workdir /repo %GITLEAKS_IMAGE% ^
    git --no-banner --redact --timeout 120 .
