import os
from datetime import datetime, date

from flask import render_template, redirect, url_for, flash, request, current_app, json, session
from werkzeug.utils import secure_filename, send_from_directory

from app import app
from app import db
from app.models import SupportMessage, NewSurveyResponse, MessageRead, UploadFile
from app.forms import SupportMessageForm, TeacherUpload, SurveyBasicInfoForm, SurveyTypeForm, LearningSurveyForm, \
    ManagementSurveyForm, TeachingSurveyForm
from app.models import SupportMessage, TimeSlot, Appointment
from app.forms import SupportMessageForm, TeacherUpload, SurveyTemplateForm, AppointmentForm, TimeSlotForm
from sqlalchemy import func, cast, Float
from sqlalchemy.exc import SQLAlchemyError
from flask_login import login_user, current_user, logout_user, login_required
from app.models import User
from app.forms import RegistrationForm, LoginForm
from app.ai import generate_message_summary
from flask import jsonify
import uuid
from flask import send_from_directory

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED = {'pdf', 'docx', 'doc', 'png', 'jpg', 'zip', 'txt'}


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
            role=form.role.data,
            teacher_type=form.teacher_type.data if form.role.data == "teacher" else ""
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

    search = request.args.get('search', '')
    filter_urgency = request.args.get('urgency', '')
    sort = request.args.get('sort', '')

    query = SupportMessage.query
    if current_user.role == "teacher":
        query = query.filter_by(user_id=current_user.id)

    if search:
        query = query.filter(SupportMessage.subject.ilike(f"%{search}%"))
    if filter_urgency:
        query = query.filter(SupportMessage.urgency == filter_urgency)

    if sort == "priority_desc":
        query = query.order_by(SupportMessage.urgency.desc())
    elif sort == "priority_asc":
        query = query.order_by(SupportMessage.urgency.asc())
    else:
        query = query.order_by(SupportMessage.publish_date.desc())

    support_messages = query.all()

    ai_summary = ""
    if request.method == "POST" and current_user.role == "student":

        action = request.form.get("ai_action")

        if action:
            context = ""
            for msg in support_messages:
                content_snippet = msg.message_content[:150] if msg.message_content else ""
                context += f"Subject: {msg.subject} | Info: {content_snippet}\n"

            if context:
                ai_summary = generate_message_summary(context, mode=action)
            else:
                ai_summary = "No messages available to analyze."

    return render_template(
        'index.html',
        current_user=current_user,
        form=form,
        student_infos=support_messages,
        ai_summary=ai_summary,
        search=search,
        urgency=filter_urgency,
        sort=sort
    )

# ------------------------------
# New Message (Teacher Only)
# ------------------------------
@app.route('/new-message', methods=['GET', 'POST'])
@login_required
def new_message():
    if current_user.role != "teacher":
        flash("Only teachers can create messages", "danger")
        return redirect(url_for('index'))

    form = SupportMessageForm()
    if form.validate_on_submit():
        try:
            support_msg = SupportMessage(
                subject=form.subject.data.strip(),
                message_content=form.message_content.data.strip(),
                urgency=form.urgency.data,
                teacher_email=current_user.email,
                teacher_name=current_user.username,
                teacher_school_id=current_user.school_id,
                user_id=current_user.id,
                publish_date=date.today()
            )
            db.session.add(support_msg)
            db.session.flush()

            files = request.files.getlist("files")
            for file in files:
                if file and allowed_file(file.filename):
                    original_filename = secure_filename(file.filename)
                    ext = original_filename.rsplit('.', 1)[1].lower()
                    stored_filename = f"{uuid.uuid4()}.{ext}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], stored_filename))

                    new_file = UploadFile(
                        filename=original_filename,
                        stored_name=stored_filename,
                        message_id=support_msg.id,
                        user_id=current_user.id
                    )
                    db.session.add(new_file)

            db.session.commit()
            flash(f"Message '{form.subject.data}' created successfully!", "success")
            return redirect(url_for('index'))

        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f"Error creating message: {str(e)}", "danger")

    return render_template("new_message.html", form=form)


# List page: Display all messages in descending order of priority
@login_required
def listing_messages():
    # In descending order of priority (with high priority first)
    messages = SupportMessage.query.order_by(SupportMessage.priority.desc()).all()
    print("Number of messages retrieved：", len(messages))
    print("Message details：", messages)
    return render_template('listing.html', students=messages)


