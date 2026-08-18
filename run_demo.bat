@echo off
echo ============================================
echo  LinkedIn Lead System - Demo Mode
echo ============================================
echo Seeding demo data...
python seed_demo.py
echo.
echo Starting server...
echo Open http://127.0.0.1:5000 in your browser
echo Press Ctrl+C to stop
echo ============================================
python app.py
pause
