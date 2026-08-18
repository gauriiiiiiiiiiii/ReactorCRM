@echo off
echo ============================================
echo  LinkedIn Lead System - Installing...
echo ============================================

python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: pip install failed. Make sure Python is installed.
    pause
    exit /b 1
)

python -m playwright install chromium
if %errorlevel% neq 0 (
    echo ERROR: Playwright install failed.
    pause
    exit /b 1
)

if not exist .env (
    copy .env.example .env
    echo Created .env file from template.
    echo Edit .env to add your LinkedIn credentials, then run run.bat
)

echo.
echo ============================================
echo  Installation complete!
echo  Next step: run run_demo.bat to start with
echo  demo data, or run.bat for live scraping.
echo ============================================
pause
