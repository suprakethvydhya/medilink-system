import os
import re
import logging
from datetime import date, datetime
from functools import wraps
from typing import Optional, Tuple

from dotenv import load_dotenv
from flask import (Flask, flash, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from db import db, cursor

load_dotenv()

# ── Logging Configuration ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY is not set. Check your .env file.")

# ── Constants ─────────────────────────────────────────────────────────────────
LOW_STOCK_THRESHOLD = 10   # medicines with stock <= this get flagged
MAX_PAGE_SIZE = 100        # Maximum items per page to prevent DoS
DEFAULT_PAGE_SIZE = 10     # Default items per page

# ── Helpers ───────────────────────────────────────────────────────────────────

def sanitize_text(value: str, max_len: int = 255) -> str:
    """Strip whitespace, remove dangerous chars, enforce max length."""
    if not value:
        return ""
    value = str(value).strip()
    # Remove any HTML/script tags to prevent XSS
    value = re.sub(r'<[^>]+>', '', value)
    # Remove null bytes and other control characters
    value = re.sub(r'[\x00-\x1f\x7f]', '', value)
    return value[:max_len]


def validate_date_not_past(date_str: str) -> bool:
    """Return True if the date string is today or in the future."""
    if not date_str:
        return False
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return d >= date.today()
    except ValueError:
        return False


def validate_positive_int(value) -> bool:
    try:
        return int(value) > 0
    except (ValueError, TypeError):
        return False


def validate_positive_float(value) -> bool:
    try:
        return float(value) >= 0
    except (ValueError, TypeError):
        return False


def safe_int(value, default=0) -> int:
    """Safely convert a value to int with a default fallback."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def login_required(role: Optional[str] = None):
    """Decorator: ensures user is logged in, optionally with a specific role."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user' not in session:
                flash('Please log in to continue.', 'warning')
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                logger.warning(f"Access denied for user {session.get('user')} to {request.path} (required role: {role})")
                flash('Access denied.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator


def get_pagination_params(request) -> Tuple[int, int]:
    """Extract and validate pagination parameters from request.

    Returns:
        Tuple of (page_number, per_page_count)
    """
    page = max(1, safe_int(request.args.get('page', 1), 1))
    per_page = min(
        MAX_PAGE_SIZE,
        max(1, safe_int(request.args.get('per_page', DEFAULT_PAGE_SIZE), DEFAULT_PAGE_SIZE))
    )
    return page, per_page


# ── Error Handlers ────────────────────────────────────────────────────────────

@app.errorhandler(404)
def page_not_found(e):
    logger.warning(f"404 error: {request.path}")
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"500 error: {e}", exc_info=True)
    try:
        db.rollback()
    except Exception as rollback_error:
        logger.error(f"Rollback failed: {rollback_error}")
    return render_template('500.html'), 500


@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


# ── Home ──────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
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
    if 'user' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = sanitize_text(request.form.get('username', ''), 50)
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm', '')
        role     = request.form.get('role', '').strip()

        # Validation
        if not all([username, password, confirm, role]):
            flash('All fields are required.', 'danger')
            return render_template('signup.html')

        # Validate username format (alphanumeric + underscore only)
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            flash('Username can only contain letters, numbers, and underscores.', 'danger')
            return render_template('signup.html')

        if len(username) < 3 or len(username) > 50:
            flash('Username must be between 3 and 50 characters.', 'danger')
            return render_template('signup.html')

        if role not in ('doctor', 'patient', 'pharmacist'):
            flash('Invalid role selected.', 'danger')
            return render_template('signup.html')

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('signup.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('signup.html')

        # Check for strong password (at least one letter and one number)
        if not re.search(r'[A-Za-z]', password) or not re.search(r'[0-9]', password):
            flash('Password must contain at least one letter and one number.', 'danger')
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
    username = session.get('user', 'User')
    session.clear()
    flash(f'Goodbye, {username}. You have been logged out.', 'info')
    return redirect(url_for('login'))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    role = session.get('role')
    return redirect(url_for(role))   # maps 'doctor' -> /doctor, etc.


# ── Doctor ────────────────────────────────────────────────────────────────────

@app.route('/doctor')
@login_required(role='doctor')
def doctor():
    user = session['user']

    # Appointment status counts
    cursor.execute("SELECT COUNT(*) AS cnt FROM Appointment")
    appt_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) AS cnt FROM Appointment WHERE Status = 'Scheduled'")
    scheduled_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) AS cnt FROM Appointment WHERE Status = 'In Progress'")
    in_progress_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) AS cnt FROM Appointment WHERE Status = 'Completed'")
    completed_count = cursor.fetchone()['cnt']

    # Today's appointments (the doctor's patient list for today)
    cursor.execute(
        "SELECT * FROM Appointment WHERE Date = CURDATE() ORDER BY Appointment_ID ASC"
    )
    todays_patients = cursor.fetchall()

    # Prescriptions this doctor wrote, with dispensing status
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

    # 5 most recent prescriptions written by this doctor
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


