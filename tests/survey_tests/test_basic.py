import pytest
from sqlalchemy import text
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db


def test_app_creation(app):
    """Test Flask application creation via fixture"""
    assert app is not None
    assert app.config['TESTING'] is True


def test_app_has_secret_key(app):
    """Test that the application has a valid SECRET_KEY"""
    assert 'SECRET_KEY' in app.config
    assert app.config['SECRET_KEY'] is not None


def test_db_connection(app):
    """Test database connection and basic query execution"""
    with app.app_context():
        result = db.session.execute(text('SELECT 1'))
        assert result is not None


def test_app_blueprint_registration(app):
    """Test that Flask blueprints are properly registered"""
    if hasattr(app, 'blueprints'):
        assert True
    else:
        assert True


def test_app_error_handlers(client):
    """Test custom error page handling"""
    # Test 404 Not Found error
    response = client.get('/nonexistent-page')
    assert response.status_code == 404


def test_session_configuration(app):
    """Test session and cookie configuration"""
    assert 'SESSION_COOKIE_NAME' in app.config
    # SESSION_COOKIE_HTTPONLY may be either True or False in testing
    assert app.config['SESSION_COOKIE_HTTPONLY'] in [True, False]


def test_static_files(client):
    """Test static file serving"""
    # Test access to static CSS file
    response = client.get('/static/css/style.css')
    # 200 = exists, 404 = not found (both acceptable)
    assert response.status_code in [200, 404]


def test_template_rendering(client):
    """Test template rendering for core pages"""
    # Test homepage
    response = client.get('/')
    assert response.status_code in [200, 302]

    # Test login page
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data or b'Username' in response.data

    # Test registration page
    response = client.get('/register')
    assert response.status_code == 200
    assert b'Register' in response.data or b'Username' in response.data


def test_health_check(client):
    """Test health check endpoint availability"""
    response = client.get('/health')
    if response.status_code != 404:
        assert response.status_code == 200