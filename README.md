# MediLink - Pharmacy Management System

A comprehensive web-based pharmacy management system built with Flask and MySQL, designed to streamline interactions between doctors, patients, and pharmacists.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![Flask](https://img.shields.io/badge/flask-3.0+-green.svg)
![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)

## Features

### Doctor
- View and manage appointments with real-time status updates
- Update appointment status (Scheduled → In Progress → Completed)
- Add clinical notes to appointments
- Write prescriptions for patients
- View prescription history with dispensing status from pharmacist
- Today's patient list with quick status actions

### Patient
- Book appointments with any doctor
- View upcoming and past appointments with pagination
- Track appointment status in real-time
- View prescriptions issued by doctors
- Monitor prescription dispensing status (Pending → Dispensed)
- Cancel upcoming appointments

### Pharmacist
- Manage medicine inventory (add, edit, delete, search)
- Low stock alerts and notifications (threshold: 10 units)
- Dispense prescriptions with automatic stock tracking
- View pending and dispensed prescriptions
- Filter prescriptions by status
- Live stock level display during dispensing
- Expiry date tracking

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Flask 3.0+ |
| Database | MySQL 8.0+ |
| Frontend | HTML5, CSS3, JavaScript |
| Security | Werkzeug password hashing, XSS prevention |
| ORM | Raw SQL with PyMySQL (parameterized queries) |

## Quick Start

### Prerequisites

- Python 3.8 or higher
- MySQL 8.0 or higher
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/suprakethvydhya/medilink-system.git
cd medilink-system/pharma_systm

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your database credentials
# Then run the schema to create tables
mysql -u root -p < schema.sql
```

### Configuration

Edit the `.env` file:

```env
FLASK_SECRET_KEY=your-secret-key-here
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your-password
DB_NAME=medilink
DB_PORT=3306
```

### Run the Application

```bash
# Using run.py (recommended)
python run.py

# Or directly
python app.py

# Or using Flask CLI
flask --app app run
```

Visit `http://localhost:5000` in your browser.

## Database Schema

### Tables

#### users
Stores user accounts with role-based access.

| Column | Type | Description |
|--------|------|-------------|
| username | VARCHAR(50) | Primary key, unique identifier |
| password | VARCHAR(255) | PBKDF2:SHA256 hashed password |
| role | ENUM | 'doctor', 'patient', or 'pharmacist' |
| created_at | TIMESTAMP | Account creation time |
| is_active | BOOLEAN | Account status |

#### Appointment
Tracks patient appointments.

| Column | Type | Description |
|--------|------|-------------|
| Appointment_ID | INT | Auto-increment primary key |
| Patient_Name | VARCHAR(100) | Patient's full name |
| Doctor_Name | VARCHAR(100) | Doctor's full name |
| Symptoms | VARCHAR(200) | Patient symptoms |
| Date | DATE | Appointment date |
| Status | VARCHAR(20) | Scheduled, In Progress, Completed, Cancelled |
| Notes | TEXT | Doctor's clinical notes |

#### Prescription
Stores prescriptions written by doctors.

| Column | Type | Description |
|--------|------|-------------|
| Prescription_ID | INT | Auto-increment primary key |
| Doctor_Name | VARCHAR(100) | Prescribing doctor |
| Patient_Name | VARCHAR(100) | Patient's full name |
| Medicine_Name | VARCHAR(100) | Prescribed medicine |
| Dosage | VARCHAR(200) | Dosage instructions |
| Status | VARCHAR(20) | Pending or Dispensed |

#### Medicine
Pharmacy inventory.

| Column | Type | Description |
|--------|------|-------------|
| Medicine_ID | INT | Primary key (user-defined) |
| Medicine_Name | VARCHAR(100) | Medicine name |
| Expiry_Date | DATE | Expiration date |
| Stock | INT | Available units |
| Price | DECIMAL(10,2) | Price in local currency |

## Usage Guide

### Creating Accounts

1. Navigate to the signup page
2. Choose a role: Doctor, Patient, or Pharmacist
3. Username: 3-50 characters (letters, numbers, underscores only)
4. Password: Min 8 characters with at least one letter and one number

### Doctor Workflow

1. **Login** → Access doctor dashboard
2. **View Stats** → See appointment and prescription counts
3. **Update Status** → Mark patients as "In Progress" then "Completed"
4. **Write Prescription** → Click "New Prescription", fill details
5. **Track Dispensing** → See when pharmacist dispenses medicine

### Patient Workflow

1. **Login** → Access patient dashboard
2. **Book Appointment** → Select doctor, date, add symptoms
3. **View Appointments** → See upcoming visits with status
4. **Check Prescriptions** → Monitor when ready for pickup
5. **Cancel** → Cancel upcoming appointments if needed

### Pharmacist Workflow

1. **Login** → Access pharmacist dashboard
2. **Check Alerts** → View low stock items
3. **Dispense** → Process pending prescriptions
4. **Manage Inventory** → Add/edit medicines
5. **Search** → Find medicines by name

## API Endpoints

### Authentication

| Method | Route | Description |
|--------|-------|-------------|
| GET/POST | /login | User login |
| GET/POST | /signup | User registration |
| GET | /logout | User logout |

### Doctor Routes

| Method | Route | Description |
|--------|-------|-------------|
| GET | /doctor | Dashboard |
| GET | /view_appointments | List all appointments |
| GET/POST | /edit_appointment/<id> | Edit appointment |
| POST | /delete_appointment | Bulk delete |
| POST | /update_appointment_status/<id> | Update status |
| GET/POST | /add_prescription | Write prescription |
| GET | /view_prescriptions | View all prescriptions |

### Patient Routes

| Method | Route | Description |
|--------|-------|-------------|
| GET | /patient | Dashboard |
| GET/POST | /book_appointment | Book appointment |
| GET | /my_appointments | View appointments |
| POST | /cancel_appointment/<id> | Cancel appointment |
| GET | /my_prescriptions | View prescriptions |

### Pharmacist Routes

| Method | Route | Description |
|--------|-------|-------------|
| GET | /pharmacist | Dashboard |
| GET | /view_medicine | Inventory |
| GET/POST | /add_medicine | Add medicine |
| GET/POST | /edit_medicine/<id> | Edit medicine |
| POST | /delete_medicine | Bulk delete |
| GET | /pharmacy_prescriptions | Dispensing queue |
| POST | /dispense/<id> | Dispense prescription |

### API Routes (JSON)

| Method | Route | Description |
|--------|-------|-------------|
| GET | /api/medicine/low-stock | Get low stock medicines |
| GET | /api/appointments/today | Get today's appointments |

## Project Structure

```
pharma_systm/
├── app.py                    # Main Flask application
├── db.py                     # Database connection
├── config.py                 # Configuration management
├── validators.py             # Input validation functions
├── utils.py                  # Utility functions
├── models.py                 # Database schema definitions
├── run.py                    # Application entry point
├── requirements.txt          # Python dependencies
├── schema.sql                # Database schema
├── .env                      # Environment variables (not committed)
├── .env.example              # Example environment file
├── .gitignore                # Git ignore rules
├── README.md                 # This file
├── CHANGELOG.md              # Version history
├── CONTRIBUTING.md           # Contribution guidelines
├── static/
│   └── CSS/
│       └── style.css         # Application styles
├── templates/
│   ├── base.html             # Base template
│   ├── login.html            # Login page
│   ├── signup.html           # Registration page
│   ├── doctor.html           # Doctor dashboard
│   ├── patient.html          # Patient dashboard
│   ├── pharmacist.html       # Pharmacist dashboard
│   ├── appointment.html      # Book appointment form
│   ├── edit_appointment.html # Edit appointment form
│   ├── add_prescription.html # Add prescription form
│   ├── view_prescriptions.html
│   ├── my_prescriptions.html
│   ├── add_medicine.html     # Add medicine form
│   ├── edit_medicine.html    # Edit medicine form
│   ├── view_medicine.html    # Medicine inventory
│   ├── pharmacy_prescriptions.html
│   ├── my_appointments.html  # Patient appointments
│   ├── view_appointments.html
│   ├── 404.html              # Not found error
│   ├── 403.html              # Access denied
│   └── 500.html              # Server error
└── tests/
    ├── __init__.py
    └── test_app.py           # Test suite
```

## Security Features

- **Password Hashing**: PBKDF2:SHA256 with configurable iterations
- **XSS Prevention**: Input sanitization removes HTML/script tags
- **SQL Injection Prevention**: All queries use parameterized statements
- **Role-Based Access**: Routes protected by role verification
- **Session Management**: Secure session handling with login tracking
- **Input Validation**: Length limits, format checks, type validation
- **Audit Logging**: Track all system actions (configurable)

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test class
pytest tests/test_app.py::TestValidators -v
```

## Troubleshooting

### Database Connection Failed

```
Check your .env file:
- DB_HOST should be 'localhost' for local development
- DB_USER and DB_PASSWORD must match your MySQL credentials
- Ensure MySQL service is running: mysql --version
```

### Module Not Found

```bash
pip install -r requirements.txt
```

### Port Already in Use

```python
# In run.py or app.py, change the port:
app.run(debug=True, port=5001)
```

### Session Issues

Clear browser cookies or try incognito mode.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing issues for similar problems
- Review the documentation and changelog

## Acknowledgments

Built with ❤️ using Flask & MySQL

---

**Version**: 2.1.0  
**Last Updated**: 2026-04-26  
**Maintainer**: MediLink Team
