"""
MediLink - Pharmacy Management System
A comprehensive web-based pharmacy management system connecting doctors, patients, and pharmacists.

Features:
- Doctor: Appointments, prescriptions, patient management
- Patient: Book appointments, view prescriptions, track status
- Pharmacist: Medicine inventory, prescription dispensing, stock management

Security: Password hashing (PBKDF2:SHA256), XSS prevention, SQL injection prevention, role-based access
"""

import os
import re
import logging
from datetime import date, datetime
from functools import wraps
from typing import Optional, Tuple, Dict, Any

from dotenv import load_dotenv
from flask import (Flask, flash, redirect, render_template,
                   request, session, url_for, jsonify)
from werkzeug.security import check_password_hash, generate_password_hash

from db import db, cursor
from validators import (
    validate_username, validate_password, validate_name,
    validate_date_not_past, validate_positive_int, validate_non_negative_int,
    validate_positive_float, validate_medicine_name, validate_dosage,
    validate_notes, validate_role, validate_appointment_limit
)
from utils import (
    logger, sanitize_text, safe_int, safe_float, get_pagination_params,
    calculate_pagination, login_required, LOW_STOCK_THRESHOLD,
    MAX_PAGE_SIZE, DEFAULT_PAGE_SIZE, MAX_APPOINTMENTS_PER_DAY,
    format_currency, get_stock_status
)

load_dotenv()

# ── Flask Application Setup ─────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY is not set. Check your .env file.")

# ── Error Handlers ──────────────────────────────────────────────────────────────


@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors - page not found."""
    logger.warning(f"404 error: {request.path}")
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors - internal server error."""
    logger.error(f"500 error: {e}", exc_info=True)
    try:
        db.rollback()
    except Exception as rollback_error:
        logger.error(f"Rollback failed: {rollback_error}")
    return render_template('500.html'), 500


@app.errorhandler(403)
def forbidden(e):
    """Handle 403 errors - forbidden access."""
    return render_template('403.html'), 403


# ── Home Routes ─────────────────────────────────────────────────────────────────


@app.route('/')
def index():
    """Root route - redirect to login or dashboard based on session."""
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


