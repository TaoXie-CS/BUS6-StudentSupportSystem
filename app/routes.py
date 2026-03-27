import os
from datetime import datetime

from flask import render_template, redirect, url_for, flash, request, current_app, json
from werkzeug.utils import secure_filename, send_from_directory

from app import app
from app import db
from app.models import SupportMessage, SurveyResponse, User
from app.forms import SupportMessageForm, TeacherUpload, SurveyForm
from sqlalchemy import func, cast, Float
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_user, current_user, logout_user, login_required
from app.models import (
    SupportMessage, User, SurveyResponse, Homework, Appointment,
    UserRole, ServiceType, AppointmentStatus
)
from app.forms import (
    SupportMessageForm, TeacherUpload, SurveyForm, RegistrationForm, LoginForm,
    UserRegisterForm, HomeworkPublishForm, HomeworkSubmitForm, HomeworkGradeForm,
    AppointmentForm, AppointmentStatusForm, AppointmentFeedbackForm
)


# Register
@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


# Login
@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            return redirect(url_for('index'))
        flash("Login failed")
    return render_template('login.html', form=form)


# Logout
@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('login'))

# Extend user registration (role system)
@app.route('/user/register', methods=['GET', 'POST'])
@login_required
def user_register():
    # Only administrators or teachers can register users
    if current_user.role not in [UserRole.ADMIN.value, UserRole.TEACHER.value]:
        flash("Only administrators can register new users!", "danger")
        return redirect(url_for('index'))
    form = UserRegisterForm()
    if form.validate_on_submit():
        try:
            # Check if teacher is trying to register a non-student role
            if current_user.role == UserRole.TEACHER.value and form.role.data not in [UserRole.UNDERGRADUATE.value, UserRole.POSTGRADUATE.value, UserRole.INTERNATIONAL.value]:
                flash("Teachers can only register student users!", "danger")
                return redirect(url_for('user_register'))
            
            if User.query.filter_by(user_id=form.user_id.data).first():
                flash("User ID already exists!", "danger")
                return redirect(url_for('user_register'))
            user = User(
                user_id=form.user_id.data,
                name=form.name.data,
                role=form.role.data,
                contact_info=form.contact_info.data,
                username=form.user_id.data,  # Compatible with basic user models
                email=f"{form.user_id.data}@example.com"  # Temporary email, which can be modified later
            )
            user.set_password("123456")  # Default password; it is recommended to enforce a change.
            db.session.add(user)
            db.session.commit()
            flash(f"User {form.name.data} registered successfully!", "success")
            return redirect(url_for('user_register'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f"Error registering user: {str(e)}", "danger")
    return render_template('user_register.html', form=form, UserRole=UserRole)

# Home page: submit and display all messages
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = SupportMessageForm()

    if form.validate_on_submit():
        # Only teachers could create message
        if current_user.role != UserRole.TEACHER.value:
            flash("Only teachers can post messages", "danger")
            return redirect(url_for('index'))
        try:
            # Create a support message record
            support_msg = SupportMessage(
                user_id=current_user.id,
                course_name=form.course_name.data.strip(),
                message_title=form.message_title.data.strip(),
                message_content=form.message_content.data.strip(),
                priority=form.priority.data,
                teacher_email=form.teacher_email.data.strip().lower(),
                publish_date=form.publish_date.data,
                deadline=form.deadline.data
            )

            db.session.add(support_msg)
            db.session.commit()
            flash(f"Support message '{form.message_title.data}' added successfully!", "success")
            return redirect(url_for('index'))

        except SQLAlchemyError as e:
            db.session.rollback()  # Rollback transaction on error
            flash(f"Error adding message: {str(e)}", "danger")

    # ========== Added: Query Survey statistics (pass to homepage template) ==========
    survey_total = SurveyResponse.query.count()  # Total survey submissions
    survey_avg = None
    try:
        # Fixed: Explicitly convert string to Float (replace original cast method)
        avg_quality = db.session.query(
            func.avg(cast(SurveyResponse.teaching_quality, Float))
        ).scalar()
        survey_avg = round(avg_quality, 1) if avg_quality else 0
    except:
        survey_avg = 0
    # ========== End of addition ==========

    # Display all messages in descending order of publication date
    support_messages = SupportMessage.query.order_by(SupportMessage.publish_date.desc()).all()

    # ========== Modified: Pass survey_total/survey_avg to template ==========
    return render_template(
        'index.html',
        current_user=current_user,
        form=form,
        student_infos=support_messages,
        survey_total=survey_total,  # Added
        survey_avg=survey_avg,  # Added
        UserRole=UserRole  # Added to access UserRole enum in templates
    )


# List page: Display all messages in descending order of priority
@app.route('/listing', methods=['GET', 'POST'])
@login_required
def listing_messages():
    # In descending order of priority (with high priority first)
    messages = SupportMessage.query.order_by(SupportMessage.priority.desc()).all()
    print("Number of messages retrieved：", len(messages))
    print("Message details：", messages)
    return render_template('listing.html', students=messages, UserRole=UserRole)


# Search page: Search for messages by teacher email
@app.route('/searching', methods=['GET', 'POST'])
@login_required
def search_messages():
    email = request.args.get("email", "").strip().lower()
    course_name = request.args.get("course_name", "").strip().lower()
    message_title = request.args.get("message_title", "").strip().lower()
    query = SupportMessage.query

    # Fuzzy search conditions
    if email:
        query = query.filter(SupportMessage.teacher_email.ilike(f"%{email}%"))
    if course_name:
        query = query.filter(SupportMessage.course_name.ilike(f"%{course_name}%"))
    if message_title:
        query = query.filter(SupportMessage.message_title.ilike(f"%{message_title}%"))

    results = query.order_by(SupportMessage.priority.desc()).all()

    # Filter high-priority messages (≥8)
    high_priority = query.filter(SupportMessage.priority >= 8).all()

    return render_template(
        'searching.html',
        results=results,
        high=high_priority,
        email=email,
        course_name=course_name,
        message_title=message_title,
        UserRole=UserRole
    )


# Advanced search: by priority/ranking/average score (priority)
@app.route('/more_searching', methods=['GET', 'POST'])
@login_required
def more_search():
    query = SupportMessage.query
    # Filter by priority (high/medium/low)
    priority_level = request.args.get("priority", "")

    sort_by = request.args.get("sort", "")

    # Priority filtering option
    if priority_level == 'high':
        query = query.filter(SupportMessage.priority >= 8)
    elif priority_level == 'medium':
        query = query.filter(SupportMessage.priority.between(4, 7))
    elif priority_level == 'low':
        query = query.filter(SupportMessage.priority <= 3)

    # Sorting option
    if sort_by == "priority_high":
        query = query.order_by(SupportMessage.priority.desc())
    elif sort_by == "priority_low":
        query = query.order_by(SupportMessage.priority.asc())
    elif sort_by == "newest":
        query = query.order_by(SupportMessage.publish_date.desc())

    results = query.all()

    # Calculate average priority
    try:
        avg_priority = db.session.query(func.avg(SupportMessage.priority)).scalar()
        avg_priority_final = round(avg_priority, 0) if avg_priority else 0
    except:
        avg_priority_final = 0

    return render_template(
        'further_search.html',
        results=results,
        status=priority_level,
        order=sort_by,
        results1_final=avg_priority_final,
        UserRole=UserRole
    )


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def file_upload():
    # Only teachers can upload
    if current_user.role != UserRole.TEACHER.value:
        flash("Only teachers can upload files", "danger")
        return redirect(url_for('index'))
    # Create an object for upload form
    form = TeacherUpload()
    filename = None
    # Create path for json file to store upload records
    file_path = os.path.join(
        current_app.root_path, 'static', 'uploads.json')
    try:
        with open(file_path, "r") as file:
            feedback_store = json.load(file)
    except FileNotFoundError:
        feedback_store = []

    # Save upload data to json file
    if form.validate_on_submit():
        upload_data = {
            "teacher_name": form.teacher_name.data,
            "course_name": form.course_name.data,
            "remark": form.remark.data,
            "filename": filename,
            "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        feedback_store.append(upload_data)
        with open(file_path, "w") as file:
            json.dump(feedback_store, file, indent=4)
        # Get uploaded file and save to uploads directory
        file = form.file.data
        # Handle file upload, then prepare for listing files and downloading
        if file:
            filename = secure_filename(
                file.filename)  # secure_filename ensures safe filename storage
            uploaded_folder = current_app.config[
                'UPLOAD_FOLDER']  # Get upload folder from app config
            file.save(os.path.join(uploaded_folder, filename))
            flash("File uploaded successfully!")
            return redirect(url_for("file_upload", filename=filename))
    # List all files (exclude .gitkeep) for downloading
    uploaded_folder = current_app.config['UPLOAD_FOLDER']
    files = [f for f in os.listdir(uploaded_folder) if f != ".gitkeep"]
    # Get filename from request args for download
    filename = request.args.get('filename')
    # Render template for form, uploads and downloads
    return render_template("upload.html", form=form, filename=filename, files=files, UserRole=UserRole)


"""
Clicking the Download link triggers a GET request with the filename in the URL. 
Flask passes this filename to the download_file route, which returns the file to the browser as a download.
"""


@app.route('/uploads/<filename>')
@login_required
def download_file(filename):
    uploaded_folder = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(
        uploaded_folder,
        filename,
        as_attachment=True,
        environ=request.environ)


# Choose a file to download from uploaded files list
@app.route('/downloads')
@login_required
def downloads():
    uploaded_folder = current_app.config['UPLOAD_FOLDER']
    # List all files (exclude .gitkeep) and sort in reverse order
    files = [f for f in os.listdir(uploaded_folder) if f != ".gitkeep"]
    files.sort(reverse=True)
    return render_template('downloads.html', files=files, UserRole=UserRole)


@app.route('/survey', methods=['GET', 'POST'])
@login_required
def survey():
    form = SurveyForm()

    if form.validate_on_submit():
        try:
            # Create survey record
            survey_record = SurveyResponse(
                grade=form.grade.data.strip(),
                gender=form.gender.data.strip(),
                teaching_quality=form.teaching_quality.data.strip(),
                canteen_quality=form.canteen_quality.data.strip(),
                campus_quality=form.campus_quality.data.strip(),
                feedback=form.feedback.data.strip() if form.feedback.data else "",
                user_id=current_user.id
            )

            db.session.add(survey_record)
            db.session.commit()
            flash("Teaching quality survey submitted successfully! Thank you for your feedback.", "success")
            return redirect(url_for('index'))

        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f"Failed to submit survey: {str(e)}", "danger")

    return render_template('survey.html', title='Teaching Quality Survey', form=form, UserRole=UserRole)


@app.route('/survey_results')
@login_required  # 必须登录
def survey_results():
    if current_user.role != UserRole.TEACHER.value:
        flash("You are not allowed to view survey results!", "danger")
        return redirect(url_for('index'))

    survey_responses = SurveyResponse.query.order_by(SurveyResponse.submitted_at.desc()).all()

    try:
        total_surveys = SurveyResponse.query.count()
        grade_stats = db.session.query(
            SurveyResponse.grade,
            func.count(SurveyResponse.id)
        ).group_by(SurveyResponse.grade).all()

        avg_teaching = db.session.query(func.avg(cast(SurveyResponse.teaching_quality, Float))).scalar() or 0
        avg_canteen = db.session.query(func.avg(cast(SurveyResponse.canteen_quality, Float))).scalar() or 0
        avg_campus = db.session.query(func.avg(cast(SurveyResponse.campus_quality, Float))).scalar() or 0

        avg_quality_final = round((avg_teaching + avg_canteen + avg_campus) / 3, 1)

    except Exception as e:
        total_surveys = 0
        grade_stats = []
        avg_quality_final = 0
        flash(f"Error loading survey results: {str(e)}", "danger")

    return render_template(
        'survey_results.html',
        responses=survey_responses,
        total=total_surveys,
        grade_stats=grade_stats,
        avg_quality=avg_quality_final,
        UserRole=UserRole
    )

# Homework Publication (Teachers Only)
@app.route('/homework/publish', methods=['GET', 'POST'])
@login_required
def publish_homework():
    if current_user.role != UserRole.TEACHER.value:
        flash("Only teachers can publish homework!", "danger")
        return redirect(url_for('index'))

    form = HomeworkPublishForm()
    if form.validate_on_submit():
        try:
            homework = Homework(
                title=form.title.data,
                content=form.content.data,
                deadline=form.deadline.data,
                teacher_id=current_user.id
            )
            db.session.add(homework)
            db.session.commit()
            flash(f"Homework '{form.title.data}' published successfully!", "success")
            return redirect(url_for('publish_homework'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f"Error publishing homework: {str(e)}", "danger")
    return render_template('publish_homework.html', form=form, teacher=current_user, UserRole=UserRole)

# Homework Submission (Students Only)
@app.route('/homework/submit', methods=['GET', 'POST'])
@login_required
def submit_homework():
    if current_user.role not in [UserRole.UNDERGRADUATE.value, UserRole.POSTGRADUATE.value, UserRole.INTERNATIONAL.value]:
        flash("Only students can submit homework!", "danger")
        return redirect(url_for('index'))

    form = HomeworkSubmitForm()
    # Load unsubmitted homework
    form.homework_id.choices = [
        (hw.id, hw.title) for hw in Homework.query.filter(
            Homework.teacher_id.isnot(None),
            Homework.submitted_by_id.is_(None)
        ).all()
    ]

    if form.validate_on_submit():
        try:
            homework = Homework.query.get(form.homework_id.data)
            if not homework:
                flash("Homework not found!", "danger")
                return redirect(url_for('submit_homework'))
            homework.submitted_by_id = current_user.id
            homework.submission_time = datetime.now()
            db.session.commit()
            flash(f"Homework '{homework.title}' submitted successfully!", "success")
            return redirect(url_for('submit_homework'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f"Error submitting homework: {str(e)}", "danger")
    return render_template('submit_homework.html', form=form, student=current_user, UserRole=UserRole)

# Homework Grading List (Teachers Only)
@app.route('/homework/grade/list')
@login_required
def grade_homework_list():
    if current_user.role != UserRole.TEACHER.value:
        flash("Only teachers can view homework grading list!", "danger")
        return redirect(url_for('index'))
    
    # Get all homeworks that have been submitted but not yet graded
    homeworks = Homework.query.filter(
        Homework.submitted_by_id.isnot(None),
        Homework.grade.is_(None)
    ).order_by(Homework.submission_time.desc()).all()
    
    # Also get homeworks that have already been graded
    graded_homeworks = Homework.query.filter(
        Homework.submitted_by_id.isnot(None),
        Homework.grade.isnot(None)
    ).order_by(Homework.submission_time.desc()).all()
    
    # Combine both lists
    all_homeworks = homeworks + graded_homeworks
    
    return render_template('grade_homework_list.html', homeworks=all_homeworks, UserRole=UserRole)

# Homework Grading (Teachers Only)
@app.route('/homework/grade/<int:hw_id>', methods=['GET', 'POST'])
@login_required
def grade_homework(hw_id):
    if current_user.role != UserRole.TEACHER.value:
        flash("Only teachers can grade homework!", "danger")
        return redirect(url_for('index'))

    homework = Homework.query.get_or_404(hw_id)
    form = HomeworkGradeForm()
    if form.validate_on_submit():
        try:
            homework.grade = form.grade.data
            homework.comment = form.comment.data
            homework.graded_by_id = current_user.id
            db.session.commit()
            flash(f"Homework '{homework.title}' graded successfully!", "success")
            return redirect(url_for('grade_homework', hw_id=hw_id))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f"Error grading homework: {str(e)}", "danger")
    return render_template('grade_homework.html', form=form, homework=homework, UserRole=UserRole)

# Appointment Submission (Students Only)
@app.route('/appointment/submit', methods=['GET', 'POST'])
@login_required
def submit_appointment():
    if current_user.role not in [UserRole.UNDERGRADUATE.value, UserRole.POSTGRADUATE.value, UserRole.INTERNATIONAL.value]:
        flash("Only students can book appointments!", "danger")
        return redirect(url_for('index'))

    form = AppointmentForm()
    # Load available advisors
    form.advisor_id.choices = [
        (user.id, f"{user.name} ({user.role})") for user in User.query.filter(
            User.role.in_([
                UserRole.TEACHER.value,
                UserRole.PSYCHOLOGIST.value,
                UserRole.CAREER_ADVISOR.value
            ])
        ).all()
    ]

    if form.validate_on_submit():
        try:
            advisor = User.query.get(form.advisor_id.data)
            if not advisor:
                flash("Advisor not found!", "danger")
                return redirect(url_for('submit_appointment'))
            appointment = Appointment(
                student_id=current_user.id,
                advisor_id=advisor.id,
                service_type=form.service_type.data,
                appointment_time=form.appointment_time.data,
                status=AppointmentStatus.PENDING.value
            )
            db.session.add(appointment)
            db.session.commit()
            flash("Appointment submitted successfully! Waiting for confirmation.", "success")
            return redirect(url_for('submit_appointment'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f"Error submitting appointment: {str(e)}", "danger")
    return render_template('submit_appointment.html', form=form, student=current_user, UserRole=UserRole)

# Appointment Status Update (Only for Corresponding Advisors)
@app.route('/appointment/update/<int:app_id>', methods=['GET', 'POST'])
@login_required
def update_appointment(app_id):
    appointment = Appointment.query.get_or_404(app_id)
    if current_user.id != appointment.advisor_id:
        flash("You are not authorized to update this appointment!", "danger")
        return redirect(url_for('index'))

    form = AppointmentStatusForm()
    form.status.data = appointment.status  # Echo the current status
    if form.validate_on_submit():
        try:
            appointment.status = form.status.data
            db.session.commit()
            flash(f"Appointment status updated to {form.status.data}!", "success")
            return redirect(url_for('update_appointment', app_id=app_id))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f"Error updating appointment: {str(e)}", "danger")
    return render_template('update_appointment.html', form=form, appointment=appointment, UserRole=UserRole)

# Appointment Feedback (Only for Corresponding Students)
@app.route('/appointment/feedback/<int:app_id>', methods=['GET', 'POST'])
@login_required
def feedback_appointment(app_id):
    appointment = Appointment.query.get_or_404(app_id)
    if current_user.id != appointment.student_id:
        flash("You are not authorized to submit feedback for this appointment!", "danger")
        return redirect(url_for('index'))

    form = AppointmentFeedbackForm()
    if form.validate_on_submit():
        try:
            appointment.feedback_rating = form.rating.data
            appointment.feedback_comment = form.comment.data
            db.session.commit()
            flash("Feedback submitted successfully!", "success")
            return redirect(url_for('feedback_appointment', app_id=app_id))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f"Error submitting feedback: {str(e)}", "danger")
    return render_template('feedback_appointment.html', form=form, appointment=appointment, UserRole=UserRole)
