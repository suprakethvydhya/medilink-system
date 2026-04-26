# Contributing to MediLink

Thank you for your interest in contributing to MediLink! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Requests](#pull-requests)
- [Security](#security)

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Prioritize user privacy and data security

## Getting Started

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests
5. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.8+
- MySQL 8.0+
- Git

### Setup Steps

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/medilink-system.git
cd medilink-system

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your database credentials
```

## Coding Standards

### Python Style

- Follow PEP 8 guidelines
- Use type hints for function parameters and return values
- Add docstrings to all public functions and classes
- Keep functions focused (single responsibility)

```python
def validate_username(username: str) -> Tuple[bool, str]:
    """
    Validate username format and length.

    Args:
        username: The username to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"
    # ... rest of implementation
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Variables | snake_case | `user_name` |
| Functions | snake_case | `get_user_by_id()` |
| Classes | PascalCase | `UserModel` |
| Constants | UPPER_SNAKE_CASE | `MAX_PAGE_SIZE` |
| Private | Leading underscore | `_internal_method()` |

### SQL Queries

- Always use parameterized queries to prevent SQL injection
- Use uppercase for SQL keywords
- Use meaningful aliases

```python
# Good
cursor.execute(
    "SELECT * FROM users WHERE username = %s",
    (username,)
)

# Bad - vulnerable to SQL injection
cursor.execute(
    f"SELECT * FROM users WHERE username = '{username}'"
)
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_app.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Writing Tests

- Write tests for all new features
- Aim for >80% code coverage
- Test both happy path and edge cases

```python
def test_validate_username_valid(self):
    from validators import validate_username
    is_valid, msg = validate_username('john_doe')
    assert is_valid is True
    assert msg == ""
```

## Pull Requests

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No sensitive data committed
- [ ] All tests pass

### PR Description Template

```markdown
## Summary
Brief description of changes

## Changes
- List key changes

## Testing
How to test these changes

## Screenshots (if applicable)
Add screenshots for UI changes
```

## Security

### Important Security Guidelines

1. **Never commit**:
   - `.env` files
   - Database credentials
   - API keys
   - Personal data

2. **Always**:
   - Use parameterized SQL queries
   - Sanitize user input
   - Validate data on server side
   - Use HTTPS in production

3. **Report vulnerabilities**:
   - Open a security issue (do not disclose publicly)
   - Email: security@medilink.local

## Database Migrations

When adding new tables or columns:

1. Update `schema.sql`
2. Create migration script if needed
3. Document changes in README

## Release Process

1. Update version in `__init__.py`
2. Update CHANGELOG.md
3. Create git tag
4. Create GitHub release

## Questions?

Open an issue with the "question" label or contact the maintainers.
