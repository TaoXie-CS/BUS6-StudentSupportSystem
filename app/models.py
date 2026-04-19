from flask_login import UserMixin

from app import db
import sqlalchemy.orm as so
import sqlalchemy as sa
from datetime import datetime, date, timezone
from werkzeug.security import generate_password_hash, check_password_hash

#User (student / teacher)
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
# ====================== [new]teacher adapt survey======================
class SurveyTemplate(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    title: so.Mapped[str] = so.mapped_column(sa.String(200), default="Teaching Quality Survey")
    questions: so.Mapped[str] = so.mapped_column(sa.Text, default="")  # 所有问题
    updated_at: so.Mapped[datetime] = so.mapped_column(sa.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<SurveyTemplate {self.title}>"


# ===================== Appointment System Models =====================
class TimeSlot(db.Model):
    """老师可预约时间段模型"""
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
    """预约记录模型"""
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