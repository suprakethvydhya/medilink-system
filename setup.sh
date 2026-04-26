#!/bin/bash
# MediLink Pharmacy Management System - Linux/Mac Setup Script

echo "============================================================"
echo "  MediLink Pharmacy Management System - Setup Script"
echo "============================================================"
echo ""

# Check Python installation
echo "[1/7] Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8+ first"
    exit 1
fi
python3 --version
echo ""

# Create virtual environment
echo "[2/7] Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created successfully"
else
    echo "Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "[3/7] Activating virtual environment..."
source venv/bin/activate
echo ""

# Install dependencies
echo "[4/7] Installing dependencies..."
pip install -r requirements.txt
echo ""

# Copy environment file
echo "[5/7] Setting up environment file..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ".env file created - Please edit with your database credentials"
else
    echo ".env file already exists"
fi
echo ""

# Check MySQL
echo "[6/7] Checking MySQL installation..."
if ! command -v mysql &> /dev/null; then
    echo "WARNING: MySQL is not installed or not in PATH"
    echo "Please install MySQL 8.0+"
else
    mysql --version
fi
echo ""

# Generate secret key
echo "[7/7] Generating secret key..."
python -c "import secrets; print('FLASK_SECRET_KEY=' + secrets.token_hex(32))"
echo ""

echo "============================================================"
echo "  Setup Complete!"
echo "============================================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your database credentials"
echo "2. Create database: mysql -u root -p -e 'CREATE DATABASE medilink;'"
echo "3. Run schema: mysql -u root -p medilink < schema.sql"
echo "4. Start server: python run.py"
echo ""
echo "============================================================"
