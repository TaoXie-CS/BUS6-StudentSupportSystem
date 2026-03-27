from datetime import date, datetime
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, IntegerField, TextAreaField, SelectField, RadioField, \
    SelectMultipleField, PasswordField, BooleanField, DateTimeField, FloatField
from wtforms.validators import DataRequired, Length, Email, NumberRange, EqualTo, Optional
from wtforms.widgets import ListWidget, CheckboxInput
from flask_wtf.file import FileField, FileAllowed
from app.models import UserRole, ServiceType, AppointmentStatus

# Support Message Submission Form (Core business form)
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

    # Priority level (1-10, default value = 5)
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

    # Publish date (default value = current date)
    publish_date = DateField(
        "Publish Date",
        format="%Y-%m-%d",
        default=date.today,
        validators=[DataRequired(message="Publish date is required")]
    )

    # Deadline date (default value = current date)
    deadline = DateField(
        "Deadline",
        format="%Y-%m-%d",
        default=date.today,
        validators=[DataRequired(message="Deadline is required")]
    )

    submit = SubmitField("Submit Support Message")


# Teacher File Upload Form
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


class SurveyForm(FlaskForm):
    # Grade selection dropdown (consistent with existing field naming/validation style)
    grade = SelectField(
        "Your Grade",
        choices=[
            ("", "Please select your grade"),
            ("Freshman", "Freshman"),
            ("Sophomore", "Sophomore"),
            ("Junior", "Junior"),
            ("Senior", "Senior"),
            ("Graduate", "Graduate")
        ],
        validators=[
            DataRequired(message="Grade is required")
        ]
    )

    # Gender selection (radio buttons)
    gender = RadioField(
        "Your Gender",
        choices=[("Male", "Male"), ("Female", "Female")],
        validators=[
            DataRequired(message="Gender is required")
        ]
    )

    # Teaching satisfaction rating dropdown
    teaching_quality = SelectField(
        "Teaching Satisfaction Rating",
        choices=[
            ("", "Please rate teaching quality"),
            ("5", "5 - Very Satisfied"),
            ("4", "4 - Satisfied"),
            ("3", "3 - Average"),
            ("2", "2 - Dissatisfied"),
            ("1", "1 - Very Dissatisfied")
        ],
        validators=[
            DataRequired(message="Teaching satisfaction rating is required")
        ]
    )

    # ====================== 【canteen satisfaction】 ======================
    canteen_quality = SelectField(
        "Canteen Satisfaction Rating",
        choices=[
            ("", "Please rate canteen quality"),
            ("5", "5 - Very Satisfied"),
            ("4", "4 - Satisfied"),
            ("3", "3 - Average"),
            ("2", "2 - Dissatisfied"),
            ("1", "1 - Very Dissatisfied")
        ],
        validators=[
            DataRequired(message="Canteen satisfaction rating is required")
        ]
    )

    # ====================== 【environment】 ======================
    campus_quality = SelectField(
        "Campus Environment Satisfaction Rating",
        choices=[
            ("", "Please rate campus environment"),
            ("5", "5 - Very Satisfied"),
            ("4", "4 - Satisfied"),
            ("3", "3 - Average"),
            ("2", "2 - Dissatisfied"),
            ("1", "1 - Very Dissatisfied")
        ],
        validators=[
            DataRequired(message="Campus environment satisfaction rating is required")
        ]
    )

    # Additional feedback (optional, consistent with TeacherUpload's remark style)
    feedback = TextAreaField(
        "Additional Feedback (optional)",
        validators=[
            Length(max=1000, message="Feedback cannot exceed 1000 characters")
        ],
        render_kw={"placeholder": "Enter your suggestions or comments here"}
    )

    # Submit button (consistent naming style with existing buttons)
    submit = SubmitField("Submit Survey")


# Registration
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

    role = SelectField(
        "Role",
        choices=[("student", "Student"), ("teacher", "Teacher")],
        validators=[DataRequired()]
    )

    submit = SubmitField('Register')


# Login
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class UserRegisterForm(FlaskForm):
    """User Registration Form"""
    user_id = StringField("Custom User ID", validators=[DataRequired(), Length(max=50)])
    name = StringField("Full Name", validators=[DataRequired(), Length(max=100)])
    role = SelectField(
        "User Role",
        validators=[DataRequired()],
        choices=[(role.value, role.value) for role in UserRole]
    )
    contact_info = StringField("Contact Info (Phone/Email)", validators=[Optional(), Length(max=200)])
    submit = SubmitField("Register")


class HomeworkPublishForm(FlaskForm):
    """Form for Teachers to Publish Homework"""
    title = StringField("Homework Title", validators=[DataRequired(), Length(max=256)])
    content = TextAreaField("Homework Content", validators=[DataRequired()])
    deadline = DateTimeField(
        "Deadline (YYYY-MM-DD HH:MM)",
        format="%Y-%m-%d %H:%M",
        validators=[DataRequired()],
        default=datetime.now
    )
    submit = SubmitField("Publish Homework")


class HomeworkSubmitForm(FlaskForm):
    """Form for Students to Submit Homework"""
    homework_id = SelectField("Select Homework", validators=[DataRequired()], coerce=int)
    submit = SubmitField("Submit Homework")


class HomeworkGradeForm(FlaskForm):
    """Form for Teachers to Grade Homework"""
    grade = FloatField("Grade", validators=[DataRequired(), NumberRange(min=0, max=100)])
    comment = TextAreaField("Comment", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Submit Grade")


class AppointmentForm(FlaskForm):
    """Form for Students to Book Services"""
    service_type = SelectField(
        "Service Type",
        validators=[DataRequired()],
        choices=[(type.value, type.value) for type in ServiceType]
    )
    advisor_id = SelectField("Select Advisor", validators=[DataRequired()], coerce=int)
    appointment_time = DateTimeField(
        "Appointment Time (YYYY-MM-DD HH:MM)",
        format="%Y-%m-%d %H:%M",
        validators=[DataRequired()]
    )
    submit = SubmitField("Submit Appointment")


class AppointmentStatusForm(FlaskForm):
    """Form for Advisors to Confirm/Reject Appointments"""
    status = SelectField(
        "Appointment Status",
        validators=[DataRequired()],
        choices=[(status.value, status.value) for status in AppointmentStatus]
    )
    submit = SubmitField("Update Status")


class AppointmentFeedbackForm(FlaskForm):
    """Form for Students to Provide Service Feedback"""
    rating = IntegerField("Rating (1-5)", validators=[DataRequired(), NumberRange(min=1, max=5)])
    comment = TextAreaField("Comment", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Submit Feedback")
