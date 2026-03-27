from flask_login import UserMixin

from app import db
import sqlalchemy.orm as so
import sqlalchemy as sa
from datetime import datetime, date, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from enum import Enum

class UserRole(Enum):
    """User Role Enumeration"""
    UNDERGRADUATE = "Undergraduate"
    POSTGRADUATE = "Postgraduate"
    INTERNATIONAL = "International Student"
    TEACHER = "Lecturer"
    COUNSELOR = "Counselor"
    ACADEMIC_ADVISOR = "Academic Advisor"
    ADMIN = "Administrator"
    PSYCHOLOGIST = "Psychologist"
    CAREER_ADVISOR = "Career Advisor"

class ServiceType(Enum):
    """Service Type Enumeration"""
    TUTORING = "Tutoring"
    HOMEWORK = "Homework Submission & Correction"
    PSYCHOLOGY = "Psychological Counseling"
    ACADEMIC = "Academic Consultation"
    CAREER = "Career Guidance"

class AppointmentStatus(Enum):
    """Appointment Status Enumeration"""
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    REJECTED = "Rejected"
    COMPLETED = "Completed"

#User (student / teacher)
class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    user_id: so.Mapped[str] = so.mapped_column(sa.String(50), unique=True, index=True, nullable=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), unique=True, index=True, nullable=False)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), unique=True, index=True, nullable=False)
    name: so.Mapped[str] = so.mapped_column(sa.String(100), nullable=True)
    password_hash: so.Mapped[str] = so.mapped_column(sa.String(256), nullable=False)
    role: so.Mapped[str] = so.mapped_column(sa.String(20), nullable=False, default="student")
    contact_info: so.Mapped[str] = so.mapped_column(sa.String(200), nullable=True)
    messages: so.WriteOnlyMapped[list["SupportMessage"]] = so.relationship(back_populates="author")
    homeworks_published: so.WriteOnlyMapped[list["Homework"]] = so.relationship(back_populates="teacher", foreign_keys="Homework.teacher_id")
    homeworks_submitted: so.WriteOnlyMapped[list["Homework"]] = so.relationship(back_populates="submitted_by", foreign_keys="Homework.submitted_by_id")
    appointments: so.WriteOnlyMapped[list["Appointment"]] = so.relationship(back_populates="student", foreign_keys="Appointment.student_id")
    advisor_appointments: so.WriteOnlyMapped[list["Appointment"]] = so.relationship(back_populates="advisor", foreign_keys="Appointment.advisor_id")

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

    # Course name (indexed for fast search, max length 256, non-nullable)
    course_name: so.Mapped[str] = so.mapped_column(sa.String(256), index=True, nullable=False)

    # Message title (indexed for fast search, max length 256, non-nullable)
    message_title: so.Mapped[str] = so.mapped_column(sa.String(256), index=True, nullable=False)

    # Message content (long text, max length 500, indexed for fast search, non-nullable)
    message_content: so.Mapped[str] = so.mapped_column(sa.String(500), index=True, nullable=False)

    # Priority level (1-10, default value 5, indexed, non-nullable)
    priority: so.Mapped[int] = so.mapped_column(sa.Integer, index=True, nullable=False, default=5)

    # Teacher email address (max length 255, non-unique, indexed for fast search, non-nullable)
    teacher_email: so.Mapped[str] = so.mapped_column(sa.String(255), nullable=False, unique=False, index=True)

    # Publish date (date only, no time component, default to current date, non-nullable)
    publish_date: so.Mapped[date] = so.mapped_column(sa.Date, nullable=False, default=date.today)

    # Deadline date (date only, no time component, default to current date, non-nullable)
    deadline: so.Mapped[date] = so.mapped_column(sa.Date, nullable=False, default=date.today)
    #User ID
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey("user.id"), nullable=False)
    #Author
    author: so.Mapped["User"] = so.relationship(back_populates="messages")

    def __repr__(self):
        # String representation for debugging (consistent format)
        return f'<SupportMessage {self.id} - {self.message_title} ({self.course_name})>'


