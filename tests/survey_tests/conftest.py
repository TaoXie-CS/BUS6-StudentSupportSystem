import pytest
import sys
import os
import tempfile
from datetime import datetime
from flask import Flask, session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db
from app.models import User, NewSurveyResponse
from app.forms import LoginForm, RegistrationForm, SurveyBasicInfoForm, SurveyTypeForm, \
    LearningSurveyForm, ManagementSurveyForm, TeachingSurveyForm


@pytest.fixture(scope='session')
def app():
    """Create a test application instance for non-factory mode projects"""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp()

    # Configure application for testing
    from app import app as flask_app
    flask_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False
    })

    with flask_app.app_context():
        db.create_all()
        create_test_data()

    yield flask_app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope='function')
def client(app):
    """Provide a test client for HTTP requests"""
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture(scope='function')
def runner(app):
    """Provide a CLI test runner for command-line commands"""
    return app.test_cli_runner()


def create_test_data():
    """Initialize database with test users and survey data"""
    try:
        with db.engine.connect() as conn:
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()

            if 'user' in tables:
                conn.execute(db.text("DELETE FROM user"))
                conn.commit()

        # Create test users
        users = [
            User(username='student1', email='student1@test.com',
                 school_id='S001', role='student'),
            User(username='student2', email='student2@test.com',
                 school_id='S002', role='student'),
            User(username='teacher1', email='teacher1@test.com',
                 school_id='T001', role='teacher'),
            User(username='admin1', email='admin1@test.com',
                 school_id='A001', role='admin')
        ]

        for user in users:
            user.set_password('password')
            db.session.add(user)
        db.session.commit()

        # Create sample survey responses
        existing_surveys = [
            NewSurveyResponse(
                user_id=1,
                survey_type='learning',
                grade='Junior',
                major='Computer Science',
                course_schedule='Very Satisfied',
                course_quality='Satisfied',
                knowledge_mastery='Neutral',
                other_learning='Great courses overall.'
            ),
            NewSurveyResponse(
                user_id=2,
                survey_type='management',
                grade='Senior',
                major='Business',
                campus_cleanliness='Very Satisfied',
                cafeteria='Satisfied',
                holiday_arrangement='Neutral',
                student_activities='Dissatisfied',
                other_management='More activities needed.'
            )
        ]

        for survey in existing_surveys:
            db.session.add(survey)
        db.session.commit()

    except Exception as e:
        print(f"Error creating test data: {e}")
        db.session.rollback()
        raise


@pytest.fixture
def auth(client, app):
    """Authentication fixture for login/logout helper methods"""

    class AuthActions:
        def __init__(self, client):
            self._client = client

        def login(self, username='student1', password='password'):
            """Log in a test user with provided credentials"""
            return self._client.post('/login', data={
                'username': username,
                'password': password
            }, follow_redirects=True)

        def logout(self):
            """Log out the current user"""
            return self._client.get('/logout', follow_redirects=True)

    return AuthActions(client)


# Test data for messaging module
try:
    from app.models import Message
    MESSAGE_MODEL_EXISTS = True
except ImportError:
    class Message:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    MESSAGE_MODEL_EXISTS = False


def create_test_data():
    """Populate database with test data including users, surveys, and messages"""
    try:
        with db.engine.connect() as conn:
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()

            if 'user' in tables:
                conn.execute(db.text("DELETE FROM user"))
                conn.commit()

        # Create test users
        users = [
            User(username='student1', email='student1@test.com',
                 school_id='S001', role='student'),
            User(username='student2', email='student2@test.com',
                 school_id='S002', role='student'),
            User(username='teacher1', email='teacher1@test.com',
                 school_id='T001', role='teacher'),
            User(username='admin1', email='admin1@test.com',
                 school_id='A001', role='admin')
        ]

        for user in users:
            user.set_password('password')
            db.session.add(user)
        db.session.commit()

        # Create test survey data
        existing_surveys = [
            NewSurveyResponse(
                user_id=1,
                survey_type='learning',
                grade='Junior',
                major='Computer Science',
                course_schedule='Very Satisfied',
                course_quality='Satisfied',
                knowledge_mastery='Neutral',
                other_learning='Great courses overall.'
            ),
            NewSurveyResponse(
                user_id=2,
                survey_type='management',
                grade='Senior',
                major='Business',
                campus_cleanliness='Very Satisfied',
                cafeteria='Satisfied',
                holiday_arrangement='Neutral',
                student_activities='Dissatisfied',
                other_management='More activities needed.'
            )
        ]

        for survey in existing_surveys:
            db.session.add(survey)
        db.session.commit()

        # Create test messages if model exists
        if MESSAGE_MODEL_EXISTS:
            with db.engine.connect() as conn:
                if 'message' in tables:
                    conn.execute(db.text("DELETE FROM message"))
                    conn.commit()

            test_messages = [
                Message(
                    sender_id=4,
                    receiver_id=1,
                    title="System Notification",
                    content="Reminder: deadline for filling out the questionnaire",
                    is_read=False,
                    created_at=datetime.now()
                ),
                Message(
                    sender_id=4,
                    receiver_id=2,
                    title="Important Notice",
                    content="Course adjustment for the new semester",
                    is_read=True,
                    created_at=datetime.now()
                )
            ]

            for msg in test_messages:
                db.session.add(msg)
            db.session.commit()

    except Exception as e:
        print(f"Error creating test data: {e}")
        db.session.rollback()
        raise