# Search page: Search for messages by teacher email
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

# ====================== FILE UPLOAD / DOWNLOAD / DELETE ======================


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED

# file list
@app.route('/files')
@login_required
def files():
    # teacher can see own files
    if current_user.role == "teacher":
        files = UploadFile.query.filter_by(user_id=current_user.id).order_by(UploadFile.upload_time.desc()).all()
    else:
        # student can see all files
        files = UploadFile.query.order_by(UploadFile.upload_time.desc()).all()
    return render_template('files.html', files=files)


# upload file
@app.route('/upload', methods=['GET','POST'])
@login_required
def file_upload():
    if current_user.role != 'teacher':
        flash('Only teachers can upload','danger')
        return redirect(url_for('files'))

    form = TeacherUpload()
    if form.validate_on_submit():
        f = form.file.data
        if f and allowed_file(f.filename):
            orig = secure_filename(f.filename)
            ext = orig.rsplit('.',1)[1].lower()
            stored = f"{uuid.uuid4()}.{ext}"
            f.save(os.path.join(UPLOAD_FOLDER, stored))

            newfile = UploadFile(
                filename=orig,
                stored_name=stored,
                subject=form.subject.data,
                teacher_name=form.teacher_name.data,
                remark=form.remark.data,
                user_id=current_user.id
            )
            db.session.add(newfile)
            db.session.commit()
            flash('Upload success!','success')
            return redirect(url_for('files'))

    return render_template('upload.html', form=form)

# download file
@app.route('/download/<int:file_id>')
@login_required
def download_file(file_id):
    f = UploadFile.query.get_or_404(file_id)
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        f.stored_name,
        as_attachment=True,
        download_name=f.filename
    )


# ====================== [Modified] New Survey System Routes ======================
@app.route('/survey', methods=['GET', 'POST'])
@login_required
def survey():
    """Main survey entry - redirect based on user role"""
    if current_user.role != "student":
        # Teachers and other roles cannot fill out surveys
        flash("Only students can complete surveys", "danger")
        return redirect(url_for('index'))

    # If basic info already exists, go to type selection
    if 'survey_grade' in session and 'survey_major' in session:
        return redirect(url_for('select_survey_type'))

    # Otherwise go to basic info form
    return redirect(url_for('survey_basic_info'))


@app.route('/survey/basic_info', methods=['GET', 'POST'])
@login_required
def survey_basic_info():
    """Enter grade and major information"""
    if current_user.role != "student":
        flash("Only students can complete surveys", "danger")
        return redirect(url_for('index'))

    form = SurveyBasicInfoForm()

    if form.validate_on_submit():
        # Save to session
        session['survey_grade'] = form.grade.data
        session['survey_major'] = form.major.data
        flash("Basic information saved. Please select survey type.", "success")
        return redirect(url_for('select_survey_type'))

    return render_template('survey_basic_info.html', form=form)


@app.route('/survey/select_type', methods=['GET', 'POST'])
@login_required
def select_survey_type():
    """Select survey type"""
    if current_user.role != "student":
        flash("Only students can complete surveys", "danger")
        return redirect(url_for('index'))

    # Check if basic info exists
    if 'survey_grade' not in session or 'survey_major' not in session:
        flash("Please complete basic information first", "warning")
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
    """Learning Status Survey"""
    if current_user.role != "student":
        flash("Only students can complete surveys", "danger")
        return redirect(url_for('index'))

    # Check if basic info and type exist
    if 'survey_grade' not in session or 'survey_major' not in session:
        flash("Please complete basic information first", "warning")
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

            flash("Learning survey submitted successfully! Thank you for your feedback.", "success")
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
        flash("Only students can complete surveys", "danger")
        return redirect(url_for('index'))

    # Check if basic info and type exist
    if 'survey_grade' not in session or 'survey_major' not in session:
        flash("Please complete basic information first", "warning")
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

            flash("School management survey submitted successfully! Thank you for your feedback.",
                  "success")
            return redirect(url_for('index'))

        except Exception as e:
            db.session.rollback()
            flash(f"Submission failed: {str(e)}", "danger")

    return render_template('survey_management.html', form=form)


