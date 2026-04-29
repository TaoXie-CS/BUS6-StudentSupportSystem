import pytest
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(os.path.join(CURRENT_DIR, 'app', '__init__.py')):
    PROJECT_DIR = CURRENT_DIR
else:
    PROJECT_DIR = os.path.join(CURRENT_DIR, 'BUS6-StudentSupportSystem')
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from app import app, db
from app.models import User, SupportMessage
from datetime import date

# Test configuration
TEST_TEACHER_MAIL = "teacher_ai@example.com"
TEST_STUDENT_MAIL = "student_ai@example.com"
TEST_PWD = "test12345"

@pytest.fixture(scope="module")
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    original_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            db.create_all()

            # Create test teacher
            teacher = User(username="teacher_ai", email=TEST_TEACHER_MAIL, role="teacher")
            teacher.set_password(TEST_PWD)
            db.session.add(teacher)
            db.session.flush()

            # Create test student
            student = User(username="student_ai", email=TEST_STUDENT_MAIL, role="student")
            student.set_password(TEST_PWD)
            db.session.add(student)
            db.session.flush()

            # Create test message
            msg = SupportMessage(
                subject="Midterm Exam",
                message_content="Python midterm is on April 24",
                urgency="urgent",
                teacher_email=teacher.email,
                teacher_name=teacher.username,
                teacher_school_id="T001",
                publish_date=date.today(),
                user_id=teacher.id
            )
            db.session.add(msg)
            db.session.commit()

        yield client

        with app.app_context():
            db.session.remove()
            db.drop_all()
            app.config['SQLALCHEMY_DATABASE_URI'] = original_uri

# ------------------------------ Helper methods ------------------------------
def login_student(client):
    """Log in test student via login endpoint"""
    client.get('/logout')
    return client.post('/login', data=dict(
        email=TEST_STUDENT_MAIL, password=TEST_PWD, remember=False
    ), follow_redirects=True)

def login_teacher(client):
    """Log in test teacher via login endpoint"""
    client.get('/logout')
    return client.post('/login', data=dict(
        email=TEST_TEACHER_MAIL, password=TEST_PWD, remember=False
    ), follow_redirects=True)

# ------------------------------ Test cases ------------------------------
def test_unauthenticated_user_redirected(client):
    """Unauthenticated users are redirected to login"""
    resp = client.get("/ai-assistant", follow_redirects=True)
    assert resp.status_code == 200
    assert '/login' in resp.request.path

def test_teacher_blocked_from_ai(client):
    """Test teachers are blocked from accessing the AI Assistant"""
    login_teacher(client)
    resp = client.get("/ai-assistant", follow_redirects=True)
    assert resp.status_code == 200
    assert resp.request.path == '/'

def test_student_can_access_ai(client):
    """Test students can successfully access the AI Assistant page"""
    login_student(client)
    resp = client.get("/ai-assistant")
    assert resp.status_code == 200

def test_ai_summarize_function(client):
    """Test AI summarize message functionality"""
    login_student(client)
    resp = client.post("/ai-assistant", data={"ai_action": "summarize"})
    assert resp.status_code == 200
    assert b'ai response:' in resp.data.lower()

def test_ai_deadline_reminder(client):
    """Test AI deadline extraction functionality"""
    login_student(client)
    resp = client.post("/ai-assistant", data={"ai_action": "deadlines"})
    assert resp.status_code == 200
    assert b'ai response:' in resp.data.lower()

def test_ai_motivation(client):
    """Test AI motivational message functionality"""
    login_student(client)
    resp = client.post("/ai-assistant", data={"ai_action": "motivation"})
    assert resp.status_code == 200
    assert b'ai response:' in resp.data.lower()

def test_ai_invalid_action(client):
    """Invalid ai_action does not crash the application"""
    login_student(client)
    resp = client.post("/ai-assistant", data={"ai_action": "invalid_action"})
    assert resp.status_code == 200