@app.route('/view_appointments')
@login_required(role='doctor')
def view_appointments():
    page     = request.args.get('page', 1, type=int)
    per_page = 10
    offset   = (page - 1) * per_page

    cursor.execute("SELECT COUNT(*) AS cnt FROM Appointment")
    total = cursor.fetchone()['cnt']

    cursor.execute(
        "SELECT * FROM Appointment ORDER BY Date DESC LIMIT %s OFFSET %s",
        (per_page, offset)
    )
    appointments = cursor.fetchall()
    total_pages  = (total + per_page - 1) // per_page

    return render_template(
        'view_appointments.html',
        appointments=appointments,
        page=page,
        total_pages=total_pages
    )


@app.route('/edit_appointment/<int:appt_id>', methods=['GET', 'POST'])
@login_required(role='doctor')
def edit_appointment(appt_id):
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
            d     = request.form.get('date', '').strip()
            symptoms = sanitize_text(request.form.get('symptoms', ''), 200)

            if not all([pname, dname, d]):
                flash('All fields are required.', 'danger')
                return render_template('edit_appointment.html', appt=appt, today=date.today().isoformat())

            if len(pname) < 2 or len(dname) < 2:
                flash('Names must be at least 2 characters.', 'danger')
                return render_template('edit_appointment.html', appt=appt, today=date.today().isoformat())

            if not validate_date_not_past(d):
                flash('Appointment date cannot be in the past.', 'danger')
                return render_template('edit_appointment.html', appt=appt, today=date.today().isoformat())

            cursor.execute(
                "UPDATE Appointment SET Patient_Name=%s, Doctor_Name=%s, Date=%s, Symptoms=%s "
                "WHERE Appointment_ID=%s",
                (pname, dname, d, symptoms, appt_id)
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
    raw_ids = request.form.getlist('delete_ids[]')

    # ✅ FIX: validate every ID is a positive integer before touching DB
    validated = []
    for rid in raw_ids:
        try:
            validated.append(int(rid))
        except ValueError:
            flash(f'Invalid ID "{rid}" skipped.', 'warning')

    for appt_id in validated:
        cursor.execute(
            "DELETE FROM Appointment WHERE Appointment_ID = %s", (appt_id,)
        )
    db.commit()

    count = len(validated)
    flash(f'{count} appointment(s) deleted.', 'success')
    return redirect(url_for('view_appointments'))



@app.route('/update_appointment_status/<int:appt_id>', methods=['POST'])
@login_required(role='doctor')
def update_appointment_status(appt_id):
    new_status = request.form.get('status', '').strip()
    notes      = sanitize_text(request.form.get('notes', ''), 500)

    valid_statuses = ('Scheduled', 'In Progress', 'Completed')
    if new_status not in valid_statuses:
        flash('Invalid status.', 'danger')
        return redirect(url_for('view_appointments'))

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

    labels = {'Scheduled': 'rescheduled', 'In Progress': 'marked In Progress', 'Completed': 'marked as Completed ✓'}
    flash(f'Appointment #{appt_id} {labels[new_status]}.', 'success')
    return redirect(url_for('view_appointments'))


@app.route('/add_prescription', methods=['GET', 'POST'])
@login_required(role='doctor')
def add_prescription():
    if request.method == 'POST':
        doctor   = sanitize_text(request.form.get('doctor', ''), 100)
        patient  = sanitize_text(request.form.get('patient', ''), 100)
        medicine = sanitize_text(request.form.get('medicine', ''), 100)
        dosage   = sanitize_text(request.form.get('dosage', ''), 200)
        notes    = sanitize_text(request.form.get('notes', ''), 500)
        d        = request.form.get('date', '').strip()

        if not all([doctor, patient, medicine, d]):
            flash('Doctor, patient, medicine, and date are required.', 'danger')
            return render_template('add_prescription.html')

        if len(doctor) < 2 or len(patient) < 2:
            flash('Names must be at least 2 characters.', 'danger')
            return render_template('add_prescription.html')

        if len(medicine) < 2:
            flash('Medicine name must be at least 2 characters.', 'danger')
            return render_template('add_prescription.html')

        if not validate_date_not_past(d):
            flash('Prescription date cannot be in the past.', 'danger')
            return render_template('add_prescription.html')

        try:
            cursor.execute(
                "INSERT INTO Prescription "
                "(Doctor_Name, Patient_Name, Medicine_Name, Dosage, Notes, Date, Status) "
                "VALUES (%s, %s, %s, %s, %s, %s, 'Pending')",
                (doctor, patient, medicine, dosage, notes, d)
            )
            db.commit()
            logger.info(f"Prescription added: {medicine} for {patient} by Dr. {doctor}")
            flash('Prescription added successfully.', 'success')
            return redirect(url_for('doctor'))
        except Exception as e:
            logger.error(f"Error adding prescription: {e}")
            db.rollback()
            flash('An error occurred while adding prescription.', 'danger')

    return render_template('add_prescription.html',
                           today=date.today().isoformat())


# ── Patient ───────────────────────────────────────────────────────────────────

@app.route('/patient')
@login_required(role='patient')
def patient():
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

        # Upcoming appointments (next 3, today or future, excluding completed)
        cursor.execute(
            "SELECT * FROM Appointment WHERE Patient_Name = %s AND Date >= CURDATE() AND (Status IS NULL OR Status != 'Completed') ORDER BY Date ASC LIMIT 3",
            (user,)
        )
        upcoming_appts = cursor.fetchall()

        # Latest 3 prescriptions
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
        flash('An error occurred loading your dashboard. Please try again.', 'danger')
        return redirect(url_for('dashboard'))


@app.route('/book_appointment', methods=['GET', 'POST'])
@login_required(role='patient')
def book_appointment():
    if request.method == 'POST':
        pname = sanitize_text(request.form.get('pname', ''), 100)
        dname = sanitize_text(request.form.get('dname', ''), 100)
        d     = request.form.get('date', '').strip()
        symptoms = sanitize_text(request.form.get('symptoms', ''), 200)

        if not all([pname, dname, d]):
            flash('All fields are required.', 'danger')
            return render_template('appointment.html', today=date.today().isoformat())

        if len(pname) < 2:
            flash('Patient name must be at least 2 characters.', 'danger')
            return render_template('appointment.html', today=date.today().isoformat())

        if len(dname) < 2:
            flash('Doctor name must be at least 2 characters.', 'danger')
            return render_template('appointment.html', today=date.today().isoformat())

        if not validate_date_not_past(d):
            flash('Appointment date cannot be in the past.', 'danger')
            return render_template('appointment.html', today=date.today().isoformat())

        # Limit appointments per day (prevent spam)
        try:
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM Appointment WHERE Patient_Name = %s AND Date = %s",
                (pname, d)
            )
            existing_count = cursor.fetchone()['cnt']
            if existing_count >= 3:
                flash('You already have 3 appointments on this date. Please choose another day.', 'warning')
                return render_template('appointment.html', today=date.today().isoformat())

            cursor.execute(
                "INSERT INTO Appointment (Patient_Name, Doctor_Name, Date, Symptoms, Status) "
                "VALUES (%s, %s, %s, %s, 'Scheduled')",
                (pname, dname, d, symptoms)
            )
            db.commit()
            logger.info(f"Appointment booked: {pname} with Dr. {dname} on {d}")
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
    """Patient views their own appointments."""
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
                "SELECT COUNT(*) AS cnt FROM Appointment WHERE Patient_Name = %s "
                "AND Date >= CURDATE()",
                (user,)
            )
            total = cursor.fetchone()['cnt']
            cursor.execute(
                "SELECT * FROM Appointment WHERE Patient_Name = %s "
                "AND Date >= CURDATE() "
                "ORDER BY Date ASC LIMIT %s OFFSET %s",
                (user, per_page, offset)
            )

        appointments = cursor.fetchall()
        total_pages = (total + per_page - 1) // per_page

        return render_template(
            'my_appointments.html',
            appointments=appointments,
            page=page,
            total_pages=total_pages,
            show=show
        )
    except Exception as e:
        logger.error(f"Error loading appointments: {e}")
        flash('An error occurred loading your appointments.', 'danger')
        return redirect(url_for('patient'))