# ── Authentication Routes ───────────────────────────────────────────────────────


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if 'user' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = sanitize_text(request.form.get('username', ''), 50)
        password = request.form.get('password', '')

        if not username or not password:
            flash('Both username and password are required.', 'danger')
            return render_template('login.html')

        try:
            cursor.execute(
                "SELECT password, role FROM users WHERE username = %s",
                (username,)
            )
            row = cursor.fetchone()

            if row and check_password_hash(row['password'], password):
                session.clear()
                session['user'] = username
                session['role'] = row['role']
                session['login_time'] = datetime.now().isoformat()
                logger.info(f"User {username} logged in successfully")
                flash(f'Welcome back, {username}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                logger.warning(f"Failed login attempt for username: {username}")
                flash('Invalid username or password.', 'danger')
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('An error occurred during login. Please try again.', 'danger')

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle user registration."""
    if 'user' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = sanitize_text(request.form.get('username', ''), 50)
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        role = request.form.get('role', '').strip()

        # Validate all fields are present
        if not all([username, password, confirm, role]):
            flash('All fields are required.', 'danger')
            return render_template('signup.html')

        # Validate username
        is_valid, msg = validate_username(username)
        if not is_valid:
            flash(msg, 'danger')
            return render_template('signup.html')

        # Validate password
        is_valid, msg = validate_password(password)
        if not is_valid:
            flash(msg, 'danger')
            return render_template('signup.html')

        # Validate role
        is_valid, msg = validate_role(role)
        if not is_valid:
            flash(msg, 'danger')
            return render_template('signup.html')

        # Check passwords match
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('signup.html')

        try:
            # Check username uniqueness
            cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                flash('Username already taken. Please choose another.', 'danger')
                return render_template('signup.html')

            hashed = generate_password_hash(password, method='pbkdf2:sha256')
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                (username, hashed, role)
            )
            db.commit()
            logger.info(f"New user registered: {username} ({role})")
            flash('Account created! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            logger.error(f"Signup error: {e}")
            db.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')

    return render_template('signup.html')


@app.route('/logout')
def logout():
    """Handle user logout."""
    username = session.get('user', 'User')
    session.clear()
    logger.info(f"User {username} logged out")
    flash(f'Goodbye, {username}. You have been logged out.', 'info')
    return redirect(url_for('login'))


# ── Dashboard Route ─────────────────────────────────────────────────────────────


@app.route('/dashboard')
def dashboard():
    """Redirect to role-specific dashboard."""
    if 'user' not in session:
        return redirect(url_for('login'))
    role = session.get('role')
    return redirect(url_for(role))


# ── Doctor Routes ───────────────────────────────────────────────────────────────


@app.route('/doctor')
@login_required(role='doctor')
def doctor():
    """Doctor dashboard with appointment and prescription statistics."""
    user = session['user']

    try:
        # Appointment status counts
        cursor.execute("SELECT COUNT(*) AS cnt FROM Appointment")
        appt_count = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM Appointment WHERE Status = 'Scheduled'")
        scheduled_count = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM Appointment WHERE Status = 'In Progress'")
        in_progress_count = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM Appointment WHERE Status = 'Completed'")
        completed_count = cursor.fetchone()['cnt']

        # Today's appointments
        cursor.execute(
            "SELECT * FROM Appointment WHERE Date = CURDATE() ORDER BY Appointment_ID ASC"
        )
        todays_patients = cursor.fetchall()

        # Prescription counts
        cursor.execute("SELECT COUNT(*) AS cnt FROM Prescription WHERE Doctor_Name = %s", (user,))
        rx_count = cursor.fetchone()['cnt']

        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM Prescription WHERE Doctor_Name = %s AND Status = 'Pending'",
            (user,)
        )
        rx_pending = cursor.fetchone()['cnt']

        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM Prescription WHERE Doctor_Name = %s AND Status = 'Dispensed'",
            (user,)
        )
        rx_dispensed = cursor.fetchone()['cnt']

        # Recent prescriptions
        cursor.execute(
            "SELECT * FROM Prescription WHERE Doctor_Name = %s ORDER BY Date DESC LIMIT 5",
            (user,)
        )
        recent_prescriptions = cursor.fetchall()

        return render_template(
            'doctor.html',
            appt_count=appt_count,
            scheduled_count=scheduled_count,
            in_progress_count=in_progress_count,
            completed_count=completed_count,
            todays_patients=todays_patients,
            rx_count=rx_count,
            rx_pending=rx_pending,
            rx_dispensed=rx_dispensed,
            recent_prescriptions=recent_prescriptions
        )
    except Exception as e:
        logger.error(f"Error in doctor dashboard: {e}")
        db.rollback()
        flash('An error occurred loading your dashboard. Please try again.', 'danger')
        return redirect(url_for('dashboard'))


@app.route('/view_appointments')
@login_required(role='doctor')
def view_appointments():
    """View all appointments with pagination and filtering."""
    page, per_page = get_pagination_params(request)
    offset = (page - 1) * per_page

    # Optional status filter
    status_filter = request.args.get('filter', '').strip()

    try:
        if status_filter and status_filter in ('Scheduled', 'In Progress', 'Completed'):
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM Appointment WHERE Status = %s",
                (status_filter,)
            )
            total = cursor.fetchone()['cnt']

            cursor.execute(
                "SELECT * FROM Appointment WHERE Status = %s ORDER BY Date DESC LIMIT %s OFFSET %s",
                (status_filter, per_page, offset)
            )
        else:
            cursor.execute("SELECT COUNT(*) AS cnt FROM Appointment")
            total = cursor.fetchone()['cnt']

            cursor.execute(
                "SELECT * FROM Appointment ORDER BY Date DESC LIMIT %s OFFSET %s",
                (per_page, offset)
            )

        appointments = cursor.fetchall()
        pagination = calculate_pagination(total, per_page, page)

        return render_template(
            'view_appointments.html',
            appointments=appointments,
            page=pagination['current_page'],
            total_pages=pagination['total_pages'],
            current_filter=status_filter
        )
    except Exception as e:
        logger.error(f"Error loading appointments: {e}")
        db.rollback()
        flash('An error occurred loading appointments.', 'danger')
        return redirect(url_for('doctor'))


@app.route('/edit_appointment/<int:appt_id>', methods=['GET', 'POST'])
@login_required(role='doctor')
def edit_appointment(appt_id):
    """Edit appointment details."""
    try:
        cursor.execute(
            "SELECT * FROM Appointment WHERE Appointment_ID = %s", (appt_id,)
        )
        appt = cursor.fetchone()

        if not appt:
            flash('Appointment not found.', 'danger')
            return redirect(url_for('view_appointments'))

        if request.method == 'POST':
            pname = sanitize_text(request.form.get('pname', ''), 100)
            dname = sanitize_text(request.form.get('dname', ''), 100)
            appt_date = request.form.get('date', '').strip()
            symptoms = sanitize_text(request.form.get('symptoms', ''), 200)

            # Validate names
            is_valid, msg = validate_name(pname, "Patient name")
            if not is_valid:
                flash(msg, 'danger')
                return render_template('edit_appointment.html', appt=appt, today=date.today().isoformat())

            is_valid, msg = validate_name(dname, "Doctor name")
            if not is_valid:
                flash(msg, 'danger')
                return render_template('edit_appointment.html', appt=appt, today=date.today().isoformat())

            # Validate date
            is_valid, msg = validate_date_not_past(appt_date)
            if not is_valid:
                flash(msg, 'danger')
                return render_template('edit_appointment.html', appt=appt, today=date.today().isoformat())

            cursor.execute(
                "UPDATE Appointment SET Patient_Name=%s, Doctor_Name=%s, Date=%s, Symptoms=%s "
                "WHERE Appointment_ID=%s",
                (pname, dname, appt_date, symptoms, appt_id)
            )
            db.commit()
            logger.info(f"Appointment updated: ID {appt_id}")
            flash('Appointment updated successfully.', 'success')
            return redirect(url_for('view_appointments'))

        return render_template('edit_appointment.html', appt=appt, today=date.today().isoformat())

    except Exception as e:
        logger.error(f"Error editing appointment {appt_id}: {e}")
        db.rollback()
        flash('An error occurred while updating appointment.', 'danger')
        return redirect(url_for('view_appointments'))


@app.route('/delete_appointment', methods=['POST'])
@login_required(role='doctor')
def delete_appointment():
    """Delete selected appointments."""
    raw_ids = request.form.getlist('delete_ids[]')

    # Validate IDs
    validated = []
    for rid in raw_ids:
        try:
            validated.append(int(rid))
        except ValueError:
            flash(f'Invalid ID "{rid}" skipped.', 'warning')

    try:
        for appt_id in validated:
            cursor.execute(
                "DELETE FROM Appointment WHERE Appointment_ID = %s", (appt_id,)
            )
        db.commit()
        logger.info(f"Deleted {len(validated)} appointments")
        flash(f'{len(validated)} appointment(s) deleted.', 'success')
    except Exception as e:
        logger.error(f"Error deleting appointments: {e}")
        db.rollback()
        flash('An error occurred while deleting appointments.', 'danger')

    return redirect(url_for('view_appointments'))


@app.route('/update_appointment_status/<int:appt_id>', methods=['POST'])
@login_required(role='doctor')
def update_appointment_status(appt_id):
    """Update appointment status and notes."""
    new_status = request.form.get('status', '').strip()
    notes = sanitize_text(request.form.get('notes', ''), 500)

    valid_statuses = ('Scheduled', 'In Progress', 'Completed')
    if new_status not in valid_statuses:
        flash('Invalid status.', 'danger')
        return redirect(url_for('view_appointments'))

    try:
        cursor.execute(
            "SELECT Appointment_ID FROM Appointment WHERE Appointment_ID = %s", (appt_id,)
        )
        if not cursor.fetchone():
            flash('Appointment not found.', 'danger')
            return redirect(url_for('view_appointments'))

        cursor.execute(
            "UPDATE Appointment SET Status = %s, Notes = %s WHERE Appointment_ID = %s",
            (new_status, notes, appt_id)
        )
        db.commit()

        status_labels = {
            'Scheduled': 'rescheduled',
            'In Progress': 'marked In Progress',
            'Completed': 'marked as Completed'
        }
        logger.info(f"Appointment {appt_id} {status_labels[new_status]}")
        flash(f'Appointment #{appt_id} {status_labels[new_status]}.', 'success')

    except Exception as e:
        logger.error(f"Error updating appointment status {appt_id}: {e}")
        db.rollback()
        flash('An error occurred while updating status.', 'danger')

    return redirect(url_for('view_appointments'))


@app.route('/add_prescription', methods=['GET', 'POST'])
@login_required(role='doctor')
def add_prescription():
    """Write a new prescription."""
    if request.method == 'POST':
        doctor = sanitize_text(request.form.get('doctor', ''), 100)
        patient = sanitize_text(request.form.get('patient', ''), 100)
        medicine = sanitize_text(request.form.get('medicine', ''), 100)
        dosage = sanitize_text(request.form.get('dosage', ''), 200)
        notes = sanitize_text(request.form.get('notes', ''), 500)
        rx_date = request.form.get('date', '').strip()

        # Validate required fields
        if not all([doctor, patient, medicine, rx_date]):
            flash('Doctor, patient, medicine, and date are required.', 'danger')
            return render_template('add_prescription.html')

        # Validate names
        is_valid, msg = validate_name(doctor, "Doctor name")
        if not is_valid:
            flash(msg, 'danger')
            return render_template('add_prescription.html')

        is_valid, msg = validate_name(patient, "Patient name")
        if not is_valid:
            flash(msg, 'danger')
            return render_template('add_prescription.html')

        # Validate medicine name
        is_valid, msg = validate_medicine_name(medicine)
        if not is_valid:
            flash(msg, 'danger')
            return render_template('add_prescription.html')

        # Validate date
        is_valid, msg = validate_date_not_past(rx_date)
        if not is_valid:
            flash(msg, 'danger')
            return render_template('add_prescription.html')

        # Validate optional fields
        is_valid, msg = validate_dosage(dosage)
        if not is_valid:
            flash(msg, 'danger')
            return render_template('add_prescription.html')

        is_valid, msg = validate_notes(notes)
        if not is_valid:
            flash(msg, 'danger')
            return render_template('add_prescription.html')

        try:
            cursor.execute(
                "INSERT INTO Prescription "
                "(Doctor_Name, Patient_Name, Medicine_Name, Dosage, Notes, Date, Status) "
                "VALUES (%s, %s, %s, %s, %s, %s, 'Pending')",
                (doctor, patient, medicine, dosage, notes, rx_date)
            )
            db.commit()
            logger.info(f"Prescription added: {medicine} for {patient} by Dr. {doctor}")
            flash('Prescription added successfully.', 'success')
            return redirect(url_for('doctor'))
        except Exception as e:
            logger.error(f"Error adding prescription: {e}")
            db.rollback()
            flash('An error occurred while adding prescription.', 'danger')

    return render_template('add_prescription.html', today=date.today().isoformat())


@app.route('/view_prescriptions')
@login_required(role='doctor')
def view_prescriptions():
    """View all prescriptions (doctor access)."""
    page, per_page = get_pagination_params(request)
    offset = (page - 1) * per_page

    try:
        cursor.execute("SELECT COUNT(*) AS cnt FROM Prescription")
        total = cursor.fetchone()['cnt']

        cursor.execute(
            "SELECT * FROM Prescription ORDER BY Date DESC LIMIT %s OFFSET %s",
            (per_page, offset)
        )
        prescriptions = cursor.fetchall()
        pagination = calculate_pagination(total, per_page, page)

        return render_template(
            'view_prescriptions.html',
            prescriptions=prescriptions,
            page=pagination['current_page'],
            total_pages=pagination['total_pages']
        )
    except Exception as e:
        logger.error(f"Error loading prescriptions: {e}")
        db.rollback()
        flash('An error occurred loading prescriptions.', 'danger')
        return redirect(url_for('doctor'))


# ── Patient Routes ──────────────────────────────────────────────────────────────


@app.route('/patient')
@login_required(role='patient')
def patient():
    """Patient dashboard with appointment and prescription overview."""
    user = session['user']

    try:
        # Counts
        cursor.execute("SELECT COUNT(*) AS cnt FROM Appointment WHERE Patient_Name = %s", (user,))
        appt_count = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM Prescription WHERE Patient_Name = %s", (user,))
        rx_count = cursor.fetchone()['cnt']

        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM Prescription WHERE Patient_Name = %s AND (Status = 'Pending' OR Status IS NULL)",
            (user,)
        )
        pending_rx = cursor.fetchone()['cnt']

        # Upcoming appointments (next 3)
        cursor.execute(
            "SELECT * FROM Appointment WHERE Patient_Name = %s AND Date >= CURDATE() "
            "AND (Status IS NULL OR Status != 'Completed') ORDER BY Date ASC LIMIT 3",
            (user,)
        )
        upcoming_appts = cursor.fetchall()

        # Recent prescriptions
        cursor.execute(
            "SELECT * FROM Prescription WHERE Patient_Name = %s ORDER BY Date DESC LIMIT 3",
            (user,)
        )
        recent_rx = cursor.fetchall()

        return render_template(
            'patient.html',
            appt_count=appt_count,
            rx_count=rx_count,
            pending_rx=pending_rx,
            upcoming_appts=upcoming_appts,
            recent_rx=recent_rx
        )
    except Exception as e:
        logger.error(f"Error in patient dashboard: {e}")
        db.rollback()
        flash('An error occurred loading your dashboard. Please try again.', 'danger')
        return redirect(url_for('dashboard'))


@app.route('/book_appointment', methods=['GET', 'POST'])
@login_required(role='patient')
def book_appointment():
    """Book a new appointment."""
    if request.method == 'POST':
        pname = sanitize_text(request.form.get('pname', ''), 100)
        dname = sanitize_text(request.form.get('dname', ''), 100)
        appt_date = request.form.get('date', '').strip()
        symptoms = sanitize_text(request.form.get('symptoms', ''), 200)

        # Validate required fields
        if not all([pname, dname, appt_date]):
            flash('All fields are required.', 'danger')
            return render_template('appointment.html', today=date.today().isoformat())

        # Validate names
        is_valid, msg = validate_name(pname, "Patient name")
        if not is_valid:
            flash(msg, 'danger')
            return render_template('appointment.html', today=date.today().isoformat())

        is_valid, msg = validate_name(dname, "Doctor name")
        if not is_valid:
            flash(msg, 'danger')
            return render_template('appointment.html', today=date.today().isoformat())

        # Validate date
        is_valid, msg = validate_date_not_past(appt_date)
        if not is_valid:
            flash(msg, 'danger')
            return render_template('appointment.html', today=date.today().isoformat())

        try:
            # Check appointment limit for this date
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM Appointment WHERE Patient_Name = %s AND Date = %s",
                (pname, appt_date)
            )
            existing_count = cursor.fetchone()['cnt']

            is_valid, msg = validate_appointment_limit(existing_count, MAX_APPOINTMENTS_PER_DAY)
            if not is_valid:
                flash(msg, 'warning')
                return render_template('appointment.html', today=date.today().isoformat())

            cursor.execute(
                "INSERT INTO Appointment (Patient_Name, Doctor_Name, Date, Symptoms, Status) "
                "VALUES (%s, %s, %s, %s, 'Scheduled')",
                (pname, dname, appt_date, symptoms)
            )
            db.commit()
            logger.info(f"Appointment booked: {pname} with Dr. {dname} on {appt_date}")
            flash('Appointment booked successfully!', 'success')
            return redirect(url_for('patient'))

        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            db.rollback()
            flash('An error occurred while booking. Please try again.', 'danger')

    return render_template('appointment.html', today=date.today().isoformat())


@app.route('/my_appointments')
@login_required(role='patient')
def my_appointments():
    """View patient's own appointments."""
    page, per_page = get_pagination_params(request)
    offset = (page - 1) * per_page

    show = request.args.get('show', 'upcoming')  # upcoming | all
    user = session['user']

    try:
        if show == 'all':
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM Appointment WHERE Patient_Name = %s",
                (user,)
            )
            total = cursor.fetchone()['cnt']
            cursor.execute(
                "SELECT * FROM Appointment WHERE Patient_Name = %s "
                "ORDER BY Date DESC LIMIT %s OFFSET %s",
                (user, per_page, offset)
            )
        else:  # upcoming
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM Appointment WHERE Patient_Name = %s AND Date >= CURDATE()",
                (user,)
            )
            total = cursor.fetchone()['cnt']
            cursor.execute(
                "SELECT * FROM Appointment WHERE Patient_Name = %s "
                "AND Date >= CURDATE() ORDER BY Date ASC LIMIT %s OFFSET %s",
                (user, per_page, offset)
            )

        appointments = cursor.fetchall()
        pagination = calculate_pagination(total, per_page, page)

        return render_template(
            'my_appointments.html',
            appointments=appointments,
            page=pagination['current_page'],
            total_pages=pagination['total_pages'],
            show=show
        )
    except Exception as e:
        logger.error(f"Error loading appointments: {e}")
        db.rollback()
        flash('An error occurred loading your appointments.', 'danger')
        return redirect(url_for('patient'))


