from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, IntegerField, TextAreaField, SelectField, RadioField, \
    SelectMultipleField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length, Email, NumberRange, EqualTo, ValidationError
from wtforms.widgets import ListWidget, CheckboxInput
from flask_wtf.file import FileField, FileAllowed


# Support Message Submission Form (Core business form)
# Support Message Submission Form (Simplified)
class SupportMessageForm(FlaskForm):
    subject = StringField(
        "Subject",
        validators=[
            DataRequired(message="Subject is required"),
            Length(max=256, message="Subject cannot exceed 256 characters")
        ]
    )

    message_content = TextAreaField(
        "Message Content",
        validators=[
            DataRequired(message="Content is required"),
            Length(max=500, message="Content cannot exceed 500 characters")
        ]
    )

    # Urgency level (only two options)
    urgency = SelectField(
        "Urgency",
        choices=[
            ("urgent", "Urgent"),
            ("non-urgent", "Non-urgent")
        ],
        validators=[DataRequired(message="Please select urgency level")]
    )
    #files upload
    files = FileField("Attach files (multiple)", render_kw={"multiple": True})

    submit = SubmitField("Submit Message")


# Teacher File Upload Form
class TeacherUpload(FlaskForm):
    teacher_name = StringField(
        "Your Full Name",
        validators=[DataRequired()]
    )

    subject = StringField(
        "subject",
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


# ====================== [Modified] Student Survey Forms ======================
class SurveyBasicInfoForm(FlaskForm):
    """Grade and Major Information Form"""
    grade = SelectField(
        "Grade",
        choices=[
            ("", "Please select your grade"),
            ("Freshman", "Freshman"),
            ("Sophomore", "Sophomore"),
            ("Junior", "Junior"),
            ("Senior", "Senior"),
            ("Graduate", "Graduate")
        ],
        validators=[DataRequired(message="Please select your grade")]
    )

    major = StringField(
        "Major",
        validators=[
            DataRequired(message="Please enter your major"),
            Length(max=100, message="Major name cannot exceed 100 characters")
        ],
        render_kw={"placeholder": "Enter your major"}
    )

    submit = SubmitField("Confirm")


class SurveyTypeForm(FlaskForm):
    """Survey Type Selection Form"""
    survey_type = SelectField(
        "Please select survey type",
        choices=[
            ("", "Please select survey type"),
            ("learning", "Learning Situation Survey"),
            ("management", "School Management Satisfaction Survey"),
            ("teaching", "Teacher Teaching Satisfaction Survey")
        ],
        validators=[DataRequired(message="Please select survey type")]
    )

    submit = SubmitField("Start Survey")


class LearningSurveyForm(FlaskForm):
    """Learning Situation Survey Form"""
    course_schedule = SelectField(
        "Course Schedule Satisfaction",
        choices=[
            ("", "Please select satisfaction level"),
            ("5", "Very Satisfied"),
            ("4", "Satisfied"),
            ("3", "Average"),
            ("2", "Dissatisfied"),
            ("1", "Very Dissatisfied")
        ],
        validators=[DataRequired(message="Please select course schedule satisfaction")]
    )

    course_quality = SelectField(
        "Course Quality",
        choices=[
            ("", "Please select course quality evaluation"),
            ("5", "Excellent"),
            ("4", "Good"),
            ("3", "Average"),
            ("2", "Poor"),
            ("1", "Very Poor")
        ],
        validators=[DataRequired(message="Please select course quality evaluation")]
    )

    knowledge_mastery = SelectField(
        "Knowledge Mastery Level",
        choices=[
            ("", "Please select mastery level"),
            ("5", "Completely Mastered"),
            ("4", "Mostly Mastered"),
            ("3", "Partially Mastered"),
            ("2", "Insufficient Mastery"),
            ("1", "Not Mastered")
        ],
        validators=[DataRequired(message="Please select knowledge mastery level")]
    )

    other_learning = TextAreaField(
        "Additional Comments (Optional)",
        validators=[Length(max=500, message="Additional comments cannot exceed 500 characters")],
        render_kw={"rows": 4, "placeholder": "Enter other comments or suggestions about learning situation..."}
    )

    submit = SubmitField("Submit")


class ManagementSurveyForm(FlaskForm):
    """School Management Satisfaction Survey Form"""
    campus_cleanliness = SelectField(
        "Campus Cleanliness",
        choices=[
            ("", "Please select satisfaction level"),
            ("5", "Very Clean"),
            ("4", "Clean"),
            ("3", "Average"),
            ("2", "Not Clean"),
            ("1", "Very Unclean")
        ],
        validators=[DataRequired(message="Please select campus cleanliness evaluation")]
    )

    cafeteria = SelectField(
        "Cafeteria Food and Environment",
        choices=[
            ("", "Please select satisfaction level"),
            ("5", "Very Satisfied"),
            ("4", "Satisfied"),
            ("3", "Average"),
            ("2", "Dissatisfied"),
            ("1", "Very Dissatisfied")
        ],
        validators=[DataRequired(message="Please select cafeteria satisfaction")]
    )

    holiday_arrangement = SelectField(
        "Holiday Arrangement",
        choices=[
            ("", "Please select satisfaction level"),
            ("5", "Very Reasonable"),
            ("4", "Reasonable"),
            ("3", "Average"),
            ("2", "Unreasonable"),
            ("1", "Very Unreasonable")
        ],
        validators=[DataRequired(message="Please select holiday arrangement satisfaction")]
    )

    student_activities = SelectField(
        "Student Activities Richness",
        choices=[
            ("", "Please select satisfaction level"),
            ("5", "Very Rich"),
            ("4", "Rich"),
            ("3", "Average"),
            ("2", "Insufficient"),
            ("1", "Very Insufficient")
        ],
        validators=[DataRequired(message="Please select student activities richness evaluation")]
    )

    other_management = TextAreaField(
        "Additional Comments (Optional)",
        validators=[Length(max=500, message="Additional comments cannot exceed 500 characters")],
        render_kw={"rows": 4, "placeholder": "Enter other comments or suggestions about school management..."}
    )

    submit = SubmitField("Submit")


class TeachingSurveyForm(FlaskForm):
    """Teacher Teaching Satisfaction Survey Form"""
    teacher_responsibility = RadioField(
        "Is the teacher responsible?",
        choices=[
            ("yes", "Yes"),
            ("no", "No")
        ],
        validators=[DataRequired(message="Please select if the teacher is responsible")]
    )

    teaching_satisfaction = RadioField(
        "Are you satisfied with the teaching?",
        choices=[
            ("yes", "Yes"),
            ("no", "No")
        ],
        validators=[DataRequired(message="Please select if you are satisfied with the teaching")]
    )

    # Only show when not satisfied
    dissatisfaction_reason = TextAreaField(
        "Reasons for dissatisfaction (Please fill if not satisfied)",
        validators=[Length(max=500, message="Comments cannot exceed 500 characters")],
        render_kw={"rows": 4, "placeholder": "Please specify the reasons for dissatisfaction with teaching..."}
    )

    other_teaching = TextAreaField(
        "Other Comments (Optional)",
        validators=[Length(max=500, message="Additional comments cannot exceed 500 characters")],
        render_kw={"rows": 4, "placeholder": "Enter other comments or suggestions about teaching..."}
    )

    submit = SubmitField("Submit")


# Registration
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    school_id = StringField('School ID', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

    role = SelectField(
        "Role",
        choices=[("student", "Student"), ("teacher", "Teacher")],
        validators=[DataRequired()]
    )
    teacher_type = SelectField(
        "Teacher Type",
        choices=[
            ("", "Select Teacher Type"),
            ("lecturer", "Lecturer"),
            ("wellbeing_adviser", "Wellbeing Adviser"),
            ("careers_adviser", "Careers Adviser")
        ],
        validators=[]
    )

    submit = SubmitField('Register')

    def validate_teacher_type(self, field):
        if self.role.data == "teacher" and not field.data:
            raise ValidationError("You must select a teacher type")

    def validate_school_id(self, field):
        # Upper Case
        sid = field.data.strip().upper()

        # student
        if self.role.data == "student":
            if not sid.startswith("S"):
                raise ValidationError("Student ID must start with 'S' → example：S2026001")

        # teacher
        if self.role.data == "teacher":
            if not sid.startswith("T"):
                raise ValidationError("Teacher ID must start with 'T' → example：T2026001")


# Login
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

# ====================== [new]teacher adapt survey ======================
class SurveyTemplateForm(FlaskForm):
    title = StringField("Survey Title", validators=[DataRequired()])
    questions = TextAreaField("Survey Questions (one question per line)", validators=[DataRequired()])
    submit = SubmitField("Save Survey")


# ====================== Appointment Form ======================
class AppointmentForm(FlaskForm):
    """Student Appointment Form"""
    appointment_type = SelectField(
        "Appointment Type",
        choices=[
            ("", "Please select appointment type"),
            ("lecturer", "Student Tutoring Appointment"),
            ("wellbeing_adviser", "Student Counseling Appointment"),
            ("careers_adviser", "Career Guidance Appointment"),
        ],
        validators=[DataRequired(message="Please select appointment type")]
    )
    teacher_type = SelectField(
        "Select Teacher",
        choices=[],
        validators=[DataRequired(message="Please select teacher")],
        coerce=int
    )
    date = DateField(
        "Appointment Date",
        format="%Y-%m-%d",
        validators=[DataRequired(message="Please select date")]
    )
    time_slot_id = SelectField(
        "Time Slot",
        choices=[],
        validators=[DataRequired(message="Please select time slot")],
        coerce=int
    )
    description = TextAreaField(
        "Description / Requirements",
        validators=[Length(max=500, message="Description cannot exceed 500 characters")]
    )
    submit = SubmitField("Submit Appointment")


class TimeSlotForm(FlaskForm):
    """Teacher Time Slot Form"""
    date = DateField(
        "Date",
        format="%Y-%m-%d",
        validators=[DataRequired(message="Please select a date")]
    )
    time_slots = SelectMultipleField(
        "Available Time Slots",
        choices=[
            ("09:00-10:00", "09:00-10:00"),
            ("10:00-11:00", "10:00-11:00"),
            ("11:00-12:00", "11:00-12:00"),
            ("14:00-15:00", "14:00-15:00"),
            ("15:00-16:00", "15:00-16:00"),
            ("16:00-17:00", "16:00-17:00")
        ],
        validators=[DataRequired(message="Please select at least one time slot")],
        widget=ListWidget(prefix_label=False),
        option_widget=CheckboxInput()
    )
    submit = SubmitField("Add Time Slots")
# ====================== End of Appointment Form ======================