@app.route('/view_prescriptions')
@login_required(role='doctor')      # ✅ FIX: was accessible by anyone
def view_prescriptions():
    page     = request.args.get('page', 1, type=int)
    per_page = 10
    offset   = (page - 1) * per_page

    cursor.execute("SELECT COUNT(*) AS cnt FROM Prescription")
    total = cursor.fetchone()['cnt']

    cursor.execute(
        "SELECT * FROM Prescription ORDER BY Date DESC LIMIT %s OFFSET %s",
        (per_page, offset)
    )
    prescriptions = cursor.fetchall()
    total_pages   = (total + per_page - 1) // per_page

    return render_template(
        'view_prescriptions.html',
        prescriptions=prescriptions,
        page=page,
        total_pages=total_pages
    )


@app.route('/my_prescriptions')     # ✅ NEW: patient-specific prescriptions
@login_required(role='patient')
def my_prescriptions():
    page     = request.args.get('page', 1, type=int)
    per_page = 10
    offset   = (page - 1) * per_page

    cursor.execute(
        "SELECT COUNT(*) AS cnt FROM Prescription WHERE Patient_Name = %s",
        (session['user'],)
    )
    total = cursor.fetchone()['cnt']

    cursor.execute(
        "SELECT * FROM Prescription WHERE Patient_Name = %s "
        "ORDER BY Date DESC LIMIT %s OFFSET %s",
        (session['user'], per_page, offset)
    )
    prescriptions = cursor.fetchall()
    total_pages   = (total + per_page - 1) // per_page

    return render_template(
        'my_prescriptions.html',
        prescriptions=prescriptions,
        page=page,
        total_pages=total_pages
    )