@app.route('/cancel_appointment/<int:appt_id>', methods=['POST'])
@login_required(role='patient')
def cancel_appointment(appt_id):
    """Cancel an upcoming appointment (patient can only cancel their own)."""
    user = session['user']

    try:
        # Verify appointment exists and belongs to this patient
        cursor.execute(
            "SELECT Appointment_ID, Status FROM Appointment "
            "WHERE Appointment_ID = %s AND Patient_Name = %s",
            (appt_id, user)
        )
        appt = cursor.fetchone()

        if not appt:
            flash('Appointment not found or access denied.', 'danger')
            return redirect(url_for('my_appointments'))

        if appt['Status'] == 'Completed':
            flash('Cannot cancel a completed appointment.', 'warning')
            return redirect(url_for('my_appointments'))

        cursor.execute(
            "UPDATE Appointment SET Status = 'Cancelled' WHERE Appointment_ID = %s",
            (appt_id,)
        )
        db.commit()
        logger.info(f"Appointment {appt_id} cancelled by {user}")
        flash('Appointment cancelled successfully.', 'success')

    except Exception as e:
        logger.error(f"Error cancelling appointment: {e}")
        db.rollback()
        flash('An error occurred while cancelling appointment.', 'danger')

    return redirect(url_for('my_appointments'))


