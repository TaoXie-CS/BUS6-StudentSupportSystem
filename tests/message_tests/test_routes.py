import sys
import os
import pytest
import shutil

# Adjust import path for test compatibility
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app import app as test_app, db
from app.models import User, SupportMessage, UploadFile


# Test fixture: Set up isolated test environment
@pytest.fixture(scope="function")
def client():
    test_app.config['TESTING'] = True
    test_app.config['WTF_CSRF_ENABLED'] = False
    test_app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), "test_uploads")
    os.makedirs(test_app.config['UPLOAD_FOLDER'], exist_ok=True)

    with test_app.test_client() as client:
        with test_app.app_context():
            # Reset database for clean state
            db.drop_all()
            db.create_all()

            # Create test users
            teacher1 = User(
                username="teacher1",
                email="teacher1@test.com",
                role="teacher",
                teacher_type="academic",
                school_id="T001"
            )
            teacher1.set_password("password123")

            teacher2 = User(
                username="teacher2",
                email="teacher2@test.com",
                role="teacher",
                teacher_type="personal",
                school_id="T002"
            )
            teacher2.set_password("password123")

            student1 = User(
                username="student1",
                email="student1@test.com",
                role="student",
                school_id="S001"
            )
            student1.set_password("password123")

            db.session.add_all([teacher1, teacher2, student1])
            db.session.commit()

            yield client

            # Teardown: Clean up database and files
            db.session.remove()
            db.drop_all()
            if os.path.exists(test_app.config['UPLOAD_FOLDER']):
                shutil.rmtree(test_app.config['UPLOAD_FOLDER'], ignore_errors=True)


# Helper: Log in with given credentials
def login_user(client, email, password):
    client.get('/logout', follow_redirects=True)
    return client.post('/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)


# Test 1: Page access permissions
def test_unauthenticated_access(client):
    response = client.get('/', follow_redirects=True)
    assert b"Login" in response.data


def test_teacher_access_home(client):
    login_user(client, "teacher1@test.com", "password123")
    response = client.get('/')
    assert response.status_code == 200
    assert b"Messages" in response.data


def test_student_access_home(client):
    login_user(client, "student1@test.com", "password123")
    response = client.get('/')
    assert response.status_code == 200
    assert b"Messages" in response.data


# Test 2: Teacher-only permissions
def test_new_message_permission(client):
    # Student attempts to access new message page
    login_user(client, "student1@test.com", "password123")
    response = client.get('/new-message', follow_redirects=True)
    assert b"Only teachers can create messages" in response.data or b"Insufficient permissions" in response.data

    # Teacher can access successfully
    login_user(client, "teacher1@test.com", "password123")
    response = client.get('/new-message')
    assert response.status_code in (200, 302)


# Test 3: Message creation and data isolation
def test_teacher_create_message(client):
    login_user(client, "teacher1@test.com", "password123")
    response = client.post('/new-message', data={
        'subject': 'Test Message',
        'message_content': 'This is a test message',
        'urgency': 'urgent'
    }, follow_redirects=True)

    assert b"created successfully" in response.data or b"Created successfully" in response.data

    with test_app.app_context():
        msg = SupportMessage.query.filter_by(subject='Test Message').first()
        assert msg is not None


def test_teacher_data_isolation(client):
    # Teacher 1 creates a message
    login_user(client, "teacher1@test.com", "password123")
    client.post('/new-message', data={
        'subject': 'Teacher1 Private Msg',
        'message_content': 'Secret',
        'urgency': 'non-urgent'
    }, follow_redirects=True)

    # Teacher 2 cannot see messages from other teachers
    login_user(client, "teacher2@test.com", "password123")
    response = client.get('/messages')
    assert b"Teacher1 Private Msg" not in response.data

    # Students can view all messages
    login_user(client, "student1@test.com", "password123")
    response = client.get('/messages')
    assert b"Teacher1 Private Msg" in response.data


# Test 4: Message edit/delete permissions
def test_teacher_edit_own_message(client):
    login_user(client, "teacher1@test.com", "password123")
    # Create a test message
    client.post('/new-message', data={
        'subject': 'Old Subject',
        'message_content': 'Old Content',
        'urgency': 'non-urgent'
    }, follow_redirects=True)

    with test_app.app_context():
        msg = SupportMessage.query.first()
        assert msg is not None

    # Update the message
    response = client.post(f'/edit/{msg.id}', data={
        'subject': 'New Subject',
        'message_content': 'New Content',
        'urgency': 'urgent'
    }, follow_redirects=True)

    assert b"updated" in response.data or b"edit succeed" in response.data


def test_teacher_cannot_edit_others_message(client):
    # Teacher 1 creates a message
    login_user(client, "teacher1@test.com", "password123")
    client.post('/new-message', data={
        'subject': 'Not Yours',
        'message_content': 'No Touch',
        'urgency': 'non-urgent'
    }, follow_redirects=True)

    with test_app.app_context():
        msg = SupportMessage.query.first()
        assert msg is not None

    # Teacher 2 attempts to edit another teacher's message
    login_user(client, "teacher2@test.com", "password123")
    response = client.get(f'/edit/{msg.id}', follow_redirects=True)
    assert response.status_code in (403, 302) or b"Permission denied" in response.data


def test_teacher_delete_own_message(client):
    login_user(client, "teacher1@test.com", "password123")

    # Create a message to delete
    client.post('/new-message', data={
        'subject': 'To Delete',
        'message_content': 'Delete Me',
        'urgency': 'non-urgent'
    }, follow_redirects=True)

    with test_app.app_context():
        msg = SupportMessage.query.first()
        assert msg is not None

    # Delete the message
    response = client.get(f'/delete/{msg.id}', follow_redirects=True)
    assert b"deleted" in response.data or b"delete succeed" in response.data


# Test 5: Student message search and filtering
def test_student_message_search(client):
    login_user(client, "teacher1@test.com", "password123")

    client.post('/new-message', data={
        'subject': 'Math Homework',
        'message_content': 'Do page 10',
        'urgency': 'urgent'
    }, follow_redirects=True)

    client.post('/new-message', data={
        'subject': 'PE Class',
        'message_content': 'Bring sportswear',
        'urgency': 'non-urgent'
    }, follow_redirects=True)

    login_user(client, "student1@test.com", "password123")

    # Test search functionality
    response = client.get('/messages?search=Math')
    assert b"Math Homework" in response.data

    # Test urgency filter
    response = client.get('/messages?urgency=non-urgent')
    assert b"PE Class" in response.data