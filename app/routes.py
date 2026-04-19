import os
from datetime import datetime

from flask import render_template, redirect, url_for, flash, request, current_app, json, session
from werkzeug.utils import secure_filename, send_from_directory

from app import app
from app import db
from app.models import SupportMessage, NewSurveyResponse
from app.forms import SupportMessageForm, TeacherUpload, SurveyBasicInfoForm, SurveyTypeForm, LearningSurveyForm, \
    ManagementSurveyForm, TeachingSurveyForm
from sqlalchemy import func, cast, Float
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_user, current_user, logout_user, login_required
from app.models import User
from app.forms import RegistrationForm, LoginForm
from app.ai import generate_message_summary
from flask import jsonify


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


# Home page: submit and display all messages
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = SupportMessageForm()

    if form.validate_on_submit():
        # Only teachers could create message
        if current_user.role != "teacher":
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

    # Display all messages in descending order of publication date
    support_messages = SupportMessage.query.order_by(SupportMessage.publish_date.desc()).all()

    ai_summary = ""
    if request.method == "POST":
        context = ""
        for msg in support_messages:
            context += f"Course:{msg.course_name} Title:{msg.message_title} Priority:{msg.priority}\n"

        if not context:
            ai_summary = "⚠️ No messages yet. Please add some first."
        else:
            ai_summary = generate_message_summary(context)
    return render_template(
        'index.html',
        current_user=current_user,
        form=form,
        student_infos=support_messages,
        ai_summary=ai_summary
    )


# List page: Display all messages in descending order of priority
@app.route('/listing', methods=['GET', 'POST'])
@login_required
def listing_messages():
    # In descending order of priority (with high priority first)
    messages = SupportMessage.query.order_by(SupportMessage.priority.desc()).all()
    print("Number of messages retrieved：", len(messages))
    print("Message details：", messages)
    return render_template('listing.html', students=messages)


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
        message_title=message_title
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
        results1_final=avg_priority_final
    )


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def file_upload():
    # Only teachers can upload files
    if current_user.role != "teacher":
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
    # Get filename from request args
    filename = request.args.get('filename')
    # Render template for form, uploads and downloads
    return render_template("upload.html", form=form, filename=filename, files=files)


@app.route('/uploads/<filename>')
@login_required
def download_file(filename):
    uploaded_folder = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(
        uploaded_folder,
        filename,
        as_attachment=True,
        environ=request.environ)


@app.route('/downloads')
@login_required
def downloads():
    uploaded_folder = current_app.config['UPLOAD_FOLDER']
    files = [f for f in os.listdir(uploaded_folder) if f != ".gitkeep"]
    files.sort(reverse=True)
    return render_template('downloads.html', files=files)


# ====================== [Modified] New Survey System Routes ======================
@app.route('/survey', methods=['GET', 'POST'])
@login_required
def survey():
    """Survey main entry - redirect based on user role"""
    if current_user.role != "student":
        # Teachers and other roles cannot fill out surveys
        flash("Only students can fill out surveys", "danger")
        return redirect(url_for('index'))

    # If basic info already exists, go to type selection
    if 'survey_grade' in session and 'survey_major' in session:
        return redirect(url_for('select_survey_type'))

    # Otherwise go to basic info form
    return redirect(url_for('survey_basic_info'))


@app.route('/survey/basic_info', methods=['GET', 'POST'])
@login_required
def survey_basic_info():
    """Fill in grade and major information"""
    if current_user.role != "student":
        flash("Only students can fill out surveys", "danger")
        return redirect(url_for('index'))

    form = SurveyBasicInfoForm()

    if form.validate_on_submit():
        # Save to session
        session['survey_grade'] = form.grade.data
        session['survey_major'] = form.major.data
        flash("Basic information saved, please select survey type", "success")
        return redirect(url_for('select_survey_type'))

    return render_template('survey_basic_info.html', form=form)


@app.route('/survey/select_type', methods=['GET', 'POST'])
@login_required
def select_survey_type():
    """Select survey type"""
    if current_user.role != "student":
        flash("Only students can fill out surveys", "danger")
        return redirect(url_for('index'))

    # Check if basic info exists
    if 'survey_grade' not in session or 'survey_major' not in session:
        flash("Please fill in basic information first", "warning")
        return redirect(url_for('survey_basic_info'))

    form = SurveyTypeForm()

    if form.validate_on_submit():
        survey_type = form.survey_type.data
        session['survey_type'] = survey_type

        # Redirect to corresponding survey page based on type
        if survey_type == 'learning':
            return redirect(url_for('survey_learning'))
        elif survey_type == 'management':
            return redirect(url_for('survey_management'))
        elif survey_type == 'teaching':
            return redirect(url_for('survey_teaching'))

    return render_template('survey_select_type.html', form=form)