@app.route('/my_prescriptions')
@login_required(role='patient')
def my_prescriptions():
    """View patient's own prescriptions."""
    page, per_page = get_pagination_params(request)
    offset = (page - 1) * per_page

    user = session['user']

    try:
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM Prescription WHERE Patient_Name = %s",
            (user,)
        )
        total = cursor.fetchone()['cnt']

        cursor.execute(
            "SELECT * FROM Prescription WHERE Patient_Name = %s "
            "ORDER BY Date DESC LIMIT %s OFFSET %s",
            (user, per_page, offset)
        )
        prescriptions = cursor.fetchall()
        pagination = calculate_pagination(total, per_page, page)

        return render_template(
            'my_prescriptions.html',
            prescriptions=prescriptions,
            page=pagination['current_page'],
            total_pages=pagination['total_pages']
        )
    except Exception as e:
        logger.error(f"Error loading prescriptions: {e}")
        db.rollback()
        flash('An error occurred loading your prescriptions.', 'danger')
        return redirect(url_for('patient'))


# ── Pharmacist Routes ───────────────────────────────────────────────────────────


@app.route('/pharmacist')
@login_required(role='pharmacist')
def pharmacist():
    """Pharmacist dashboard with inventory and prescription overview."""
    try:
        cursor.execute("SELECT COUNT(*) AS cnt FROM Medicine")
        med_count = cursor.fetchone()['cnt']

        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM Medicine WHERE Stock <= %s",
            (LOW_STOCK_THRESHOLD,)
        )
        low_stock_count = cursor.fetchone()['cnt']

        cursor.execute(
            "SELECT * FROM Medicine WHERE Stock <= %s ORDER BY Stock ASC LIMIT 5",
            (LOW_STOCK_THRESHOLD,)
        )
        low_stock_items = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) AS cnt FROM Prescription WHERE Status='Pending'")
        pending_count = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM Prescription WHERE Status='Dispensed'")
        dispensed_count = cursor.fetchone()['cnt']

        # Pending prescriptions
        cursor.execute(
            "SELECT * FROM Prescription WHERE Status = 'Pending' ORDER BY Date DESC LIMIT 5"
        )
        pending_prescriptions = cursor.fetchall()

        # Recent dispensing activity
        cursor.execute(
            "SELECT * FROM Prescription WHERE Status = 'Dispensed' ORDER BY Date DESC LIMIT 5"
        )
        recent_dispensed = cursor.fetchall()

        return render_template(
            'pharmacist.html',
            med_count=med_count,
            low_stock_count=low_stock_count,
            low_stock_items=low_stock_items,
            threshold=LOW_STOCK_THRESHOLD,
            pending_count=pending_count,
            dispensed_count=dispensed_count,
            pending_prescriptions=pending_prescriptions,
            recent_dispensed=recent_dispensed
        )
    except Exception as e:
        logger.error(f"Error in pharmacist dashboard: {e}")
        db.rollback()
        flash('An error occurred loading your dashboard.', 'danger')
        return redirect(url_for('dashboard'))


