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
    #aAuthor
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

    # Additional feedback (optional text, max length 1000, nullable, default empty string)
    feedback: so.Mapped[str] = so.mapped_column(sa.String(1000), nullable=True, default="")

    # Submission timestamp (auto-recorded, timezone-aware datetime, modern best practice, non-nullable)
    submitted_at: so.Mapped[datetime] = so.mapped_column(
        sa.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        # Consistent __repr__ format with SupportMessage for debugging convenience
        return f'<SurveyResponse {self.id} - {self.grade} ({self.gender})>'
# ===================== End of addition =====================