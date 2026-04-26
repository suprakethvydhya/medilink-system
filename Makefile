# MediLink Pharmacy Management System
# Makefile for common development tasks

.PHONY: help install run test clean lint format db-setup venv

# Default target
help:
	@echo "MediLink Pharmacy Management System"
	@echo ""
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make venv       - Create virtual environment"
	@echo "  make run        - Run development server"
	@echo "  make test       - Run test suite"
	@echo "  make lint       - Run linter (flake8)"
	@echo "  make format     - Format code (black)"
	@echo "  make clean      - Clean up generated files"
	@echo "  make db-setup   - Setup database (requires MySQL)"
	@echo ""

# Install dependencies
install:
	pip install -r requirements.txt

# Create virtual environment
venv:
	python -m venv venv
	@echo "Virtual environment created. Activate with:"
	@echo "  Windows: venv\\Scripts\\activate"
	@echo "  Linux/Mac: source venv/bin/activate"

# Run development server
run:
	python run.py

# Run tests
test:
	pytest tests/ -v

# Run tests with coverage
test-cov:
	pytest tests/ --cov=app --cov-report=html --cov-report=term

# Run linter
lint:
	@echo "Running flake8..."
	flake8 app.py validators.py utils.py config.py --max-line-length=100

# Format code
format:
	@echo "Formatting code with black..."
	black app.py validators.py utils.py config.py tests/ --line-length=100

# Clean up
clean:
	@echo "Cleaning up..."
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf *.log
	rm -rf *.pyc
	rm -rf .mypy_cache/
	@echo "Clean complete!"

# Database setup
db-setup:
	@echo "Setting up database..."
	mysql -u root -p < schema.sql
	@echo "Database setup complete!"

# Create migrations backup
backup:
	@echo "Creating backup..."
	mkdir -p backups
	mysqldump -u root -p medilink > backups/medilink_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup created!"

# Development mode with auto-reload
dev:
	flask --app app run --debug --reload

# Production readiness check
prod-check:
	@echo "Checking production readiness..."
	@echo "1. Ensure FLASK_DEBUG=False in .env"
	@echo "2. Ensure SECRET_KEY is set and secure"
	@echo "3. Ensure database user has limited permissions"
	@echo "4. Enable HTTPS"
	@echo "5. Set up proper logging"
	@echo ""