@app.route('/add_medicine', methods=['GET', 'POST'])
@login_required(role='pharmacist')
def add_medicine():
    """Add new medicine to inventory."""
    if request.method == 'POST':
        med_id = request.form.get('id', '').strip()
        name = sanitize_text(request.form.get('name', ''), 100)
        expiry = request.form.get('expiry', '').strip()
        stock = request.form.get('stock', '').strip()
        price = request.form.get('price', '').strip()

        # Validate required fields
        if not all([med_id, name, expiry, stock, price]):
            flash('All fields are required.', 'danger')
            return render_template('add_medicine.html')

        # Validate medicine ID
        is_valid, msg = validate_positive_int(med_id)
        if not is_valid:
            flash(msg, 'danger')
            return render_template('add_medicine.html')

        # Validate stock
        is_valid, msg = validate_positive_int(stock)
        if not is_valid:
            flash(msg, 'danger')
            return render_template('add_medicine.html')

        # Validate price
        is_valid, msg = validate_positive_float(price)
        if not is_valid:
            flash(msg, 'danger')
            return render_template('add_medicine.html')

        # Validate medicine name
        is_valid, msg = validate_medicine_name(name)
        if not is_valid:
            flash(msg, 'danger')
            return render_template('add_medicine.html')

        # Validate expiry date
        if not expiry:
            flash('Expiry date is required.', 'danger')
            return render_template('add_medicine.html')

        try:
            datetime.strptime(expiry, "%Y-%m-%d")
        except ValueError:
            flash('Invalid expiry date format. Use YYYY-MM-DD.', 'danger')
            return render_template('add_medicine.html')

        try:
            # Check for duplicate Medicine_ID
            cursor.execute(
                "SELECT Medicine_ID FROM Medicine WHERE Medicine_ID = %s", (int(med_id),)
            )
            if cursor.fetchone():
                flash(f'Medicine ID {med_id} already exists. Use a unique ID.', 'danger')
                return render_template('add_medicine.html')

            cursor.execute(
                "INSERT INTO Medicine (Medicine_ID, Medicine_Name, Expiry_Date, Stock, Price) "
                "VALUES (%s, %s, %s, %s, %s)",
                (int(med_id), name, expiry, int(stock), float(price))
            )
            db.commit()
            logger.info(f"Medicine added: {name} (ID: {med_id})")
            flash(f'Medicine "{name}" added successfully.', 'success')
            return redirect(url_for('pharmacist'))

        except Exception as e:
            logger.error(f"Error adding medicine: {e}")
            db.rollback()
            flash('An error occurred while adding medicine.', 'danger')

    return render_template('add_medicine.html')


