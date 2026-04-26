"""
MediLink - Application Entry Point
Run this file to start the development server.

Usage:
    python run.py

Or with environment variables:
    flask --app run run

For production, use a WSGI server like Gunicorn:
    gunicorn -w 4 -b 0.0.0.0:5000 run:app
"""

import os
import sys

# Ensure the application directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == '__main__':
    print("=" * 60)
    print("  MediLink Pharmacy Management System")
    print("=" * 60)
    print()
    print("Starting development server...")
    print()
    print("Access the application at:")
    print("  http://localhost:5000")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)

    # Run with debug mode (disable in production)
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(
        debug=debug,
        host='0.0.0.0',
        port=5000
    )
