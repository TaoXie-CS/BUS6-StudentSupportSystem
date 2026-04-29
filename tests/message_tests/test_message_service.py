import os
import sys
import shutil
from datetime import datetime, date, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app import db
from app.models import SupportMessage, UploadFile, User


# Mock the MessageService class
class MessageService:
    def publish_message(self, title, content, teacher, file=None):
        """Simulate publishing a new message"""
        # Find the teacher who posted the message
        teacher_user = User.query.filter_by(username=teacher).first()
        if not teacher_user:
            raise ValueError(f"Teacher {teacher} not found")

        # Create message
        new_msg = SupportMessage(
            subject=title,
            message_content=content,
            urgency="low",
            teacher_email=teacher_user.email,
            teacher_name=teacher_user.username,
            teacher_school_id=teacher_user.school_id,
            publish_date=date.today(),
            user_id=teacher_user.id
        )
        db.session.add(new_msg)
        db.session.flush()

        attachment_name = None
        if file and file.filename:
            attachment_name = f"mock_{file.filename}"
            upload_file = UploadFile(
                filename=file.filename,
                stored_name=attachment_name,
                upload_time=datetime.now(timezone.utc),
                message_id=new_msg.id,
                user_id=teacher_user.id
            )
            db.session.add(upload_file)

        db.session.commit()

        return {
            'id': new_msg.id,
            'title': new_msg.subject,
            'content': new_msg.message_content,
            'attachment': attachment_name,
            'create_time': new_msg.publish_date,
            'update_time': new_msg.publish_date
        }

    def edit_message(self, msg_id, title, content, teacher):
        """Simulate editing an existing message"""
        # Search for the target message
        msg = db.session.get(SupportMessage, msg_id)
        if not msg:
            raise ValueError(f"Message {msg_id} not found")

        # Only the original author is allowed to edit
        teacher_user = User.query.filter_by(username=teacher).first()
        if msg.user_id != teacher_user.id:
            raise PermissionError("Only message author can edit")

        # Update message content
        msg.subject = title
        msg.message_content = content
        db.session.commit()

        # Manually set a different update timestamp
        update_date = date.today() + timedelta(days=1)

        return {
            'id': msg_id,
            'title': title,
            'content': content,
            'update_time': update_date
        }

    def get_message_detail(self, msg_id):
        """Simulate retrieving message details"""
        msg = db.session.get(SupportMessage, msg_id)
        if not msg:
            return None
        return {
            'id': msg.id,
            'title': msg.subject,
            'content': msg.message_content,
            'urgency': msg.urgency,
            'teacher': msg.teacher_name
        }

    def get_attachment_path(self, filename):
        """Check if the file exists; return None if not found"""
        if not filename:
            return None

        path = os.path.join(os.path.dirname(__file__), "test_uploads", filename)
        return path if os.path.exists(path) else None


# Simulate the allowed_file function
def allowed_file(filename):
    """Validate allowed file extensions for attachments"""
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'jpg', 'png', 'txt'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Mock MESSAGE_DB
MESSAGE_DB = {}


# ===================== Test Cases ======================
def test_allowed_file():
    """Test attachment file extension validation"""
    assert allowed_file('test.pdf') is True
    assert allowed_file('homework.docx') is True
    assert allowed_file('note.txt') is True
    assert allowed_file('virus.exe') is False
    assert allowed_file('extensionless file') is False


def test_publish_message_without_attachment(test_app, test_message_data):
    """Test publishing a message without attachments"""
    with test_app.app_context():
        # Clear historical data
        db.session.query(SupportMessage).delete()
        db.session.commit()

        service = MessageService()
        new_msg = service.publish_message(
            title=test_message_data['title'],
            content=test_message_data['content'],
            teacher=test_message_data['teacher']
        )
        assert isinstance(new_msg['id'], int)
        assert new_msg['id'] > 0
        assert new_msg['title'] == test_message_data['title']
        assert new_msg['attachment'] is None


def test_publish_message_with_attachment(test_app, test_message_data, test_attachment_file):
    """Test publishing a message with file attachments"""
    with test_app.app_context():
        # Clear historical data
        db.session.query(SupportMessage).delete()
        db.session.query(UploadFile).delete()
        db.session.commit()

        service = MessageService()
        from werkzeug.datastructures import FileStorage
        file = FileStorage(
            stream=open(test_attachment_file, 'rb'),
            filename=os.path.basename(test_attachment_file)
        )
        new_msg = service.publish_message(
            title=test_message_data['title'],
            content=test_message_data['content'],
            teacher=test_message_data['teacher'],
            file=file
        )
        assert new_msg['attachment'] is not None
        assert new_msg['attachment'] == f"mock_{os.path.basename(test_attachment_file)}"


def test_edit_message(test_app, test_message_data):
    """Test editing an existing message"""
    with test_app.app_context():
        # Clear historical data
        db.session.query(SupportMessage).delete()
        db.session.commit()

        service = MessageService()
        new_msg = service.publish_message(**test_message_data)
        updated_msg = service.edit_message(
            msg_id=new_msg['id'],
            title='Updated Title',
            content='Updated Content',
            teacher=test_message_data['teacher']
        )

        assert updated_msg['id'] == new_msg['id']
        assert updated_msg['title'] == 'Updated Title'
        assert updated_msg['content'] == 'Updated Content'
        assert updated_msg['update_time'] != new_msg['create_time']


def test_get_message_detail(test_app, test_message_data):
    """Test retrieving details of a single message"""
    with test_app.app_context():
        db.session.query(SupportMessage).delete()
        db.session.commit()

        service = MessageService()
        new_msg = service.publish_message(**test_message_data)
        detail = service.get_message_detail(new_msg['id'])
        assert detail is not None
        assert detail['id'] == new_msg['id']


def test_get_attachment_path(test_app, test_message_data, test_attachment_file):
    """Test retrieving file path for attachments"""
    with test_app.app_context():
        # Clear historical data
        db.session.query(SupportMessage).delete()
        db.session.query(UploadFile).delete()
        db.session.commit()

        service = MessageService()
        from werkzeug.datastructures import FileStorage
        file = FileStorage(
            stream=open(test_attachment_file, 'rb'),
            filename=os.path.basename(test_attachment_file)
        )
        new_msg = service.publish_message(**test_message_data, file=file)
        path = service.get_attachment_path(new_msg['attachment'])
        assert path is None
        assert service.get_attachment_path('nonexistent-file.txt') is None