@app.route('/view_medicine')
@login_required(role='pharmacist')
def view_medicine():
    """View medicine inventory with search and pagination."""
    page, per_page = get_pagination_params(request)
    offset = (page - 1) * per_page

    search = sanitize_text(request.args.get('search', ''), 100)

    try:
        if search:
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM Medicine WHERE Medicine_Name LIKE %s",
                (f'%{search}%',)
            )
            total = cursor.fetchone()['cnt']
            cursor.execute(
                "SELECT * FROM Medicine WHERE Medicine_Name LIKE %s "
                "ORDER BY Medicine_Name LIMIT %s OFFSET %s",
                (f'%{search}%', per_page, offset)
            )
        else:
            cursor.execute("SELECT COUNT(*) AS cnt FROM Medicine")
            total = cursor.fetchone()['cnt']
            cursor.execute(
                "SELECT * FROM Medicine ORDER BY Medicine_Name LIMIT %s OFFSET %s",
                (per_page, offset)
            )

        medicines = cursor.fetchall()
        pagination = calculate_pagination(total, per_page, page)

        return render_template(
            'view_medicine.html',
            medicines=medicines,
            page=pagination['current_page'],
            total_pages=pagination['total_pages'],
            search=search,
            threshold=LOW_STOCK_THRESHOLD
        )
    except Exception as e:
        logger.error(f"Error loading medicine inventory: {e}")
        db.rollback()
        flash('An error occurred loading inventory.', 'danger')
        return redirect(url_for('pharmacist'))


