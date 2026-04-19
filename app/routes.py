import os
from datetime import datetime

from flask import render_template, redirect, url_for, flash, request, current_app, json, session
from werkzeug.utils import secure_filename, send_from_directory

from app import app
from app import db
from app.models import SupportMessage, NewSurveyResponse
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
            teacher_type=form.teacher_type.data if form.role.data == "teacher" else ""  # 确保保存
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
    return render_template("survey_template.html", form=form)


# ====================== Appointment System Routes ======================

@app.route('/appointment', methods=['GET', 'POST'])
@login_required
def appointment():
    """学生预约主页"""
    if current_user.role != "student":
        flash("只有学生可以预约", "danger")
        return redirect(url_for('index'))

    form = AppointmentForm()
    return render_template('appointment.html', form=form)


@app.route('/api/teachers/<teacher_type>')
@login_required
def get_teachers(teacher_type):
    """根据老师类型返回老师列表"""
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
    """获取老师有可用时间段的日期列表"""
    from datetime import date

    # 查询该老师有可用时间段且未约满的日期
    available_dates = db.session.query(TimeSlot.date).filter(
        TimeSlot.teacher_id == teacher_id,
        TimeSlot.is_booked == False
    ).distinct().all()

    # 过滤掉所有时间段都被约满的日期
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
    """获取指定日期的可用时间段"""
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
    """提交预约申请"""
    if current_user.role != "student":
        return jsonify({'success': False, 'message': '权限不足'})

    data = request.get_json()
    time_slot_id = data.get('time_slot_id')
    description = data.get('description', '')
    appointment_type = data.get('appointment_type')

    # 检查时间段是否已被预约
    time_slot = TimeSlot.query.get(time_slot_id)
    if not time_slot or time_slot.is_booked:
        return jsonify({'success': False, 'message': '该时间段已被预约'})

    # 创建预约记录
    appointment = Appointment(
        student_id=current_user.id,
        teacher_id=time_slot.teacher_id,
        time_slot_id=time_slot_id,
        appointment_type=appointment_type,
        description=description,
        status='confirmed'
    )

    # 标记时间段为已预约
    time_slot.is_booked = True

    db.session.add(appointment)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': '预约申请已提交，等待老师确认'
    })


@app.route('/my_appointments')
@login_required
def my_appointments():
    """查看我的预约"""
    if current_user.role == "teacher":
        appointments = Appointment.query.filter_by(
            teacher_id=current_user.id
        ).order_by(Appointment.created_at.desc()).all()
    else:
        appointments = Appointment.query.filter_by(
            student_id=current_user.id
        ).order_by(Appointment.created_at.desc()).all()
    return render_template('my_appointments.html', appointments=appointments)


# @app.route('/appointment/<int:appointment_id>/<action>', methods=['POST'])
# @login_required
# def handle_appointment(appointment_id, action):
#     """老师确认/拒绝预约"""
#     appointment = Appointment.query.get_or_404(appointment_id)

#     if current_user.id != appointment.teacher_id:
#         flash("无权操作", "danger")
#         return redirect(url_for('index'))

#     if action == 'confirm':
#         appointment.status = 'confirmed'
#         flash("预约已确认", "success")
#     elif action == 'reject':
#         appointment.status = 'rejected'
#         # 释放时间段
#         appointment.time_slot.is_booked = False
#         flash("预约已拒绝", "info")

#     db.session.commit()
#     return redirect(url_for('my_appointments'))


@app.route('/appointment/<int:appointment_id>/cancel', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    """学生撤销预约"""
    appointment = Appointment.query.get_or_404(appointment_id)

    # 检查权限：只有预约的学生本人可以撤销
    if current_user.id != appointment.student_id:
        flash("无权操作", "danger")
        return redirect(url_for('index'))

    # 检查状态：只能撤销待确认或已确认的预约
    if appointment.status != 'confirmed':
        flash("该预约无法撤销", "warning")
        return redirect(url_for('my_appointments'))

    # 释放时间段
    appointment.time_slot.is_booked = False
    
    # 删除预约记录或更新状态为已取消
    # 方案A：删除记录
    db.session.delete(appointment)
    
    # 方案B：更新状态（如需保留记录）
    # appointment.status = 'cancelled'
    
    db.session.commit()
    flash("预约已撤销", "success")
    return redirect(url_for('my_appointments'))


@app.route('/teacher/time_slots', methods=['GET', 'POST'])
@login_required
def manage_time_slots():
    """老师管理可预约时间段"""
    if current_user.role != "teacher":
        flash("只有老师可以管理时间段", "danger")
        return redirect(url_for('index'))

    form = TimeSlotForm()

    if form.validate_on_submit():
        date = form.date.data
        selected_slots = form.time_slots.data

        # 检查是否已存在这些时间段
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
            flash(f"成功添加 {added_count} 个时间段", "success")
        else:
            flash("所选时间段已存在", "info")

        return redirect(url_for('manage_time_slots'))

    # 获取老师已设置的时间段
    my_slots = TimeSlot.query.filter_by(
        teacher_id=current_user.id
    ).order_by(TimeSlot.date.desc(), TimeSlot.time_slot).all()

    return render_template('manage_time_slots.html', form=form, slots=my_slots)
# ====================== End of Appointment Routes ======================