@app.route('/survey/learning', methods=['GET', 'POST'])
@login_required
def survey_learning():
    """Learning Situation Survey"""
    if current_user.role != "student":
        flash("Only students can fill out surveys", "danger")
        return redirect(url_for('index'))

    # Check if basic info and type exist
    if 'survey_grade' not in session or 'survey_major' not in session:
        flash("Please fill in basic information first", "warning")
        return redirect(url_for('survey_basic_info'))

    if 'survey_type' not in session or session.get('survey_type') != 'learning':
        flash("Please select survey type first", "warning")
        return redirect(url_for('select_survey_type'))

    form = LearningSurveyForm()

    if form.validate_on_submit():
        try:
            # Create new survey response record
            survey_response = NewSurveyResponse(
                grade=session['survey_grade'],
                major=session['survey_major'],
                survey_type='learning',
                course_schedule=form.course_schedule.data,
                course_quality=form.course_quality.data,
                knowledge_mastery=form.knowledge_mastery.data,
                other_learning=form.other_learning.data,
                user_id=current_user.id
            )

            db.session.add(survey_response)
            db.session.commit()

            # Clear session
            session.pop('survey_grade', None)
            session.pop('survey_major', None)
            session.pop('survey_type', None)

            flash("Learning situation survey submitted successfully! Thank you for your feedback.", "success")
            return redirect(url_for('index'))

        except Exception as e:
            db.session.rollback()
            flash(f"Submission failed: {str(e)}", "danger")

    return render_template('survey_learning.html', form=form)


@app.route('/survey/management', methods=['GET', 'POST'])
@login_required
def survey_management():
    """School Management Satisfaction Survey"""
    if current_user.role != "student":
        flash("Only students can fill out surveys", "danger")
        return redirect(url_for('index'))

    # Check if basic info and type exist
    if 'survey_grade' not in session or 'survey_major' not in session:
        flash("Please fill in basic information first", "warning")
        return redirect(url_for('survey_basic_info'))

    if 'survey_type' not in session or session.get('survey_type') != 'management':
        flash("Please select survey type first", "warning")
        return redirect(url_for('select_survey_type'))

    form = ManagementSurveyForm()

    if form.validate_on_submit():
        try:
            # Create new survey response record
            survey_response = NewSurveyResponse(
                grade=session['survey_grade'],
                major=session['survey_major'],
                survey_type='management',
                campus_cleanliness=form.campus_cleanliness.data,
                cafeteria=form.cafeteria.data,
                holiday_arrangement=form.holiday_arrangement.data,
                student_activities=form.student_activities.data,
                other_management=form.other_management.data,
                user_id=current_user.id
            )

            db.session.add(survey_response)
            db.session.commit()

            # Clear session
            session.pop('survey_grade', None)
            session.pop('survey_major', None)
            session.pop('survey_type', None)

            flash("School management satisfaction survey submitted successfully! Thank you for your feedback.",
                  "success")
            return redirect(url_for('index'))

        except Exception as e:
            db.session.rollback()
            flash(f"Submission failed: {str(e)}", "danger")

    return render_template('survey_management.html', form=form)


@app.route('/survey/teaching', methods=['GET', 'POST'])
@login_required
def survey_teaching():
    """Teacher Teaching Satisfaction Survey"""
    if current_user.role != "student":
        flash("Only students can fill out surveys", "danger")
        return redirect(url_for('index'))

    # Check if basic info and type exist
    if 'survey_grade' not in session or 'survey_major' not in session:
        flash("Please fill in basic information first", "warning")
        return redirect(url_for('survey_basic_info'))

    if 'survey_type' not in session or session.get('survey_type') != 'teaching':
        flash("Please select survey type first", "warning")
        return redirect(url_for('select_survey_type'))

    form = TeachingSurveyForm()

    if form.validate_on_submit():
        try:
            # If not satisfied but reason not filled, prompt user
            if form.teaching_satisfaction.data == 'no' and not form.dissatisfaction_reason.data:
                flash("If you are not satisfied with teaching, please fill in the reasons for dissatisfaction",
                      "warning")
                return render_template('survey_teaching.html', form=form)

            # Create new survey response record
            survey_response = NewSurveyResponse(
                grade=session['survey_grade'],
                major=session['survey_major'],
                survey_type='teaching',
                teacher_responsibility=form.teacher_responsibility.data,
                teaching_satisfaction=form.teaching_satisfaction.data,
                dissatisfaction_reason=form.dissatisfaction_reason.data if form.teaching_satisfaction.data == 'no' else None,
                other_teaching=form.other_teaching.data,
                user_id=current_user.id
            )

            db.session.add(survey_response)
            db.session.commit()

            # Clear session
            session.pop('survey_grade', None)
            session.pop('survey_major', None)
            session.pop('survey_type', None)

            flash("Teacher teaching satisfaction survey submitted successfully! Thank you for your feedback.",
                  "success")
            return redirect(url_for('index'))

        except Exception as e:
            db.session.rollback()
            flash(f"Submission failed: {str(e)}", "danger")

    return render_template('survey_teaching.html', form=form)


@app.route('/survey/reset')
@login_required
def reset_survey():
    """Reset survey information, start over"""
    session.pop('survey_grade', None)
    session.pop('survey_major', None)
    session.pop('survey_type', None)
    flash("Survey information reset, please fill in again", "info")
    return redirect(url_for('survey_basic_info'))


@app.route('/survey_results')
@login_required
def survey_results():
    # Survey results are not available to anyone
    flash("Survey results are not available at this time.", "danger")
    return redirect(url_for('index'))

# ====================== End of Modified Survey System ======================