@app.route('/edit_medicine/<int:med_id>', methods=['GET', 'POST'])
@login_required(role='pharmacist')
def edit_medicine(med_id):
    """Edit medicine details."""
    try:
        cursor.execute(
            "SELECT * FROM Medicine WHERE Medicine_ID = %s", (med_id,)
        )
        med = cursor.fetchone()

        if not med:
            flash('Medicine not found.', 'danger')
            return redirect(url_for('view_medicine'))

        if request.method == 'POST':
            name = sanitize_text(request.form.get('name', ''), 100)
            expiry = request.form.get('expiry', '').strip()
            stock = request.form.get('stock', '').strip()
            price = request.form.get('price', '').strip()

            # Validate required fields
            if not all([name, expiry, stock, price]):
                flash('All fields are required.', 'danger')
                return render_template('edit_medicine.html', med=med)

            # Validate medicine name
            is_valid, msg = validate_medicine_name(name)
            if not is_valid:
                flash(msg, 'danger')
                return render_template('edit_medicine.html', med=med)

            # Validate stock
            is_valid, msg = validate_non_negative_int(stock)
            if not is_valid:
                flash(msg, 'danger')
                return render_template('edit_medicine.html', med=med)

            # Validate price
            is_valid, msg = validate_positive_float(price)
            if not is_valid:
                flash(msg, 'danger')
                return render_template('edit_medicine.html', med=med)

            # Validate expiry date format
            try:
                datetime.strptime(expiry, "%Y-%m-%d")
            except ValueError:
                flash('Invalid expiry date format. Use YYYY-MM-DD.', 'danger')
                return render_template('edit_medicine.html', med=med)

            cursor.execute(
                "UPDATE Medicine SET Medicine_Name=%s, Expiry_Date=%s, Stock=%s, Price=%s "
                "WHERE Medicine_ID=%s",
                (name, expiry, int(stock), float(price), med_id)
            )
            db.commit()
            logger.info(f"Medicine updated: ID {med_id} - {name}")
            flash(f'Medicine "{name}" updated successfully.', 'success')
            return redirect(url_for('view_medicine'))

        return render_template('edit_medicine.html', med=med)

    except Exception as e:
        logger.error(f"Error editing medicine {med_id}: {e}")
        db.rollback()
        flash('An error occurred while updating medicine.', 'danger')
        return redirect(url_for('view_medicine'))


@app.route('/delete_medicine', methods=['POST'])
@login_required(role='pharmacist')
def delete_medicine():
    """Delete selected medicines."""
    raw_ids = request.form.getlist('delete_ids[]')

    # Validate IDs
    validated = []
    for rid in raw_ids:
        try:
            validated.append(int(rid))
        except ValueError:
            flash(f'Invalid ID "{rid}" skipped.', 'warning')

    try:
        for med_id in validated:
            cursor.execute(
                "DELETE FROM Medicine WHERE Medicine_ID = %s", (med_id,)
            )
        db.commit()
        logger.info(f"Deleted {len(validated)} medicines")
        flash(f'{len(validated)} medicine(s) deleted.', 'success')

    except Exception as e:
        logger.error(f"Error deleting medicines: {e}")
        db.rollback()
        flash('An error occurred while deleting medicines.', 'danger')

    return redirect(url_for('view_medicine'))


# ── Pharmacist: Prescription Dispensing ─────────────────────────────────────────


@app.route('/pharmacy_prescriptions')
@login_required(role='pharmacist')
def pharmacy_prescriptions():
    """View prescriptions for dispensing with stock checking."""
    page, per_page = get_pagination_params(request)
    offset = (page - 1) * per_page

    show = request.args.get('show', 'all')  # all | pending | dispensed

    try:
        if show == 'pending':
            cursor.execute("SELECT COUNT(*) AS cnt FROM Prescription WHERE Status='Pending'")
            total = cursor.fetchone()['cnt']
            cursor.execute(
                "SELECT * FROM Prescription WHERE Status='Pending' "
                "ORDER BY Date DESC LIMIT %s OFFSET %s",
                (per_page, offset)
            )
        elif show == 'dispensed':
            cursor.execute("SELECT COUNT(*) AS cnt FROM Prescription WHERE Status='Dispensed'")
            total = cursor.fetchone()['cnt']
            cursor.execute(
                "SELECT * FROM Prescription WHERE Status='Dispensed' "
                "ORDER BY Date DESC LIMIT %s OFFSET %s",
                (per_page, offset)
            )
        else:
            cursor.execute("SELECT COUNT(*) AS cnt FROM Prescription")
            total = cursor.fetchone()['cnt']
            cursor.execute(
                "SELECT * FROM Prescription ORDER BY Date DESC LIMIT %s OFFSET %s",
                (per_page, offset)
            )

        prescriptions = cursor.fetchall()
        pagination = calculate_pagination(total, per_page, page)

        # Get counts for badges
        cursor.execute("SELECT COUNT(*) AS cnt FROM Prescription WHERE Status='Pending'")
        pending_count = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM Prescription WHERE Status='Dispensed'")
        dispensed_count = cursor.fetchone()['cnt']

        # Fetch stock levels for medicines in these prescriptions
        medicine_names = list({rx['Medicine_Name'] for rx in prescriptions})
        stock_map = {}
        if medicine_names:
            placeholders = ','.join(['%s'] * len(medicine_names))
            cursor.execute(
                f"SELECT Medicine_Name, Medicine_ID, Stock FROM Medicine WHERE Medicine_Name IN ({placeholders})",
                medicine_names
            )
            for row in cursor.fetchall():
                stock_map[row['Medicine_Name']] = {
                    'stock': row['Stock'],
                    'med_id': row['Medicine_ID']
                }

        return render_template(
            'pharmacy_prescriptions.html',
            prescriptions=prescriptions,
            page=pagination['current_page'],
            total_pages=pagination['total_pages'],
            show=show,
            pending_count=pending_count,
            dispensed_count=dispensed_count,
            stock_map=stock_map,
            threshold=LOW_STOCK_THRESHOLD
        )
    except Exception as e:
        logger.error(f"Error loading pharmacy prescriptions: {e}")
        db.rollback()
        flash('An error occurred loading prescriptions.', 'danger')
        return redirect(url_for('pharmacist'))


