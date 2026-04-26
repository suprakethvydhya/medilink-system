@echo off
REM MediLink Pharmacy Management System - Windows Setup Script

echo ============================================================
echo   MediLink Pharmacy Management System - Setup Script
echo ============================================================
echo.

REM Check Python installation
echo [1/7] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)
python --version
echo.

REM Create virtual environment
echo [2/7] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created successfully
) else (
    echo Virtual environment already exists
)
echo.

REM Activate virtual environment
echo [3/7] Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Install dependencies
echo [4/7] Installing dependencies...
pip install -r requirements.txt
echo.

REM Copy environment file
echo [5/7] Setting up environment file...
if not exist ".env" (
    copy .env.example .env
    echo .env file created - Please edit with your database credentials
) else (
    echo .env file already exists
)
echo.

REM Check MySQL
echo [6/7] Checking MySQL installation...
mysql --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: MySQL is not installed or not in PATH
    echo Please install MySQL 8.0+ from https://mysql.com
) else (
    mysql --version
)
echo.

REM Generate secret key
echo [7/7] Generating secret key...
python -c "import secrets; print('FLASK_SECRET_KEY=' + secrets.token_hex(32))" > temp_key.txt
echo.

echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo Next steps:
echo 1. Edit .env file with your database credentials
echo 2. Create database: mysql -u root -p -e "CREATE DATABASE medilink;"
echo 3. Run schema: mysql -u root -p medilink < schema.sql
echo 4. Start server: python run.py
echo.
echo ============================================================

pause
