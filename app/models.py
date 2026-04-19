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
    # User ID
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey("user.id"), nullable=False)
    # Author
    author: so.Mapped["User"] = so.relationship(back_populates="messages")

    def __repr__(self):
        # String representation for debugging (consistent format)
        return f'<SupportMessage {self.id} - {self.message_title} ({self.course_name})>'


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
        return f'<NewSurveyResponse {self.id} - {self.survey_type} ({self.grade})>'

# Note: Old SurveyResponse and SurveyTemplate models are kept for backward compatibility
# but are no longer used in the new survey system