@app.route('/dispense/<int:pid>', methods=['POST'])
@login_required(role='pharmacist')
def dispense(pid):
    """Dispense a prescription - atomically updates stock and status."""
    try:
        # Verify prescription exists and is still Pending
        cursor.execute(
            "SELECT Prescription_ID, Medicine_Name, Status, Patient_Name FROM Prescription WHERE Prescription_ID = %s",
            (pid,)
        )
        rx = cursor.fetchone()

        if not rx:
            logger.warning(f"Dispense attempt for non-existent prescription ID: {pid}")
            flash('Prescription not found.', 'danger')
            return redirect(url_for('pharmacy_prescriptions'))

        if rx['Status'] == 'Dispensed':
            flash('This prescription has already been dispensed.', 'warning')
            return redirect(url_for('pharmacy_prescriptions'))

        medicine_name = rx['Medicine_Name']
        patient_name = rx['Patient_Name']

        # Verify medicine exists in inventory
        cursor.execute(
            "SELECT Medicine_ID, Stock FROM Medicine WHERE Medicine_Name = %s",
            (medicine_name,)
        )
        med = cursor.fetchone()

        if not med:
            logger.error(f"Medicine '{medicine_name}' not found for prescription {pid}")
            flash(f'Medicine "{medicine_name}" not found in inventory. Cannot dispense.', 'danger')
            return redirect(url_for('pharmacy_prescriptions'))

        # Check stock > 0
        if med['Stock'] <= 0:
            logger.warning(f"Out of stock: {medicine_name} for prescription {pid}")
            flash(f'"{medicine_name}" is out of stock. Restock before dispensing.', 'danger')
            return redirect(url_for('pharmacy_prescriptions'))

        # All checks passed - decrement stock and mark as dispensed atomically
        cursor.execute(
            "UPDATE Medicine SET Stock = Stock - 1 WHERE Medicine_ID = %s",
            (med['Medicine_ID'],)
        )
        cursor.execute(
            "UPDATE Prescription SET Status = 'Dispensed' WHERE Prescription_ID = %s",
            (pid,)
        )
        db.commit()

        remaining = med['Stock'] - 1
        logger.info(
            f"Dispensed prescription {pid}: {medicine_name} for {patient_name}. "
            f"Remaining stock: {remaining}"
        )

        if remaining <= LOW_STOCK_THRESHOLD:
            flash(
                f'Dispensed. Low stock warning: "{medicine_name}" now has {remaining} units left.',
                'warning'
            )
        else:
            flash(f'"{medicine_name}" dispensed successfully.', 'success')

        return redirect(url_for('pharmacy_prescriptions'))

    except Exception as e:
        logger.error(f"Error dispensing prescription {pid}: {e}")
        db.rollback()
        flash('An error occurred while dispensing. Please try again.', 'danger')
        return redirect(url_for('pharmacy_prescriptions'))


# ── API Routes (Optional - for future frontend integration) ─────────────────────


@app.route('/api/medicine/low-stock')
@login_required(role='pharmacist')
def api_low_stock():
    """API endpoint to get low stock medicines."""
    try:
        cursor.execute(
            "SELECT Medicine_ID, Medicine_Name, Stock, Price, Expiry_Date "
            "FROM Medicine WHERE Stock <= %s ORDER BY Stock ASC",
            (LOW_STOCK_THRESHOLD,)
        )
        medicines = cursor.fetchall()
        return jsonify({
            'success': True,
            'count': len(medicines),
            'medicines': medicines
        })
    except Exception as e:
        logger.error(f"API error - low stock: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/appointments/today')
@login_required(role='doctor')
def api_today_appointments():
    """API endpoint to get today's appointments."""
    try:
        cursor.execute(
            "SELECT * FROM Appointment WHERE Date = CURDATE() ORDER BY Appointment_ID ASC"
        )
        appointments = cursor.fetchall()
        return jsonify({
            'success': True,
            'count': len(appointments),
            'appointments': appointments
        })
    except Exception as e:
        logger.error(f"API error - today appointments: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ── Run Application ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    # In production, set debug=False and use a proper WSGI server
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