# ===================== Added: Survey Response Model (Teaching Quality Survey) =====================
class SurveyResponse(db.Model):
    # Primary key (consistent style with SupportMessage)
    id: so.Mapped[int] = so.mapped_column(primary_key=True)

    # Grade level (e.g. Junior 1/Senior 3, max length 20, indexed for fast filtering, non-nullable)
    grade: so.Mapped[str] = so.mapped_column(sa.String(20), index=True, nullable=False)

    # Gender (Male/Female/Other, max length 10, indexed for fast filtering, non-nullable)
    gender: so.Mapped[str] = so.mapped_column(sa.String(10), index=True, nullable=False)

    # Teaching satisfaction rating (1-5, stored as string for flexibility, indexed, non-nullable)
    teaching_quality: so.Mapped[str] = so.mapped_column(sa.String(10), index=True, nullable=False)

    canteen_quality: so.Mapped[str] = so.mapped_column(sa.String(10), index=True, nullable=False)

    campus_quality: so.Mapped[str] = so.mapped_column(sa.String(10), index=True, nullable=False)

    # Additional feedback (optional text, max length 1000, nullable, default empty string)
    feedback: so.Mapped[str] = so.mapped_column(sa.String(1000), nullable=True, default="")

    # Submission timestamp (auto-recorded, timezone-aware datetime, modern best practice, non-nullable)
    submitted_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    # User ID
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey("user.id"), nullable=False)

    def __repr__(self):
        # Consistent __repr__ format with SupportMessage for debugging convenience
        return f'<SurveyResponse {self.id} - {self.grade} ({self.gender})>'
# ===================== End of addition =====================

class Homework(db.Model):
    """Homework Model"""
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    title: so.Mapped[str] = so.mapped_column(sa.String(256), nullable=False)
    content: so.Mapped[str] = so.mapped_column(sa.Text, nullable=False)
    deadline: so.Mapped[datetime] = so.mapped_column(sa.DateTime, nullable=False)

    teacher_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey("user.id"), nullable=False)
    teacher = so.relationship("User", back_populates="homeworks_published", foreign_keys=[teacher_id])

    submitted_by_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey("user.id"), nullable=True)
    submitted_by = so.relationship("User", back_populates="homeworks_submitted", foreign_keys=[submitted_by_id])

    submission_time: so.Mapped[datetime] = so.mapped_column(sa.DateTime, nullable=True)
    grade: so.Mapped[float] = so.mapped_column(sa.Float, nullable=True)
    comment: so.Mapped[str] = so.mapped_column(sa.Text, nullable=True)
    graded_by_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey("user.id"), nullable=True)
    graded_by = so.relationship("User", foreign_keys=[graded_by_id])

    def __repr__(self):
        return f"<Homework {self.title} (Deadline: {self.deadline})>"

class Appointment(db.Model):
    """Appointment Model"""
    id: so.Mapped[int] = so.mapped_column(primary_key=True)

    student_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey("user.id"), nullable=False)
    student = so.relationship("User", back_populates="appointments", foreign_keys=[student_id])

    advisor_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey("user.id"), nullable=False)
    advisor = so.relationship("User", back_populates="advisor_appointments", foreign_keys=[advisor_id])

    service_type: so.Mapped[str] = so.mapped_column(sa.String(50), nullable=False)
    appointment_time: so.Mapped[datetime] = so.mapped_column(sa.DateTime, nullable=False)
    status: so.Mapped[str] = so.mapped_column(sa.String(50), default=AppointmentStatus.PENDING.value, nullable=False)

    feedback_rating: so.Mapped[int] = so.mapped_column(sa.Integer, default=0)
    feedback_comment: so.Mapped[str] = so.mapped_column(sa.Text, nullable=True)

    def __repr__(self):
        return f"<Appointment {self.service_type} ({self.status})>"