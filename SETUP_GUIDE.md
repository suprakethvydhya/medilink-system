# MediLink Setup Guide

Complete step-by-step setup instructions for MediLink Pharmacy Management System.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Database Setup](#database-setup)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [First Login](#first-login)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

| Software | Version | Download |
|----------|---------|----------|
| Python | 3.8+ | https://python.org |
| MySQL | 8.0+ | https://mysql.com |
| Git | Latest | https://git-scm.com |

### Verify Installation

```bash
# Check Python version
python --version

# Check MySQL version
mysql --version

# Check Git version
git --version
```

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/suprakethvydhya/medilink-system.git
cd medilink-system/pharma_systm
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Verify Installation

```bash
python -c "import flask; print(f'Flask {flask.__version__}')"
python -c "import pymysql; print(f'PyMySQL {pymysql.__version__}')"
```

## Database Setup

### Option A: Using MySQL Command Line

```bash
# Login to MySQL
mysql -u root -p

# Create database
CREATE DATABASE medilink;

# Use database
USE medilink;

# Run schema
source schema.sql;

# Exit
exit;
```

### Option B: Using MySQL Workbench

1. Open MySQL Workbench
2. Connect to your MySQL server
3. Create new schema: `medilink`
4. Open `schema.sql` file
5. Execute the script

### Option C: One-liner

```bash
mysql -u root -p < schema.sql
```

### Verify Database Setup

```bash
mysql -u root -p -e "USE medilink; SHOW TABLES;"
```

Expected output:
```
+---------------------+
| Tables_in_medilink  |
+---------------------+
| Appointment         |
| Medicine            |
| Prescription        |
| users               |
| audit_log           |
+---------------------+
```

## Configuration

### Step 1: Copy Environment File

```bash
cp .env.example .env
```

### Step 2: Generate Secret Key

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Step 3: Edit .env File

Open `.env` and update:

```env
# Flask Security
FLASK_SECRET_KEY=<paste-generated-key-here>
FLASK_DEBUG=True  # Set False in production

# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=<your-mysql-password>
DB_NAME=medilink
```

### Step 4: Verify Configuration

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('DB:', os.getenv('DB_NAME'))"
```

## Running the Application

### Development Mode

```bash
# Using run.py (recommended)
python run.py

# Using Flask CLI
flask --app app run

# Using Python directly
python app.py
```

### Production Mode

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

### Access the Application

Open your browser and navigate to:
```
http://localhost:5000
```

## First Login

### Create Test Users

1. Go to `/signup`
2. Create a doctor account:
   - Username: `dr_test`
   - Password: `Doctor123`
   - Role: Doctor

3. Create a patient account:
   - Username: `patient_test`
   - Password: `Patient123`
   - Role: Patient

4. Create a pharmacist account:
   - Username: `pharm_test`
   - Password: `Pharm123`
   - Role: Pharmacist

### Test Workflow

1. **As Doctor**:
   - View dashboard
   - Add a prescription

2. **As Patient**:
   - Book an appointment
   - View prescriptions

3. **As Pharmacist**:
   - Add medicine to inventory
   - Dispense prescription

## Troubleshooting

### Issue: Cannot connect to database

**Solution:**
```bash
# Check MySQL is running
# Windows
net start mysql

# Linux/Mac
sudo systemctl status mysql
```

### Issue: Module not found

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Issue: Port 5000 already in use

**Solution:**
```bash
# Find process using port 5000
# Windows
netstat -ano | findstr :5000

# Linux/Mac
lsof -i :5000

# Kill the process or change port in app.py
```

### Issue: .env not loading

**Solution:**
```python
# Add this at the top of app.py
import os
from dotenv import load_dotenv
load_dotenv()
print(f"SECRET_KEY set: {bool(os.getenv('FLASK_SECRET_KEY'))}")
```

### Issue: Template not found

**Solution:**
```bash
# Verify template directory
ls templates/

# Check Flask can find templates
python -c "from app import app; print(app.template_folder)"
```

## Next Steps

- [ ] Add sample data for testing
- [ ] Configure email notifications (optional)
- [ ] Set up HTTPS for production
- [ ] Configure backup strategy
- [ ] Review security settings

## Support

If you encounter issues:
1. Check this guide thoroughly
2. Review error logs (`medilink.log`)
3. Search existing GitHub issues
4. Create a new issue with details

---

**Happy coding!** 🏥💊
