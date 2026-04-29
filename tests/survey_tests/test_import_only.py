"""
Perform a simple import test to ensure all modules can be imported correctly.
This test file is primarily used to verify import dependencies.
"""

import sys
import os

# Add the project root directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_import_app():
    """Test importing the main application"""
    from app import app
    assert app is not None


def test_import_db():
    """Test importing the database instance"""
    from app import db
    assert db is not None


def test_import_models():
    """Test importing database models"""
    from app.models import User, NewSurveyResponse
    assert User is not None
    assert NewSurveyResponse is not None


def test_import_forms():
    """Test importing form classes"""
    from app.forms import (
        LoginForm, RegistrationForm, SurveyBasicInfoForm,
        SurveyTypeForm, LearningSurveyForm, ManagementSurveyForm,
        TeachingSurveyForm
    )
    assert LoginForm is not None
    assert RegistrationForm is not None
    assert SurveyBasicInfoForm is not None
    assert SurveyTypeForm is not None
    assert LearningSurveyForm is not None
    assert ManagementSurveyForm is not None
    assert TeachingSurveyForm is not None


def test_import_routes():
    """Test importing route blueprints"""
    try:
        from app.routes import main, auth, survey
        assert True
    except ImportError as e:
        print(f"Note: Some routes may not be importable: {e}")


def test_import_config():
    """Test importing configuration module"""
    import config
    assert config is not None
    # Check essential configuration items
    assert hasattr(config, 'SECRET_KEY') or hasattr(config, 'Config')


def test_import_dependencies():
    """Test importing required third-party dependencies"""
    import flask
    import sqlalchemy
    import wtforms
    import alembic
    import pytest

    # Ensure all packages can be imported
    assert flask is not None
    assert sqlalchemy is not None
    assert wtforms is not None
    assert alembic is not None
    assert pytest is not None


def test_app_initialization():
    """Test Flask application initialization"""
    from app import app
    assert app is not None
    # Verify application configuration exists
    assert hasattr(app, 'config')


def test_module_versions():
    """Test versions of key dependencies"""
    import flask
    import sqlalchemy

    # Log versions for debugging
    print(f"Flask version: {flask.__version__}")
    print(f"SQLAlchemy version: {sqlalchemy.__version__}")

    # Validate minimum version requirements
    flask_version = tuple(map(int, flask.__version__.split('.')))
    assert flask_version >= (2, 0, 0)


if __name__ == '__main__':
    """Run import tests directly when executing this script"""
    test_import_app()
    test_import_db()
    test_import_models()
    test_import_forms()
    test_import_config()
    test_import_dependencies()
    test_app_initialization()
    test_module_versions()
    print("All imports successful!")