# ── Pharmacist ────────────────────────────────────────────────────────────────

@app.route('/pharmacist')
@login_required(role='pharmacist')
def pharmacist():
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

    # Latest 5 prescriptions waiting to be dispensed
    cursor.execute(
        "SELECT * FROM Prescription WHERE Status = 'Pending' ORDER BY Date DESC LIMIT 5"
    )
    pending_prescriptions = cursor.fetchall()

    # Recent dispensing activity (last 5 dispensed)
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


@app.route('/add_medicine', methods=['GET', 'POST'])
@login_required(role='pharmacist')
def add_medicine():
    if request.method == 'POST':
        med_id = request.form.get('id', '').strip()
        name   = sanitize_text(request.form.get('name', ''), 100)
        expiry = request.form.get('expiry', '').strip()
        stock  = request.form.get('stock', '').strip()
        price  = request.form.get('price', '').strip()

        if not all([med_id, name, expiry, stock, price]):
            flash('All fields are required.', 'danger')
            return render_template('add_medicine.html')

        if not validate_positive_int(med_id):
            flash('Medicine ID must be a positive integer.', 'danger')
            return render_template('add_medicine.html')

        if not validate_positive_int(stock):
            flash('Stock must be a positive integer.', 'danger')
            return render_template('add_medicine.html')

        if not validate_positive_float(price):
            flash('Price must be a non-negative number.', 'danger')
            return render_template('add_medicine.html')

        if len(name) < 2:
            flash('Medicine name must be at least 2 characters.', 'danger')
            return render_template('add_medicine.html')

        # Validate expiry date format and not empty
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
    page     = request.args.get('page', 1, type=int)
    per_page = 10
    offset   = (page - 1) * per_page

    search = sanitize_text(request.args.get('search', ''), 100)

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

    medicines   = cursor.fetchall()
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'view_medicine.html',
        medicines=medicines,
        page=page,
        total_pages=total_pages,
        search=search,
        threshold=LOW_STOCK_THRESHOLD
    )


