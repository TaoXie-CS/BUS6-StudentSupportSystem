import pytest
import os
import sys
import shutil

# Add the project root directory to the Python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Import the app and db from the existing project
from app import app, db
from app.models import User

# Test-specific app fixture
@pytest.fixture
def test_app():
    # Override configuration for testing (runtime only, no file changes)
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "UPLOAD_FOLDER": os.path.join(os.path.dirname(__file__), "test_uploads")
    })

    # Initialize test database
    with app.app_context():
        db.create_all()
        # Create test users (matches existing User model fields)
        teacher = User(
            username="testteacher",
            email="teacher@test.com",
            role="teacher",
            school_id="T001"
        )

        if hasattr(User, 'set_password'):
            teacher.set_password("123456")
        else:
            teacher.password_hash = "pbkdf2:sha256:150000$xxxxxx$xxxxxx"

        student = User(
            username="teststudent",
            email="student@test.com",
            role="student",
            school_id="S001"
        )
        if hasattr(User, 'set_password'):
            student.set_password("123456")
        else:
            student.password_hash = "pbkdf2:sha256:150000$xxxxxx$xxxxxx"

        db.session.add_all([teacher, student])
        db.session.commit()

        yield app

        # Clean up after tests
        db.session.remove()
        db.drop_all()
        if os.path.exists(app.config["UPLOAD_FOLDER"]):
            shutil.rmtree(app.config["UPLOAD_FOLDER"], ignore_errors=True)

# Test client fixture
@pytest.fixture
def client(test_app):
    return test_app.test_client()

# Teacher login fixture
@pytest.fixture
def login_teacher(client):
    response = client.post("/login", data={
        "email": "teacher@test.com",
        "password": "123456"
    }, follow_redirects=True)
    assert b"Login" not in response.data
    yield client
    client.get("/logout", follow_redirects=True)

# Student login fixture
@pytest.fixture
def login_student(client):
    response = client.post("/login", data={
        "email": "student@test.com",
        "password": "123456"
    }, follow_redirects=True)
    assert b"Login" not in response.data
    yield client
    client.get("/logout", follow_redirects=True)

# Common test data fixture
@pytest.fixture
def test_message():
    return {"subject": "Test Message", "message_content": "Test content", "urgency": "urgent"}

@pytest.fixture
def test_attachment_file(tmp_path):
    file_path = tmp_path / "test_attachment.pdf"
    file_path.write_bytes(b"test attachment content")
    return str(file_path)

@pytest.fixture
def test_message_data():
    return {"title": "Test Title", "content": "Test Content", "teacher": "testteacher"}