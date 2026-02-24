"""
Shared test configuration for Version B backend unit tests.

Bypasses CSRF protection globally so existing tests keep passing unchanged.
Only test_csrf.py uses a fixture that restores the real require_csrf.
"""
from backend.routers.csrf import require_csrf
from backend.main import app

# Bypass CSRF in all unit tests
app.dependency_overrides[require_csrf] = lambda: None
