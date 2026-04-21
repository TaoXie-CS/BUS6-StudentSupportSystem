from flask_login import UserMixin

from app import db
import sqlalchemy.orm as so
import sqlalchemy as sa
from datetime import datetime, date, timezone
from werkzeug.security import generate_password_hash, check_password_hash


# User (student / teacher)
class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), unique=True, index=True, nullable=False)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), unique=True, index=True, nullable=False)
    password_hash: so.Mapped[str] = so.mapped_column(sa.String(256), nullable=False)
    role: so.Mapped[str] = so.mapped_column(sa.String(20), nullable=False, default="student")
    teacher_type: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=True, default="")
    school_id: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, nullable=True)
    messages: so.WriteOnlyMapped[list["SupportMessage"]] = so.relationship(back_populates="author")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


# Support Message Model (Core business model)
class SupportMessage(db.Model):
    # Primary key (unique identifier for each message)
    id: so.Mapped[int] = so.mapped_column(primary_key=True)

    # Subject (renamed from message_title, removed course_name)
    subject: so.Mapped[str] = so.mapped_column(sa.String(256), index=True, nullable=False)

    # Message content (long text, max length 500, indexed for fast search, non-nullable)
    message_content: so.Mapped[str] = so.mapped_column(sa.String(500), index=True, nullable=False)

    # Urgency: urgent / non-urgent (replaced numeric priority 1-10)
    urgency: so.Mapped[str] = so.mapped_column(sa.String(20), index=True, nullable=False)

    # Teacher email address (max length 255, non-unique, indexed for fast search, non-nullable)
    teacher_email: so.Mapped[str] = so.mapped_column(sa.String(255), nullable=False, unique=False, index=True)

    # Teacher name (auto filled from login user)
    teacher_name: so.Mapped[str] = so.mapped_column(sa.String(100), nullable=False)

    # Teacher school ID (auto filled from login user)
    teacher_school_id: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=False)

    # Publish date (auto set on submission, used for query and AI analysis)
    publish_date: so.Mapped[date] = so.mapped_column(sa.Date, nullable=False, default=date.today)

    # User ID
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey("user.id"), nullable=False)
    # Author
    author: so.Mapped["User"] = so.relationship(back_populates="messages")
    # linked files
    files: so.Mapped[list["UploadFile"]] = so.relationship(back_populates="message", cascade="all, delete-orphan")
    # Read records for students
    read_records = db.relationship('MessageRead', backref='message', lazy=True, passive_deletes=True)

    def __repr__(self):
        return f'<SupportMessage {self.id} - {self.subject}>'


# ====================== [Modified] New Survey Response Model ======================
class NewSurveyResponse(db.Model):
    """New survey response model"""
    id: so.Mapped[int] = so.mapped_column(primary_key=True)

    # Student basic information
    grade: so.Mapped[str] = so.mapped_column(sa.String(20), nullable=False)
    major: so.Mapped[str] = so.mapped_column(sa.String(100), nullable=False)

    # Survey type
    survey_type: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=False)

    # Learning situation survey fields
    course_schedule: so.Mapped[str] = so.mapped_column(sa.String(10), nullable=True)
    course_quality: so.Mapped[str] = so.mapped_column(sa.String(10), nullable=True)
    knowledge_mastery: so.Mapped[str] = so.mapped_column(sa.String(10), nullable=True)
    other_learning: so.Mapped[str] = so.mapped_column(sa.Text, nullable=True)

    # School management satisfaction survey fields
    campus_cleanliness: so.Mapped[str] = so.mapped_column(sa.String(10), nullable=True)
    cafeteria: so.Mapped[str] = so.mapped_column(sa.String(10), nullable=True)
    holiday_arrangement: so.Mapped[str] = so.mapped_column(sa.String(10), nullable=True)
    student_activities: so.Mapped[str] = so.mapped_column(sa.String(10), nullable=True)
    other_management: so.Mapped[str] = so.mapped_column(sa.Text, nullable=True)

    # Teacher teaching satisfaction survey fields
    teacher_responsibility: so.Mapped[str] = so.mapped_column(sa.String(10), nullable=True)
    teaching_satisfaction: so.Mapped[str] = so.mapped_column(sa.String(10), nullable=True)
    dissatisfaction_reason: so.Mapped[str] = so.mapped_column(sa.Text, nullable=True)
    other_teaching: so.Mapped[str] = so.mapped_column(sa.Text, nullable=True)

    # Submission information
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey("user.id"), nullable=False)
    submitted_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<SurveyTemplate {self.title}>"


# ===================== Appointment System Models =====================
class TimeSlot(db.Model):
    """Teacher available time slot model"""
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    teacher_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey("user.id"), nullable=False)
    date: so.Mapped[date] = so.mapped_column(sa.Date, nullable=False)
    time_slot: so.Mapped[str] = so.mapped_column(sa.String(20), nullable=False)
    is_booked: so.Mapped[bool] = so.mapped_column(sa.Boolean, default=False, nullable=False)
    created_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    teacher: so.Mapped["User"] = so.relationship("User", foreign_keys=[teacher_id])
    appointment: so.Mapped["Appointment"] = so.relationship(
        back_populates="time_slot", uselist=False
    )

    def __repr__(self):
        return f'<TimeSlot {self.date} {self.time_slot}>'


class Appointment(db.Model):
    """Appointment record model"""
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    student_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey("user.id"), nullable=False)
    teacher_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey("user.id"), nullable=False)
    time_slot_id: so.Mapped[int] = so.mapped_column(
        sa.ForeignKey("time_slot.id"), nullable=False, unique=True
    )
    appointment_type: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=False)
    description: so.Mapped[str] = so.mapped_column(sa.Text, nullable=True)
    status: so.Mapped[str] = so.mapped_column(sa.String(20), default="pending", nullable=False)
    created_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    student: so.Mapped["User"] = so.relationship("User", foreign_keys=[student_id])
    teacher: so.Mapped["User"] = so.relationship("User", foreign_keys=[teacher_id])
    time_slot: so.Mapped["TimeSlot"] = so.relationship(back_populates="appointment")

    def __repr__(self):
        return f'<Appointment {self.id} - {self.status}>'
# ===================== End of Appointment System =====================

# Message read status (student view tracking)
class MessageRead(db.Model):
    __tablename__ = "message_read"

    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey("user.id"), nullable=False)
    message_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey("support_message.id"), nullable=False)
    read_at: so.Mapped[datetime] = so.mapped_column(sa.DateTime, default=lambda: datetime.now(timezone.utc))

    # One user can only read one message once
    __table_args__ = (
        sa.UniqueConstraint('user_id', 'message_id', name='_user_message_uc'),
    )

    def __repr__(self):
        return f"<MessageRead user={self.user_id} message={self.message_id}>"


class UploadFile(db.Model):
    __tablename__ = "upload_file"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)

    # link with message
    message_id = db.Column(db.Integer, db.ForeignKey("support_message.id", ondelete="CASCADE"))
    message = db.relationship("SupportMessage", backref=db.backref("files", cascade="all, delete-orphan"))

    # who upload file
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    message: so.Mapped["SupportMessage"] = so.relationship(back_populates="files")

    def __repr__(self):
        return f"<File {self.filename}>"