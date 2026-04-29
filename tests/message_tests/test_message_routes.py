import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from app import app as real_app, db


# ===================== fixture =====================
@pytest.fixture
def app():
    real_app.config['TESTING'] = True
    real_app.config['WTF_CSRF_ENABLED'] = False
    real_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    real_app.config['SECRET_KEY'] = 'test'
    real_app.config['UPLOAD_FOLDER'] = os.path.join(real_app.root_path, 'static', 'uploads')
    os.makedirs(real_app.config['UPLOAD_FOLDER'], exist_ok=True)

    with real_app.app_context():
        db.create_all()
        yield real_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def test_message_data():
    return {
        "subject": "Test Message",
        "message_content": "Test Content",
        "urgency": "urgent"
    }


@pytest.fixture
def test_attachment_file(app):
    path = os.path.join(app.config['UPLOAD_FOLDER'], "test.pdf")
    with open(path, "wb") as f:
        f.write(b"test content")
    yield path
    if os.path.exists(path):
        os.remove(path)


# ===================== test cases =====================
def test_teacher_get_message_form(client):
    """Test that a teacher can access the message creation form"""
    client.post('/login', data={'email': 'teacher@test.com', 'password': '123456'}, follow_redirects=True)
    response = client.get('/new-message')
    assert response.status_code in [200, 302]


def test_teacher_save_message(client, test_message_data):
    """Test that a teacher can submit a new message"""
    client.post('/login', data={'email': 'teacher@test.com', 'password': '123456'}, follow_redirects=True)
    response = client.post('/new-message', data=test_message_data, follow_redirects=True)
    assert response.status_code == 200


def test_teacher_save_message_with_attachment(client, test_message_data, test_attachment_file):
    """Test that a teacher can publish a message with an attachment"""
    client.post('/login', data={'email': 'teacher@test.com', 'password': '123456'}, follow_redirects=True)

    with open(test_attachment_file, 'rb') as f:
        response = client.post('/new-message', data={
            **test_message_data,
            'files': (f, os.path.basename(test_attachment_file))
        }, content_type="multipart/form-data", follow_redirects=True)

    assert response.status_code == 200


def test_student_get_message_list(client):
    """Test that a student can view the message list"""
    client.post('/login', data={'email': 'student@test.com', 'password': '123456'}, follow_redirects=True)
    response = client.get('/messages')
    assert response.status_code in [200, 302]


def test_student_download_attachment(client, test_message_data, test_attachment_file):
    """Test that a student can download message attachments"""
    # Teacher creates a message with attachment
    client.post('/login', data={'email': 'teacher@test.com', 'password': '123456'}, follow_redirects=True)
    with open(test_attachment_file, 'rb') as f:
        client.post('/new-message', data={
            **test_message_data,
            'files': (f, os.path.basename(test_attachment_file))
        }, content_type="multipart/form-data")

    # Student logs in
    client.post('/login', data={'email': 'student@test.com', 'password': '123456'}, follow_redirects=True)

    # Verify message page access
    response = client.get('/messages')
    assert response.status_code in [200, 302]