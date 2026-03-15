from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, IntegerField, TextAreaField, SelectField, RadioField, SelectMultipleField
from wtforms.validators import DataRequired, Length, Email, NumberRange
from wtforms.widgets import ListWidget, CheckboxInput
from flask_wtf.file import FileField, FileAllowed


# Message submit form
class SupportMessageForm(FlaskForm):

    course_name = StringField(
        "Course Name",
        validators=[
            DataRequired(message="Course name is required"),
            Length(max=256, message="Course name cannot exceed 256 characters")
        ]
    )

    message_title = StringField(
        "Message Title",
        validators=[
            DataRequired(message="Message title is required"),
            Length(max=256, message="Title cannot exceed 256 characters")
        ]
    )


    message_content = TextAreaField(
        "Message Content",
        validators=[
            DataRequired(message="Message content is required"),
            Length(max=500, message="Content cannot exceed 500 characters")
        ]
    )

    # Priority（1-10，default=5）
    priority = IntegerField(
        "Priority (1-10)",
        validators=[
            DataRequired(message="Priority is required"),
            NumberRange(min=1, max=10, message="Priority must be between 1 and 10")
        ],
        default=5
    )

    teacher_email = StringField(
        "Teacher Email",
        validators=[
            DataRequired(message="Teacher email is required"),
            Email(message="Please enter a valid email address")
        ]
    )

    # Publish date（default=today）
    publish_date = DateField(
        "Publish Date",
        format="%Y-%m-%d",
        default=date.today,
        validators=[DataRequired(message="Publish date is required")]
    )

    # Deadline（default=today）
    deadline = DateField(
        "Deadline",
        format="%Y-%m-%d",
        default=date.today,
        validators=[DataRequired(message="Deadline is required")]
    )

    submit = SubmitField("Submit Support Message")


class TeacherUpload(FlaskForm):

    teacher_name = StringField(
        "Your Full Name",
        validators=[DataRequired()]
    )


    course_name = StringField(
        "Course Name",
        validators=[DataRequired()]
    )


    remark = TextAreaField(
        "Remark (optional)",
        validators=[Length(max=150)]
    )


    file = FileField(
        "Upload File (PDF, DOCX, ZIP, JPG, PNG)",
        validators=[
            DataRequired(),
            FileAllowed(['pdf', 'docx', 'doc', 'jpg', 'png', 'zip', 'txt'], "Only documents allowed")
        ]
    )


    submit = SubmitField("Upload File")