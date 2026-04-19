import mysql.connector

try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="supra123",
        database="pharmacy_db"
    )

    cursor = db.cursor()
    print("✅ Database Connected Successfully")

except mysql.connector.Error as err:
    print("❌ Database Connection Failed:", err)