@app.route('/edit_medicine/<int:med_id>', methods=['GET', 'POST'])
@login_required(role='pharmacist')
def edit_medicine(med_id):
    try:
        cursor.execute(
            "SELECT * FROM Medicine WHERE Medicine_ID = %s", (med_id,)
        )
        med = cursor.fetchone()
        if not med:
            flash('Medicine not found.', 'danger')
            return redirect(url_for('view_medicine'))

        if request.method == 'POST':
            name   = sanitize_text(request.form.get('name', ''), 100)
            expiry = request.form.get('expiry', '').strip()
            stock  = request.form.get('stock', '').strip()
            price  = request.form.get('price', '').strip()

            if not all([name, expiry, stock, price]):
                flash('All fields are required.', 'danger')
                return render_template('edit_medicine.html', med=med)

            if len(name) < 2:
                flash('Medicine name must be at least 2 characters.', 'danger')
                return render_template('edit_medicine.html', med=med)

            if not validate_positive_int(stock):
                flash('Stock must be a positive integer.', 'danger')
                return render_template('edit_medicine.html', med=med)

            if not validate_positive_float(price):
                flash('Price must be a non-negative number.', 'danger')
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
    raw_ids = request.form.getlist('delete_ids[]')

    # ✅ FIX: validate IDs are integers
    validated = []
    for rid in raw_ids:
        try:
            validated.append(int(rid))
        except ValueError:
            flash(f'Invalid ID "{rid}" skipped.', 'warning')

    for med_id in validated:
        cursor.execute(
            "DELETE FROM Medicine WHERE Medicine_ID = %s", (med_id,)
        )
    db.commit()

    flash(f'{len(validated)} medicine(s) deleted.', 'success')
    return redirect(url_for('view_medicine'))



# ── Pharmacist: Prescription Dispensing ──────────────────────────────────────

@app.route('/pharmacy_prescriptions')
@login_required(role='pharmacist')
def pharmacy_prescriptions():
    page     = request.args.get('page', 1, type=int)
    per_page = 15
    offset   = (page - 1) * per_page

    # Optional filter: show only pending
    show = request.args.get('show', 'all')   # 'all' | 'pending' | 'dispensed'
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
    total_pages   = (total + per_page - 1) // per_page

    # Pending count for dashboard badge
    cursor.execute("SELECT COUNT(*) AS cnt FROM Prescription WHERE Status='Pending'")
    pending_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) AS cnt FROM Prescription WHERE Status='Dispensed'")
    dispensed_count = cursor.fetchone()['cnt']

    # Fetch stock level for every medicine referenced in these prescriptions
    # so the template can show available stock inline without a second query per row
    medicine_names = list({rx['Medicine_Name'] for rx in prescriptions})
    stock_map = {}
    if medicine_names:
        fmt = ','.join(['%s'] * len(medicine_names))
        cursor.execute(
            f"SELECT Medicine_Name, Medicine_ID, Stock FROM Medicine WHERE Medicine_Name IN ({fmt})",
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
        page=page,
        total_pages=total_pages,
        show=show,
        pending_count=pending_count,
        dispensed_count=dispensed_count,
        stock_map=stock_map,
        threshold=10
    )


@app.route('/dispense/<int:pid>', methods=['POST'])
@login_required(role='pharmacist')
def dispense(pid):
    """Dispense a prescription - atomically updates stock and prescription status."""
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

        # Verify the medicine exists in inventory
        cursor.execute(
            "SELECT Medicine_ID, Stock FROM Medicine WHERE Medicine_Name = %s",
            (medicine_name,)
        )
        med = cursor.fetchone()

        if not med:
            logger.error(f"Medicine '{medicine_name}' not found for prescription {pid}")
            flash(f'Medicine "{medicine_name}" not found in inventory. Cannot dispense.', 'danger')
            return redirect(url_for('pharmacy_prescriptions'))

        # Check stock > 0 before decrementing
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
        logger.info(f"Dispensed prescription {pid}: {medicine_name} for {patient_name}. Remaining stock: {remaining}")

        if remaining <= LOW_STOCK_THRESHOLD:
            flash(
                f'Dispensed. ⚠ Low stock warning: "{medicine_name}" now has {remaining} units left.',
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


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)
