# Changelog

All notable changes to MediLink Pharmacy Management System are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-04-26

### Added
- Modular architecture with separate `validators.py` and `utils.py` modules
- Configuration management via `config.py` with environment-specific settings
- Comprehensive test suite with pytest
- SQL schema file with comments and sample views
- `.env.example` for easy environment setup
- `CONTRIBUTING.md` and `CHANGELOG.md` documentation
- API endpoints for low-stock medicines and today's appointments
- Patient appointment cancellation feature
- Audit logging table for security compliance
- Medicine expiry date validation

### Changed
- Refactored `app.py` with improved code organization and comments
- Updated pagination to use centralized `get_pagination_params()` helper
- Improved error handling with consistent patterns across all routes
- Enhanced input validation using centralized validator functions
- Updated `.gitignore` with comprehensive exclusions
- Expanded `requirements.txt` with optional production dependencies

### Fixed
- Added missing Symptoms field to appointment booking form
- Added missing Symptoms field to edit appointment form
- Created missing `403.html` error template
- Fixed inconsistent pagination handling across views
- Added proper transaction rollback on all database errors
- Fixed medicine stock validation in edit form

### Security
- Enhanced input sanitization with control character removal
- Added CSRF protection recommendations
- Improved password validation requirements
- Added audit logging infrastructure

## [2.0.0] - 2026-04-25

### Added
- Role-based dashboards for Doctor, Patient, and Pharmacist
- Appointment status tracking (Scheduled, In Progress, Completed)
- Prescription dispensing workflow with stock tracking
- Medicine inventory management with low-stock alerts
- Search and pagination for medicine inventory
- Filter tabs for appointment views
- Flash message notifications
- Structured logging throughout the application

### Changed
- Improved patient dashboard to show real-time status updates
- Enhanced prescription display with dispensing status
- Updated UI with consistent design system

### Fixed
- Fixed patient dashboard SQL errors (missing Status/Notes columns)
- Fixed corrupted template files (appointment.html, pharmacist.html)
- Fixed pagination and filter issues in appointment views
- Fixed patient dashboard to handle NULL status values gracefully

## [1.1.0] - 2026-04-24

### Added
- Input validation on all user-facing forms
- Rate limiting for appointment booking (max 3 per day)
- Username format validation
- Password strength requirements
- Access control logging

### Changed
- Enhanced XSS prevention with control character removal
- Improved error messages for better user experience

## [1.0.0] - 2026-04-18

### Added
- Initial release
- User authentication with PBKDF2:SHA256 password hashing
- Doctor features: appointments, prescriptions
- Patient features: book appointments, view prescriptions
- Pharmacist features: medicine inventory, dispensing
- MySQL database integration
- Responsive HTML templates
- Basic security measures

---

## Version History

| Version | Date | Status |
|---------|------|--------|
| 2.1.0 | 2026-04-26 | Current |
| 2.0.0 | 2026-04-25 | Stable |
| 1.1.0 | 2026-04-24 | Deprecated |
| 1.0.0 | 2026-04-18 | Legacy |

## Migration Guide

### From 2.0.0 to 2.1.0

No breaking changes. Simply update your files and run:

```bash
pip install -r requirements.txt
```

### From 1.x to 2.0.0

Database schema changes required. Run:

```sql
ALTER TABLE Appointment ADD COLUMN IF NOT EXISTS Status VARCHAR(20) DEFAULT 'Scheduled';
ALTER TABLE Appointment ADD COLUMN IF NOT EXISTS Notes TEXT;
```

## Upcoming Features (Roadmap)

- [ ] User profile management
- [ ] Password reset functionality
- [ ] Email notifications
- [ ] Medicine expiry alerts
- [ ] Appointment reminders
- [ ] Report generation
- [ ] Mobile app integration
- [ ] Multi-language support
