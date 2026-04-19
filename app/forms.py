from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, IntegerField, TextAreaField, SelectField, RadioField, \
    SelectMultipleField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length, Email, NumberRange, EqualTo, ValidationError
from wtforms.widgets import ListWidget, CheckboxInput
from flask_wtf.file import FileField, FileAllowed


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
        #Upper Case
        sid = field.data.strip().upper()

        #student
        if self.role.data == "student":
            if not sid.startswith("S"):
                raise ValidationError("Student ID must start with 'S' → example：S2026001")

        #teacher
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
    """学生预约表单"""
    appointment_type = SelectField(
        "预约类型",
        choices=[
            ("", "请选择预约类型"),
            ("lecturer", "学生辅导课程预约"),
            ("wellbeing_adviser", "学生心理咨询预约"),
            ("careers_adviser", "就业指导服务预约"),
            ("academic_consultation", "学生学业问题咨询预约")
        ],
        validators=[DataRequired(message="请选择预约类型")]
    )
    teacher_type = SelectField(
        "选择老师",
        choices=[],
        validators=[DataRequired(message="请选择老师")],
        coerce=int
    )
    date = DateField(
        "预约日期",
        format="%Y-%m-%d",
        validators=[DataRequired(message="请选择日期")]
    )
    time_slot_id = SelectField(
        "时间段",
        choices=[],
        validators=[DataRequired(message="请选择时间段")],
        coerce=int
    )
    description = TextAreaField(
        "问题描述 / 需求说明",
        validators=[Length(max=500, message="描述不能超过500字符")]
    )
    submit = SubmitField("提交预约申请")


class TimeSlotForm(FlaskForm):
    """老师设置可预约时间段表单"""
    date = DateField(
        "日期",
        format="%Y-%m-%d",
        validators=[DataRequired(message="请选择日期")]
    )
    time_slots = SelectMultipleField(
        "可用时间段",
        choices=[
            ("09:00-10:00", "09:00-10:00"),
            ("10:00-11:00", "10:00-11:00"),
            ("11:00-12:00", "11:00-12:00"),
            ("14:00-15:00", "14:00-15:00"),
            ("15:00-16:00", "15:00-16:00"),
            ("16:00-17:00", "16:00-17:00")
        ],
        validators=[DataRequired(message="请至少选择一个时间段")],
        widget=ListWidget(prefix_label=False),
        option_widget=CheckboxInput()
    )
    submit = SubmitField("添加时间段")
# ====================== End of Appointment Form ======================