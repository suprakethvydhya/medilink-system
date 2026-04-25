import os
import sys
import pymysql
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    try:
        conn = pymysql.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "medilink"),
            port=int(os.getenv("DB_PORT", 3306)),
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
            charset="utf8mb4",
        )
        return conn
    except pymysql.Error as e:
        print(f"[MediLink] Database connection failed: {e}", file=sys.stderr)
        sys.exit(1)

db = get_connection()
cursor = db.cursor()
