"""
MediLink Test Suite
Unit and integration tests for the pharmacy management system.

Run with: pytest tests/ -v
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db import db, cursor


@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client


@pytest.fixture
def authenticated_client(client):
    """Create authenticated test client."""
    # First create a test user
    client.post('/signup', data={
        'username': 'test_user',
        'password': 'Test1234',
        'confirm': 'Test1234',
        'role': 'patient'
    })
    # Login
    client.post('/login', data={
        'username': 'test_user',
        'password': 'Test1234'
    })
    yield client


class TestValidators:
    """Test validation functions."""

    def test_validate_username_valid(self):
        from validators import validate_username
        is_valid, msg = validate_username('john_doe')
        assert is_valid is True
        assert msg == ""

    def test_validate_username_too_short(self):
        from validators import validate_username
        is_valid, msg = validate_username('ab')
        assert is_valid is False
        assert '3' in msg

    def test_validate_username_too_long(self):
        from validators import validate_username
        is_valid, msg = validate_username('a' * 51)
        assert is_valid is False
        assert '50' in msg

    def test_validate_username_invalid_chars(self):
        from validators import validate_username
        is_valid, msg = validate_username('john@doe')
        assert is_valid is False
        assert 'only contain' in msg

    def test_validate_password_valid(self):
        from validators import validate_password
        is_valid, msg = validate_password('Password123')
        assert is_valid is True

    def test_validate_password_too_short(self):
        from validators import validate_password
        is_valid, msg = validate_password('Pass1')
        assert is_valid is False
        assert '8' in msg

    def test_validate_password_no_letter(self):
        from validators import validate_password
        is_valid, msg = validate_password('12345678')
        assert is_valid is False
        assert 'letter' in msg

    def test_validate_password_no_number(self):
        from validators import validate_password
        is_valid, msg = validate_password('Password')
        assert is_valid is False
        assert 'number' in msg

    def test_validate_date_not_past_valid(self):
        from validators import validate_date_not_past
        from datetime import date, timedelta
        future = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        is_valid, msg = validate_date_not_past(future)
        assert is_valid is True

    def test_validate_date_not_past_invalid(self):
        from validators import validate_date_not_past
        past = '2020-01-01'
        is_valid, msg = validate_date_not_past(past)
        assert is_valid is False
        assert 'past' in msg

    def test_validate_positive_int_valid(self):
        from validators import validate_positive_int
        is_valid, msg = validate_positive_int(5)
        assert is_valid is True

    def test_validate_positive_int_invalid(self):
        from validators import validate_positive_int
        is_valid, msg = validate_positive_int(-5)
        assert is_valid is False

    def test_validate_positive_int_zero(self):
        from validators import validate_positive_int
        is_valid, msg = validate_positive_int(0)
        assert is_valid is False


class TestUtils:
    """Test utility functions."""

    def test_sanitize_text_basic(self):
        from utils import sanitize_text
        result = sanitize_text('  hello world  ')
        assert result == 'hello world'

    def test_sanitize_text_removes_html(self):
        from utils import sanitize_text
        result = sanitize_text('<script>alert("xss")</script>hello')
        assert '<script>' not in result
        assert 'hello' in result

    def test_sanitize_text_max_length(self):
        from utils import sanitize_text
        result = sanitize_text('a' * 300, max_len=100)
        assert len(result) == 100

    def test_safe_int_valid(self):
        from utils import safe_int
        assert safe_int('123') == 123
        assert safe_int(123) == 123

    def test_safe_int_invalid(self):
        from utils import safe_int
        assert safe_int('abc') == 0
        assert safe_int(None) == 0

    def test_safe_float_valid(self):
        from utils import safe_float
        assert safe_float('12.5') == 12.5

    def test_safe_float_invalid(self):
        from utils import safe_float
        assert safe_float('abc') == 0.0

    def test_get_pagination_params_default(self):
        from utils import get_pagination_params
        from flask import Flask
        test_app = Flask(__name__)
        with test_app.test_request_context('/'):
            page, per_page = get_pagination_params(__import__('flask').request)
            assert page == 1
            assert per_page == 10

    def test_format_currency(self):
        from utils import format_currency
        assert format_currency(12.5) == '₹12.50'
        assert format_currency(100) == '₹100.00'

    def test_get_stock_status(self):
        from utils import get_stock_status
        assert get_stock_status(0) == 'out_of_stock'
        assert get_stock_status(5) == 'low_stock'
        assert get_stock_status(50) == 'in_stock'


class TestRoutes:
    """Test Flask routes."""

    def test_index_redirects(self, client):
        """Test root route redirects to login."""
        response = client.get('/')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_login_page_loads(self, client):
        """Test login page loads."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'Login' in response.data

    def test_signup_page_loads(self, client):
        """Test signup page loads."""
        response = client.get('/signup')
        assert response.status_code == 200
        assert b'Sign Up' in response.data

    def test_login_required_protects_routes(self, client):
        """Test that protected routes redirect to login."""
        response = client.get('/doctor')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_signup_creates_user(self, client):
        """Test user registration."""
        response = client.post('/signup', data={
            'username': 'newuser',
            'password': 'NewUser123',
            'confirm': 'NewUser123',
            'role': 'patient'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Account created' in response.data or b'log in' in response.data

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'wrongpassword'
        })
        assert response.status_code == 200
        assert b'Invalid' in response.data

    def test_404_page(self, client):
        """Test 404 error page."""
        response = client.get('/nonexistent-page')
        assert response.status_code == 404
        assert b'404' in response.data


class TestAppointmentBooking:
    """Test appointment booking flow."""

    def test_book_appointment_requires_login(self, client):
        """Test booking requires authentication."""
        response = client.get('/book_appointment')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_book_appointment_validation(self, authenticated_client):
        """Test appointment booking validation."""
        # Test missing fields
        response = authenticated_client.post('/book_appointment', data={
            'pname': '',
            'dname': 'Dr. Smith',
            'date': '2030-01-01'
        })
        assert b'required' in response.data

    def test_book_appointment_past_date_rejected(self, authenticated_client):
        """Test that past dates are rejected."""
        response = authenticated_client.post('/book_appointment', data={
            'pname': 'Test Patient',
            'dname': 'Dr. Smith',
            'date': '2020-01-01'
        })
        assert b'past' in response.data or b'required' in response.data


class TestMedicineManagement:
    """Test medicine inventory management."""

    def test_add_medicine_requires_pharmacist(self, client):
        """Test adding medicine requires pharmacist role."""
        response = client.get('/add_medicine')
        assert response.status_code == 302

    def test_medicine_validation(self):
        """Test medicine validation functions."""
        from validators import validate_medicine_name

        is_valid, msg = validate_medicine_name('Paracetamol')
        assert is_valid is True

        is_valid, msg = validate_medicine_name('')
        assert is_valid is False

        is_valid, msg = validate_medicine_name('A')
        assert is_valid is False


class TestPrescriptionDispensing:
    """Test prescription dispensing workflow."""

    def test_dispense_requires_pharmacist(self, client):
        """Test dispensing requires pharmacist role."""
        response = client.post('/dispense/1')
        assert response.status_code == 302


# ── Run Tests ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