@app.route('/survey/teaching', methods=['GET', 'POST'])
@login_required
def survey_teaching():
    """Teaching Satisfaction Survey"""
    if current_user.role != "student":
        flash("Only students can complete surveys", "danger")
        return redirect(url_for('index'))

    # Check if basic info and type exist
    if 'survey_grade' not in session or 'survey_major' not in session:
        flash("Please complete basic information first", "warning")
        return redirect(url_for('survey_basic_info'))

    if 'survey_type' not in session or session.get('survey_type') != 'teaching':
        flash("Please select survey type first", "warning")
        return redirect(url_for('select_survey_type'))

    form = TeachingSurveyForm()

    if form.validate_on_submit():
        try:
            # If not satisfied but reason not filled, prompt user
            if form.teaching_satisfaction.data == 'no' and not form.dissatisfaction_reason.data:
                flash("Please provide a reason if you are dissatisfied with teaching", "warning")
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

            flash("Teaching survey submitted successfully! Thank you for your feedback.",
                  "success")
            return redirect(url_for('index'))

        except Exception as e:
            db.session.rollback()
            flash(f"Submission failed: {str(e)}", "danger")

    return render_template('survey_teaching.html', form=form)


@app.route('/survey/reset')
@login_required
def reset_survey():
    """Reset survey progress and start over"""
    session.pop('survey_grade', None)
    session.pop('survey_major', None)
    session.pop('survey_type', None)
    flash("Survey progress reset. Please start over.", "info")
    return redirect(url_for('survey_basic_info'))


@app.route('/survey_results')
@login_required
def survey_results():
    # Survey results are not available to anyone
    flash("Survey results are not available at this time.", "danger")
    return redirect(url_for('index'))

# ====================== End of Modified Survey System ======================
# ====================== Appointment System Routes ======================

@app.route('/appointment', methods=['GET', 'POST'])
@login_required
def appointment():
    """Student appointment homepage"""
    if current_user.role != "student":
        flash("Only students can make appointments", "danger")
        return redirect(url_for('index'))

    form = AppointmentForm()
    return render_template('appointment.html', form=form)


@app.route('/api/teachers/<teacher_type>')
@login_required
def get_teachers(teacher_type):
    """Return teacher list by type"""
    teachers = User.query.filter_by(
        role="teacher",
        teacher_type=teacher_type
    ).all()
    return jsonify([{
        'id': t.id,
        'username': t.username,
        'email': t.email
    } for t in teachers])


@app.route('/api/available_dates/<int:teacher_id>')
@login_required
def get_available_dates(teacher_id):
    """Get dates with available time slots for the teacher"""
    from datetime import date

    # Query dates with available and not fully booked time slots
    available_dates = db.session.query(TimeSlot.date).filter(
        TimeSlot.teacher_id == teacher_id,
        TimeSlot.is_booked == False
    ).distinct().all()

    # Filter out dates where all slots are fully booked
    result = []
    for (date_obj,) in available_dates:
        total_slots = TimeSlot.query.filter_by(
            teacher_id=teacher_id,
            date=date_obj
        ).count()
        booked_slots = TimeSlot.query.filter_by(
            teacher_id=teacher_id,
            date=date_obj,
            is_booked=True
        ).count()
        if total_slots > booked_slots:
            result.append(date_obj.strftime('%Y-%m-%d'))

    return jsonify(result)


@app.route('/api/time_slots/<int:teacher_id>/<date_str>')
@login_required
def get_time_slots(teacher_id, date_str):
    """Get available time slots for a specific date"""
    from datetime import datetime
    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    slots = TimeSlot.query.filter_by(
        teacher_id=teacher_id,
        date=date_obj
    ).order_by(TimeSlot.time_slot).all()

    return jsonify([{
        'id': s.id,
        'time': s.time_slot,
        'is_booked': s.is_booked
    } for s in slots])


@app.route('/appointment/submit', methods=['POST'])
@login_required
def submit_appointment():
    """Submit appointment request"""
    if current_user.role != "student":
        return jsonify({'success': False, 'message': 'Insufficient permissions'})

    data = request.get_json()
    time_slot_id = data.get('time_slot_id')
    description = data.get('description', '')
    appointment_type = data.get('appointment_type')

    # Check if the time slot is already booked
    time_slot = TimeSlot.query.get(time_slot_id)
    if not time_slot or time_slot.is_booked:
        return jsonify({'success': False, 'message': 'This time slot is already taken'})

    # Create appointment record
    appointment = Appointment(
        student_id=current_user.id,
        teacher_id=time_slot.teacher_id,
        time_slot_id=time_slot_id,
        appointment_type=appointment_type,
        description=description,
        status='confirmed'
    )

    # Mark time slot as booked
    time_slot.is_booked = True

    db.session.add(appointment)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Appointment submitted successfully, awaiting teacher confirmation'
    })


