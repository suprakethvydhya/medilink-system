from flask import Flask, render_template, request, redirect, session
from db import db, cursor

app = Flask(__name__)
app.secret_key = 'secret123'


# ---------------- HELPER ----------------
def check_role(role):
    return 'role' in session and session['role'] == role


# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template('index.html')


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        cursor.execute(
            "SELECT role FROM Users WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cursor.fetchone()

        if user:
            session['user'] = username
            session['role'] = user[0]
            return redirect('/dashboard')

        return render_template('login.html', msg="❌ Invalid Login")

    return render_template('login.html')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'role' not in session:
        return redirect('/login')

    role = session['role']

    if role == 'doctor':
        return redirect('/doctor')
    elif role == 'patient':
        return redirect('/patient')
    elif role == 'pharmacist':
        return redirect('/pharmacist')

    return redirect('/login')  # fallback safety


# ---------------- DOCTOR ----------------
@app.route('/doctor')
def doctor():
    if not check_role('doctor'):
        return redirect('/login')
    return render_template('doctor.html')


# ---------------- PATIENT ----------------
@app.route('/patient')
def patient():
    if not check_role('patient'):
        return redirect('/login')
    return render_template('patient.html')


# ---------------- PHARMACIST ----------------
@app.route('/pharmacist')
def pharmacist():
    if not check_role('pharmacist'):
        return redirect('/login')
    return render_template('pharmacist.html')


# ---------------- ADD MEDICINE ----------------
@app.route('/add_medicine', methods=['GET', 'POST'])
def add_medicine():
    if not check_role('pharmacist'):
        return redirect('/login')

    if request.method == 'POST':
        try:
            data = (
                request.form['id'],
                request.form['name'],
                request.form['expiry'],
                request.form['stock'],
                request.form['price']
            )

            cursor.execute("INSERT INTO Medicine VALUES (%s,%s,%s,%s,%s)", data)
            db.commit()

            return render_template('add_medicine.html', msg="✅ Medicine Added")

        except Exception as e:
            print("ERROR:", e)
            return render_template('add_medicine.html', msg="❌ Error: Duplicate or Invalid")

    return render_template('add_medicine.html')


# ---------------- VIEW MEDICINE ----------------
@app.route('/view_medicine')
def view_medicine():
    if not check_role('pharmacist'):
        return redirect('/login')

    cursor.execute("SELECT * FROM Medicine")
    data = cursor.fetchall()
    return render_template('view_medicine.html', data=data)


# ---------------- BOOK APPOINTMENT ----------------
@app.route('/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    if not check_role('patient'):
        return redirect('/login')

    if request.method == 'POST':
        try:
            data = (
                request.form['pname'],
                request.form['dname'],
                request.form['date']
            )

            cursor.execute(
                "INSERT INTO Appointment (Patient_Name, Doctor_Name, Date) VALUES (%s,%s,%s)",
                data
            )
            db.commit()

            return render_template('appointment.html', msg="✅ Appointment Booked")

        except Exception as e:
            print("ERROR:", e)
            return render_template('appointment.html', msg="❌ Error Booking Appointment")

    return render_template('appointment.html')


# ---------------- VIEW APPOINTMENTS ----------------
@app.route('/view_appointments')
def view_appointments():
    if not check_role('doctor'):
        return redirect('/login')

    cursor.execute("SELECT * FROM Appointment")
    data = cursor.fetchall()
    return render_template('view_appointments.html', data=data)


# ---------------- ADD PRESCRIPTION ----------------
@app.route('/add_prescription', methods=['GET', 'POST'])
def add_prescription():
    if not check_role('doctor'):
        return redirect('/login')

    if request.method == 'POST':
        try:
            data = (
                request.form['doctor'],
                request.form['patient'],
                request.form['medicine'],
                request.form['date']
            )

            cursor.execute(
                "INSERT INTO Prescription (Doctor_Name, Patient_Name, Medicine_Name, Date) VALUES (%s,%s,%s,%s)",
                data
            )
            db.commit()

            return render_template('add_prescription.html', msg="✅ Prescription Added")

        except Exception as e:
            print("ERROR:", e)
            return render_template('add_prescription.html', msg="❌ Error Adding Prescription")

    return render_template('add_prescription.html')


#----------------- VIEW PRESCRIPTIONS ----------------
@app.route('/view_prescriptions')
def view_prescriptions():
    cursor.execute("SELECT * FROM Prescription")
    data = cursor.fetchall()
    return render_template('view_prescriptions.html', data=data)



#---------------- DELETE APPOINTMENT ----------------
@app.route('/delete_appointment', methods=['POST'])
def delete_appointment():
    ids = request.form.getlist('delete_ids')

    if ids:
        for aid in ids:
            cursor.execute(
                "DELETE FROM Appointment WHERE Appointment_ID=%s",
                (aid,)
            )
        db.commit()

    return redirect('/view_appointments')

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)