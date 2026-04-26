-- MediLink Pharmacy Management System - Database Schema
-- Run this script to create all required tables

-- Create database (uncomment if needed)
-- CREATE DATABASE IF NOT EXISTS medilink;
USE medilink;

-- ── Users Table ──────────────────────────────────────────────────────────────
-- Stores user accounts with role-based access (doctor, patient, pharmacist)
CREATE TABLE IF NOT EXISTS users (
    username VARCHAR(50) PRIMARY KEY,
    password VARCHAR(255) NOT NULL COMMENT 'PBKDF2:SHA256 hashed password',
    role ENUM('doctor', 'patient', 'pharmacist') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_role (role),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── Appointments Table ───────────────────────────────────────────────────────
-- Tracks patient appointments with doctors
CREATE TABLE IF NOT EXISTS Appointment (
    Appointment_ID INT AUTO_INCREMENT PRIMARY KEY,
    Patient_Name VARCHAR(100) NOT NULL,
    Doctor_Name VARCHAR(100) NOT NULL,
    Symptoms VARCHAR(200) COMMENT 'Patient symptoms description',
    Date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    Status VARCHAR(20) DEFAULT 'Scheduled' COMMENT 'Scheduled, In Progress, Completed, Cancelled',
    Notes TEXT COMMENT 'Doctor notes and observations',
    INDEX idx_patient (Patient_Name),
    INDEX idx_doctor (Doctor_Name),
    INDEX idx_date (Date),
    INDEX idx_status (Status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── Prescriptions Table ──────────────────────────────────────────────────────
-- Stores prescriptions written by doctors
CREATE TABLE IF NOT EXISTS Prescription (
    Prescription_ID INT AUTO_INCREMENT PRIMARY KEY,
    Doctor_Name VARCHAR(100) NOT NULL,
    Patient_Name VARCHAR(100) NOT NULL,
    Medicine_Name VARCHAR(100) NOT NULL,
    Dosage VARCHAR(200) COMMENT 'Dosage instructions',
    Notes TEXT COMMENT 'Clinical notes',
    Date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    Status VARCHAR(20) DEFAULT 'Pending' COMMENT 'Pending, Dispensed',
    dispensed_at TIMESTAMP NULL COMMENT 'When prescription was dispensed',
    INDEX idx_doctor (Doctor_Name),
    INDEX idx_patient (Patient_Name),
    INDEX idx_status (Status),
    INDEX idx_date (Date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── Medicines Table ──────────────────────────────────────────────────────────
-- Medicine inventory managed by pharmacists
CREATE TABLE IF NOT EXISTS Medicine (
    Medicine_ID INT PRIMARY KEY,
    Medicine_Name VARCHAR(100) NOT NULL,
    Expiry_Date DATE NOT NULL,
    Stock INT NOT NULL DEFAULT 0,
    Price DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (Medicine_Name),
    INDEX idx_stock (Stock),
    INDEX idx_expiry (Expiry_Date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── Audit Log Table ──────────────────────────────────────────────────────────
-- Tracks all system actions for security and compliance
CREATE TABLE IF NOT EXISTS audit_log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50),
    action VARCHAR(100) NOT NULL COMMENT 'Action performed (CREATE, UPDATE, DELETE, LOGIN, etc.)',
    table_name VARCHAR(50) COMMENT 'Affected table',
    record_id INT COMMENT 'Affected record ID',
    details TEXT COMMENT 'Additional details in JSON format',
    ip_address VARCHAR(45) COMMENT 'User IP address',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (username),
    INDEX idx_action (action),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── Sample Data (Optional - for testing) ─────────────────────────────────────
-- Uncomment to insert test data

-- Test users (passwords are hashed - these are examples only)
-- INSERT INTO users (username, password, role) VALUES
-- ('dr_smith', 'pbkdf2:sha256:260000$...', 'doctor'),
-- ('patient1', 'pbkdf2:sha256:260000$...', 'patient'),
-- ('pharm_john', 'pbkdf2:sha256:260000$...', 'pharmacist');

-- Test medicines
-- INSERT INTO Medicine (Medicine_ID, Medicine_Name, Expiry_Date, Stock, Price) VALUES
-- (1, 'Paracetamol 500mg', '2027-12-31', 100, 5.00),
-- (2, 'Amoxicillin 250mg', '2027-06-30', 50, 12.50),
-- (3, 'Ibuprofen 400mg', '2026-08-15', 75, 8.00);

-- ── Useful Views ─────────────────────────────────────────────────────────────

-- View: Low stock medicines
CREATE OR REPLACE VIEW low_stock_medicines AS
SELECT Medicine_ID, Medicine_Name, Stock, Price, Expiry_Date
FROM Medicine
WHERE Stock <= 10
ORDER BY Stock ASC;

-- View: Pending prescriptions
CREATE OR REPLACE VIEW pending_prescriptions AS
SELECT Prescription_ID, Doctor_Name, Patient_Name, Medicine_Name, Dosage, Notes, Date
FROM Prescription
WHERE Status = 'Pending'
ORDER BY Date DESC;

-- View: Today's appointments
CREATE OR REPLACE VIEW todays_appointments AS
SELECT * FROM Appointment
WHERE Date = CURDATE()
ORDER BY Appointment_ID ASC;

-- ── Maintenance Queries ──────────────────────────────────────────────────────

-- Delete expired medicines (run periodically)
-- DELETE FROM Medicine WHERE Expiry_Date < CURDATE();

-- Archive completed appointments older than 1 year
-- CREATE TABLE Appointment_Archive LIKE Appointment;
-- INSERT INTO Appointment_Archive SELECT * FROM Appointment
-- WHERE Status = 'Completed' AND Date < DATE_SUB(CURDATE(), INTERVAL 1 YEAR);
-- DELETE FROM Appointment WHERE Status = 'Completed' AND Date < DATE_SUB(CURDATE(), INTERVAL 1 YEAR);