@app.route('/my_appointments')
@login_required
def my_appointments():
    """View my appointments"""
    if current_user.role == "teacher":
        appointments = Appointment.query.join(TimeSlot).filter(
            Appointment.teacher_id == current_user.id
        ).order_by(TimeSlot.date.asc(), TimeSlot.time_slot.asc()).all()
    else:
        appointments = Appointment.query.join(TimeSlot).filter(
            Appointment.student_id == current_user.id
        ).order_by(TimeSlot.date.asc(), TimeSlot.time_slot.asc()).all()
    return render_template('my_appointments.html', appointments=appointments)


@app.route('/appointment/<int:appointment_id>/cancel', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    """Cancel an appointment (student only)"""
    appointment = Appointment.query.get_or_404(appointment_id)

    # Permission check: only the student who made the appointment can cancel
    if current_user.id != appointment.student_id:
        flash("Permission denied", "danger")
        return redirect(url_for('index'))

    # Status check: only confirmed appointments can be canceled
    if appointment.status != 'confirmed':
        flash("This appointment cannot be canceled", "warning")
        return redirect(url_for('my_appointments'))

    # Release the time slot
    appointment.time_slot.is_booked = False

    # Delete the appointment record
    db.session.delete(appointment)

    db.session.commit()
    flash("Appointment canceled successfully", "success")
    return redirect(url_for('my_appointments'))


@app.route('/teacher/time_slots', methods=['GET', 'POST'])
@login_required
def manage_time_slots():
    """Teacher manages available time slots"""
    if current_user.role != "teacher":
        flash("Only teachers can manage time slots", "danger")
        return redirect(url_for('index'))

    form = TimeSlotForm()

    if form.validate_on_submit():
        date = form.date.data
        selected_slots = form.time_slots.data

        # Check for existing slots
        existing_slots = TimeSlot.query.filter_by(
            teacher_id=current_user.id,
            date=date
        ).all()
        existing_times = {s.time_slot for s in existing_slots}

        added_count = 0
        for slot_time in selected_slots:
            if slot_time not in existing_times:
                new_slot = TimeSlot(
                    teacher_id=current_user.id,
                    date=date,
                    time_slot=slot_time,
                    is_booked=False
                )
                db.session.add(new_slot)
                added_count += 1

        if added_count > 0:
            db.session.commit()
            flash(f"Successfully added {added_count} time slots", "success")
        else:
            flash("Selected time slots already exist", "info")

        return redirect(url_for('manage_time_slots'))

    my_slots = TimeSlot.query.filter_by(
        teacher_id=current_user.id
    ).order_by(TimeSlot.date.desc(), TimeSlot.time_slot).all()

    return render_template('manage_time_slots.html', form=form, slots=my_slots)
# ====================== End of Appointment Routes ======================

# ------------------------------
# Message Detail (Mark as Read)
# ------------------------------
@app.route('/message/<int:msg_id>')
@login_required
def message_detail(msg_id):
    """View single message and mark as read for students"""
    msg = SupportMessage.query.get_or_404(msg_id)

    # Permission: teacher can only view their own
    if current_user.role == "teacher" and msg.user_id != current_user.id:
        flash("You cannot view this message", "danger")
        return redirect(url_for('index'))

    # Mark as read if student
    if current_user.role == "student":
        exists = MessageRead.query.filter_by(
            user_id=current_user.id,
            message_id=msg_id
        ).first()
        if not exists:
            read_record = MessageRead(
                user_id=current_user.id,
                message_id=msg_id
            )
            db.session.add(read_record)
            db.session.commit()

    return render_template("message_detail.html", message=msg)


# ------------------------------
# Edit Message (Teacher Only)
# ------------------------------
@app.route('/edit/<int:msg_id>', methods=['GET', 'POST'])
@login_required
def message_edit(msg_id):
    msg = SupportMessage.query.get_or_404(msg_id)
    if msg.user_id != current_user.id:
        flash("Permission denied")
        return redirect(url_for('index'))

    form = SupportMessageForm(obj=msg)
    if form.validate_on_submit():
        # 1. update message
        msg.subject = form.subject.data.strip()
        msg.message_content = form.message_content.data.strip()
        msg.urgency = form.urgency.data

        # 2. update new files
        files = request.files.getlist("files")
        for file in files:
            if file and allowed_file(file.filename):
                orig = secure_filename(file.filename)
                ext = orig.rsplit('.',1)[1].lower()
                stored = f"{uuid.uuid4()}.{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], stored))
                new_file = UploadFile(
                    filename=orig,
                    stored_name=stored,
                    message_id=msg.id,
                    user_id=current_user.id
                )
                db.session.add(new_file)

        db.session.commit()
        flash("Message updated successfully, new attachments added")
        return redirect(url_for('index'))

    return render_template("edit_message.html", form=form, message=msg)


# ------------------------------
# Delete Message (Teacher Only)
# ------------------------------
@app.route('/delete/<int:msg_id>')
@login_required
def message_delete(msg_id):
    msg = SupportMessage.query.get_or_404(msg_id)

    if msg.user_id != current_user.id:
        flash("No permission")
        return redirect(url_for('index'))

    # delete attached files
    for f in msg.files:
        path = os.path.join(UPLOAD_FOLDER, f.stored_name)
        if os.path.exists(path):
            os.remove(path)

    # delete message and related files
    db.session.delete(msg)
    db.session.commit()
    flash("Message and all files deleted successfully")
    return redirect(url_for('index'))

# delete single file
@app.route('/delete/file/<int:file_id>')
@login_required
def delete_file_msg(file_id):
    f = UploadFile.query.get_or_404(file_id)
    if f.user_id != current_user.id:
        flash("You can only delete your own files", "danger")
        return redirect(url_for('index'))

    path = os.path.join(app.config['UPLOAD_FOLDER'], f.stored_name)
    if os.path.exists(path):
        os.remove(path)

    db.session.delete(f)
    db.session.commit()
    flash("File deleted successfully", "success")

    return redirect(url_for('message_edit', msg_id=f.message_id))



@app.route('/messages', methods=['GET'])
@login_required
def messages_page():
    search = request.args.get('search', '')
    filter_urgency = request.args.get('urgency', '')
    sort = request.args.get('sort', '')

    query = SupportMessage.query
    if current_user.role == "teacher":
        query = query.filter_by(user_id=current_user.id)

    if search:
        query = query.filter(SupportMessage.subject.ilike(f"%{search}%"))
    if filter_urgency:
        query = query.filter(SupportMessage.urgency == filter_urgency)

    if sort == "priority_desc":
        query = query.order_by(SupportMessage.urgency.desc())
    elif sort == "priority_asc":
        query = query.order_by(SupportMessage.urgency.asc())
    else:
        query = query.order_by(SupportMessage.publish_date.desc())

    support_messages = query.all()

    return render_template(
        'messages.html',
        student_infos=support_messages,
        search=search,
        urgency=filter_urgency,
        sort=sort
    )


@app.route('/ai-assistant', methods=['GET', 'POST'])
@login_required
def ai_assistant_page():
    if current_user.role != "student":
        flash("Only students can use the AI Assistant", "danger")
        return redirect(url_for('index'))

    query = SupportMessage.query
    support_messages = query.all()

    ai_summary = ""
    if request.method == "POST":
        action = request.form.get("ai_action")
        context = ""
        for msg in support_messages:
            content_snippet = msg.message_content[:150] if msg.message_content else ""
            context += f"Subject: {msg.subject} | Info: {content_snippet}\n"

        if context:
            ai_summary = generate_message_summary(context, mode=action)
        else:
            ai_summary = "No messages available to analyze."

    return render_template('ai_assistant.html', ai_summary=ai_summary)


# ====================== Admin Survey Results Routes ======================
@app.route('/admin/survey-results')
@login_required
def admin_survey_results():
    """Admin survey results overview page"""
    if current_user.role != "admin":
        flash("Access denied. Admin only.", "danger")
        return redirect(url_for('index'))

    return render_template('admin_survey_results.html')


@app.route('/admin/survey-results/learning')
@login_required
def admin_survey_results_learning():
    """Learning survey results"""
    if current_user.role != "admin":
        flash("Access denied. Admin only.", "danger")
        return redirect(url_for('index'))

    # Get all learning survey responses
    responses = NewSurveyResponse.query.filter_by(
        survey_type='learning'
    ).all()

    if not responses:
        flash("No learning survey data available.", "info")
        return render_template('admin_survey_learning.html',
                               responses=[],
                               stats={},
                               comments=[])

    # Calculate statistics
    total = len(responses)

    # Map text values to numeric scores (1-5)
    score_mapping = {
        "1": 1, "Very Dissatisfied": 1,
        "2": 2, "Dissatisfied": 2,
        "3": 3, "Average": 3,
        "4": 4, "Satisfied": 4,
        "5": 5, "Very Satisfied": 5,
        "Very Poor": 1, "Poor": 2, "Average": 3, "Good": 4, "Excellent": 5,
        "Not Mastered": 1, "Insufficient Mastery": 2, "Partially Mastered": 3,
        "Mostly Mastered": 4, "Completely Mastered": 5
    }

    # Initialize sums
    course_schedule_sum = 0
    course_quality_sum = 0
    knowledge_mastery_sum = 0
    valid_cs = 0
    valid_cq = 0
    valid_km = 0

    # Collect comments
    comments = []

    for resp in responses:
        # Calculate course schedule score
        if resp.course_schedule and resp.course_schedule in score_mapping:
            course_schedule_sum += score_mapping[resp.course_schedule]
            valid_cs += 1

        # Calculate course quality score
        if resp.course_quality and resp.course_quality in score_mapping:
            course_quality_sum += score_mapping[resp.course_quality]
            valid_cq += 1

        # Calculate knowledge mastery score
        if resp.knowledge_mastery and resp.knowledge_mastery in score_mapping:
            knowledge_mastery_sum += score_mapping[resp.knowledge_mastery]
            valid_km += 1

        # Collect comments
        if resp.other_learning and resp.other_learning.strip():
            user = User.query.get(resp.user_id)
            comments.append({
                'username': user.username if user else 'Unknown',
                'comment': resp.other_learning.strip()
            })

    # Calculate averages
    stats = {
        'total_responses': total,
        'course_schedule_avg': round(course_schedule_sum / valid_cs, 2) if valid_cs > 0 else 0,
        'course_quality_avg': round(course_quality_sum / valid_cq, 2) if valid_cq > 0 else 0,
        'knowledge_mastery_avg': round(knowledge_mastery_sum / valid_km, 2) if valid_km > 0 else 0,
    }

    return render_template('admin_survey_learning.html',
                           responses=responses,
                           stats=stats,
                           comments=comments)


@app.route('/admin/survey-results/management')
@login_required
def admin_survey_results_management():
    """Management survey results"""
    if current_user.role != "admin":
        flash("Access denied. Admin only.", "danger")
        return redirect(url_for('index'))

    # Get all management survey responses
    responses = NewSurveyResponse.query.filter_by(
        survey_type='management'
    ).all()

    if not responses:
        flash("No management survey data available.", "info")
        return render_template('admin_survey_management.html',
                               responses=[],
                               stats={},
                               comments=[])

    # Calculate statistics
    total = len(responses)

    # Map text values to numeric scores (1-5)
    score_mapping = {
        "1": 1, "Very Dissatisfied": 1, "Very Unclean": 1, "Very Unreasonable": 1, "Very Insufficient": 1,
        "2": 2, "Dissatisfied": 2, "Not Clean": 2, "Unreasonable": 2, "Insufficient": 2,
        "3": 3, "Average": 3, "Average": 3, "Average": 3, "Average": 3,
        "4": 4, "Satisfied": 4, "Clean": 4, "Reasonable": 4, "Rich": 4,
        "5": 5, "Very Satisfied": 5, "Very Clean": 5, "Very Reasonable": 5, "Very Rich": 5
    }

    # Initialize sums
    campus_cleanliness_sum = 0
    cafeteria_sum = 0
    holiday_arrangement_sum = 0
    student_activities_sum = 0
    valid_cc = 0
    valid_caf = 0
    valid_ha = 0
    valid_sa = 0

    # Collect comments
    comments = []

    for resp in responses:
        # Calculate campus cleanliness score
        if resp.campus_cleanliness and resp.campus_cleanliness in score_mapping:
            campus_cleanliness_sum += score_mapping[resp.campus_cleanliness]
            valid_cc += 1

        # Calculate cafeteria score
        if resp.cafeteria and resp.cafeteria in score_mapping:
            cafeteria_sum += score_mapping[resp.cafeteria]
            valid_caf += 1

        # Calculate holiday arrangement score
        if resp.holiday_arrangement and resp.holiday_arrangement in score_mapping:
            holiday_arrangement_sum += score_mapping[resp.holiday_arrangement]
            valid_ha += 1

        # Calculate student activities score
        if resp.student_activities and resp.student_activities in score_mapping:
            student_activities_sum += score_mapping[resp.student_activities]
            valid_sa += 1

        # Collect comments
        if resp.other_management and resp.other_management.strip():
            user = User.query.get(resp.user_id)
            comments.append({
                'username': user.username if user else 'Unknown',
                'comment': resp.other_management.strip()
            })

    # Calculate averages
    stats = {
        'total_responses': total,
        'campus_cleanliness_avg': round(campus_cleanliness_sum / valid_cc, 2) if valid_cc > 0 else 0,
        'cafeteria_avg': round(cafeteria_sum / valid_caf, 2) if valid_caf > 0 else 0,
        'holiday_arrangement_avg': round(holiday_arrangement_sum / valid_ha, 2) if valid_ha > 0 else 0,
        'student_activities_avg': round(student_activities_sum / valid_sa, 2) if valid_sa > 0 else 0,
    }

    return render_template('admin_survey_management.html',
                           responses=responses,
                           stats=stats,
                           comments=comments)


@app.route('/admin/survey-results/teaching')
@login_required
def admin_survey_results_teaching():
    """Teaching survey results"""
    if current_user.role != "admin":
        flash("Access denied. Admin only.", "danger")
        return redirect(url_for('index'))

    # Get all teaching survey responses
    responses = NewSurveyResponse.query.filter_by(
        survey_type='teaching'
    ).all()

    if not responses:
        flash("No teaching survey data available.", "info")
        return render_template('admin_survey_teaching.html',
                               responses=[],
                               stats={},
                               comments=[],
                               dissatisfaction_comments=[])

    # Calculate statistics
    total = len(responses)

    # Initialize counters
    teacher_responsibility_yes = 0
    teaching_satisfaction_yes = 0
    teacher_responsibility_no = 0
    teaching_satisfaction_no = 0

    # Collect comments
    comments = []
    dissatisfaction_comments = []

    for resp in responses:
        # Count teacher responsibility
        if resp.teacher_responsibility == 'yes':
            teacher_responsibility_yes += 1
        elif resp.teacher_responsibility == 'no':
            teacher_responsibility_no += 1

        # Count teaching satisfaction
        if resp.teaching_satisfaction == 'yes':
            teaching_satisfaction_yes += 1
        elif resp.teaching_satisfaction == 'no':
            teaching_satisfaction_no += 1

        # Collect dissatisfaction reasons
        if resp.dissatisfaction_reason and resp.dissatisfaction_reason.strip():
            user = User.query.get(resp.user_id)
            dissatisfaction_comments.append({
                'username': user.username if user else 'Unknown',
                'comment': resp.dissatisfaction_reason.strip()
            })

        # Collect other comments
        if resp.other_teaching and resp.other_teaching.strip():
            user = User.query.get(resp.user_id)
            comments.append({
                'username': user.username if user else 'Unknown',
                'comment': resp.other_teaching.strip()
            })

    # Calculate percentages
    tr_yes_pct = round((teacher_responsibility_yes / total) * 100, 1) if total > 0 else 0
    tr_no_pct = round((teacher_responsibility_no / total) * 100, 1) if total > 0 else 0
    ts_yes_pct = round((teaching_satisfaction_yes / total) * 100, 1) if total > 0 else 0
    ts_no_pct = round((teaching_satisfaction_no / total) * 100, 1) if total > 0 else 0

    stats = {
        'total_responses': total,
        'teacher_responsibility_yes_pct': tr_yes_pct,
        'teacher_responsibility_no_pct': tr_no_pct,
        'teaching_satisfaction_yes_pct': ts_yes_pct,
        'teaching_satisfaction_no_pct': ts_no_pct,
    }

    return render_template('admin_survey_teaching.html',
                           responses=responses,
                           stats=stats,
                           comments=comments,
                           dissatisfaction_comments=dissatisfaction_comments)