import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import db, cursor

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY is not set. Check your .env file.")


# ── Helper ────────────────────────────────────────────────────────────────────

def check_role(role):
    return 'role' in session and session['role'] == role


# ── Home ──────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            return render_template('login.html', error='All fields required.')

        # Parameterized query — no SQL injection possible
        cursor.execute(
            "SELECT password, role FROM users WHERE username = %s",
            (username,)
        )
        row = cursor.fetchone()

        # check_password_hash handles hashed comparison — no plaintext stored
        if row and check_password_hash(row['password'], password):
            session.clear()          # prevent session fixation
            session['user'] = username
            session['role'] = row['role']
            return redirect('/dashboard')

        return render_template('login.html', error='Invalid credentials.')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ── Dashboard (role-based redirect) ───────────────────────────────────────────

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    role = session.get('role')
    if role == 'doctor':
        return redirect('/doctor')
    elif role == 'patient':
        return redirect('/patient')
    elif role == 'pharmacist':
        return redirect('/pharmacist')
    return redirect('/login')


# ── Doctor ────────────────────────────────────────────────────────────────────

@app.route('/doctor')
def doctor():
    if not check_role('doctor'):
        return redirect('/login')
    return render_template('doctor.html')


@app.route('/view_appointments')
def view_appointments():
    if not check_role('doctor'):
        return redirect('/login')
    cursor.execute("SELECT * FROM Appointment")
    appointments = cursor.fetchall()
    return render_template('view_appointments.html', appointments=appointments)


@app.route('/delete_appointment', methods=['POST'])
def delete_appointment():
    if not check_role('doctor'):
        return redirect('/login')
    delete_ids = request.form.getlist('delete_ids[]')
    for appt_id in delete_ids:
        # Parameterized — each ID passed safely
        cursor.execute(
            "DELETE FROM Appointment WHERE Appointment_ID = %s",
            (appt_id,)
        )
    db.commit()
    return redirect('/view_appointments')


@app.route('/add_prescription', methods=['GET', 'POST'])
def add_prescription():
    if not check_role('doctor'):
        return redirect('/login')
    if request.method == 'POST':
        doctor   = request.form.get('doctor', '').strip()
        patient  = request.form.get('patient', '').strip()
        medicine = request.form.get('medicine', '').strip()
        date     = request.form.get('date', '').strip()

        cursor.execute(
            "INSERT INTO Prescription (Doctor_Name, Patient_Name, Medicine_Name, Date) "
            "VALUES (%s, %s, %s, %s)",
            (doctor, patient, medicine, date)
        )
        db.commit()
        return redirect('/doctor')

    return render_template('add_prescription.html')


# ── Patient ───────────────────────────────────────────────────────────────────

@app.route('/patient')
def patient():
    if not check_role('patient'):
        return redirect('/login')
    return render_template('patient.html')


@app.route('/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    if not check_role('patient'):
        return redirect('/login')
    if request.method == 'POST':
        pname = request.form.get('pname', '').strip()
        dname = request.form.get('dname', '').strip()
        date  = request.form.get('date', '').strip()

        cursor.execute(
            "INSERT INTO Appointment (Patient_Name, Doctor_Name, Date) VALUES (%s, %s, %s)",
            (pname, dname, date)
        )
        db.commit()
        return redirect('/patient')

    return render_template('appointment.html')


@app.route('/view_prescriptions')
def view_prescriptions():
    cursor.execute("SELECT * FROM Prescription")
    prescriptions = cursor.fetchall()
    return render_template('view_prescriptions.html', prescriptions=prescriptions)


# ── Pharmacist ────────────────────────────────────────────────────────────────

@app.route('/pharmacist')
def pharmacist():
    if not check_role('pharmacist'):
        return redirect('/login')
    return render_template('pharmacist.html')


@app.route('/add_medicine', methods=['GET', 'POST'])
def add_medicine():
    if not check_role('pharmacist'):
        return redirect('/login')
    if request.method == 'POST':
        med_id  = request.form.get('id', '').strip()
        name    = request.form.get('name', '').strip()
        expiry  = request.form.get('expiry', '').strip()
        stock   = request.form.get('stock', '').strip()
        price   = request.form.get('price', '').strip()

        cursor.execute(
            "INSERT INTO Medicine (Medicine_ID, Medicine_Name, Expiry_Date, Stock, Price) "
            "VALUES (%s, %s, %s, %s, %s)",
            (med_id, name, expiry, stock, price)
        )
        db.commit()
        return redirect('/pharmacist')

    return render_template('add_medicine.html')


@app.route('/view_medicine')
def view_medicine():
    if not check_role('pharmacist'):
        return redirect('/login')
    cursor.execute("SELECT * FROM Medicine")
    medicines = cursor.fetchall()
    return render_template('view_medicine.html', medicines=medicines)


@app.route('/delete_medicine', methods=['POST'])
def delete_medicine():
    # This route was referenced in the template but never implemented — now fixed
    if not check_role('pharmacist'):
        return redirect('/login')
    delete_ids = request.form.getlist('delete_ids[]')
    for med_id in delete_ids:
        cursor.execute(
            "DELETE FROM Medicine WHERE Medicine_ID = %s",
            (med_id,)
        )
    db.commit()
    return redirect('/view_medicine')


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    # debug=True is fine for local dev; never deploy with it on
    app.run(debug=True)