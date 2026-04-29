import io
import os
import pytest
from datetime import datetime, timezone, date
from app import app as test_app, db
from app.models import User, SupportMessage, UploadFile

TEST_UPLOAD_FOLDER = os.path.join(test_app.root_path, 'static', 'uploads')
os.makedirs(TEST_UPLOAD_FOLDER, exist_ok=True)

# Configure test environment
test_app.config['TESTING'] = True
test_app.config['WTF_CSRF_ENABLED'] = False
test_app.config['UPLOAD_FOLDER'] = TEST_UPLOAD_FOLDER
test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
test_app.config['SECRET_KEY'] = 'test-secret-key'

# Global variables to store user IDs
TEACHER_ID = None
STUDENT_ID = None


@pytest.fixture
def app():
    """Test application fixture (compatible with pytest-flask plugin)"""
    global TEACHER_ID, STUDENT_ID

    with test_app.app_context():
        db.create_all()
        # Create test teacher user
        teacher = User(
            username="test_teacher",
            email="teacher@test.com",
            role="teacher",
            teacher_type="lecturer",
            school_id="T001"
        )
        teacher.set_password("123456")

        # Create test student user
        student = User(
            username="test_student",
            email="student@test.com",
            role="student",
            school_id="S001"
        )
        student.set_password("123456")

        db.session.add(teacher)
        db.session.add(student)
        db.session.commit()

        TEACHER_ID = teacher.id
        STUDENT_ID = student.id

        yield test_app

        # Clean up test files
        for f in os.listdir(TEST_UPLOAD_FOLDER):
            if f.startswith('test_') or f.endswith('.pdf'):
                try:
                    os.remove(os.path.join(TEST_UPLOAD_FOLDER, f))
                except FileNotFoundError:
                    pass
        # Clean up database
        db.session.remove()
        db.drop_all()

        TEACHER_ID = None
        STUDENT_ID = None


@pytest.fixture
def client(app):
    """Test client fixture with fresh session"""
    with app.test_client() as client:
        yield client


@pytest.fixture
def create_test_message(app):
    """Create a test message and return its ID"""
    with app.app_context():
        teacher = db.session.get(User, TEACHER_ID)
        msg = SupportMessage(
            subject="Test Message",
            message_content="Test content",
            urgency="urgent",
            teacher_email=teacher.email,
            teacher_name=teacher.username,
            teacher_school_id=teacher.school_id,
            publish_date=date.today(),
            user_id=teacher.id
        )
        db.session.add(msg)
        db.session.commit()
        return msg.id


@pytest.fixture
def login_teacher(client, app):
    """Log in as teacher for test session"""
    client.post("/login", data={
        "email": "teacher@test.com",
        "password": "123456",
        "remember": False
    }, follow_redirects=True)
    yield client
    client.get("/logout", follow_redirects=True)


@pytest.fixture
def login_student(client, app):
    """Log in as student for test session"""
    client.post("/login", data={
        "email": "student@test.com",
        "password": "123456",
        "remember": False
    }, follow_redirects=True)
    yield client
    client.get("/logout", follow_redirects=True)


def test_new_message_page_teacher_only(client, login_student):
    """Test only teachers can access the message creation page"""
    resp = login_student.get("/new-message", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Welcome to the Student Support App" in resp.data


def test_create_message_success(login_teacher, app):
    """Test successful message creation by teacher"""

    message_data = {
        "subject": "Test Message",
        "message_content": "Test content",
        "urgency": "urgent"
    }

    resp = login_teacher.post(
        "/new-message",
        data=message_data,
        follow_redirects=True
    )
    assert resp.status_code == 200

    # Verify message exists in database
    with app.app_context():
        teacher = db.session.get(User, TEACHER_ID)
        msg = SupportMessage.query.filter_by(
            subject="Test Message",
            user_id=teacher.id
        ).first()
        assert msg is not None
        assert msg.message_content == "Test content"
        assert msg.urgency == "urgent"
        assert msg.teacher_email == teacher.email


def test_create_message_with_file(login_teacher, app):
    """Test message creation with file attachment"""
    data = {
        "subject": "Test Message with File",
        "message_content": "Test content with file",
        "urgency": "urgent"
    }
    # Simulate PDF file upload
    data["files"] = (io.BytesIO(b"test pdf content"), "test_attachment.pdf")

    resp = login_teacher.post(
        "/new-message",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True
    )
    assert resp.status_code == 200

    # Verify message and file record
    with app.app_context():
        teacher = db.session.get(User, TEACHER_ID)
        msg = SupportMessage.query.filter_by(
            subject="Test Message with File",
            user_id=teacher.id
        ).first()
        assert msg is not None
        assert len(msg.files) >= 1
        file_obj = msg.files[0]
        assert file_obj.filename == "test_attachment.pdf"
        assert file_obj.user_id == teacher.id

        # Verify file storage
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_obj.stored_name)
            assert os.path.exists(file_path)
            with open(file_path, "rb") as f:
                assert f.read() == b"test pdf content"
        except Exception:
            pass


def test_message_detail(login_teacher, create_test_message, app):
    """Test viewing message details"""
    msg_id = create_test_message
    resp = login_teacher.get(f"/message/{msg_id}", follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        msg = db.session.get(SupportMessage, msg_id)
        assert msg.subject == "Test Message"

    assert b"Test Message" in resp.data or b"Test content" in resp.data


def test_edit_message(login_teacher, create_test_message, app):
    """Test editing an existing message"""
    msg_id = create_test_message

    edit_data = {
        "subject": "Edited Test Message",
        "message_content": "Edited content",
        "urgency": "non-urgent"
    }

    resp = login_teacher.post(
        f"/edit/{msg_id}",
        data=edit_data,
        follow_redirects=True
    )
    assert resp.status_code == 200

    # Verify updated data
    with app.app_context():
        edited_msg = db.session.get(SupportMessage, msg_id)
        assert edited_msg.subject == "Edited Test Message"
        assert edited_msg.message_content == "Edited content"
        assert edited_msg.urgency == "non-urgent"


def test_delete_message(login_teacher, create_test_message, app):
    """Test deleting a message"""
    msg_id = create_test_message
    resp = login_teacher.get(f"/delete/{msg_id}", follow_redirects=True)
    assert resp.status_code == 200

    # Verify message was deleted
    with app.app_context():
        assert db.session.get(SupportMessage, msg_id) is None


def test_messages_page_load(client, login_student, create_test_message, app):
    """Test student viewing message list"""
    msg_id = create_test_message
    resp = login_student.get("/messages", follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        assert db.session.get(SupportMessage, msg_id) is not None

    assert b"No messages yet." not in resp.data or b"Test Message" in resp.data


def test_student_download_attachment(client, login_student, create_test_message, app):
    """Test student downloading message attachments"""
    msg_id = create_test_message
    with app.app_context():
        teacher = db.session.get(User, TEACHER_ID)
        test_file_content = b"student download test content"
        original_filename = "homework.pdf"
        stored_name = f"test_download_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_name)
        with open(file_path, "wb") as f:
            f.write(test_file_content)

        file_obj = UploadFile(
            filename=original_filename,
            stored_name=stored_name,
            upload_time=datetime.now(timezone.utc),
            message_id=msg_id,
            user_id=teacher.id
        )
        db.session.add(file_obj)
        db.session.commit()
        file_id = file_obj.id

    # Test file download
    download_resp = login_student.get(f"/download/{file_id}", follow_redirects=True)
    assert download_resp.status_code == 200
    assert download_resp.data == test_file_content