import os
from datetime import datetime

from flask import render_template, redirect, url_for, flash, request, current_app, json
from werkzeug.utils import secure_filename, send_from_directory

from app import app
from app import db
from app.models import SupportMessage
from app.forms import SupportMessageForm, TeacherUpload
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError


# Home page: submit and display all messages
@app.route('/', methods=['GET', 'POST'])
def index():
    form = SupportMessageForm()

    if form.validate_on_submit():
        try:
            # create a message
            support_msg = SupportMessage(
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
            db.session.rollback()
            flash(f"Error adding message: {str(e)}", "danger")

    # Display all messages in descending order of publication date
    support_messages = SupportMessage.query.order_by(SupportMessage.publish_date.desc()).all()
    return render_template('index.html', form=form, student_infos=support_messages)


# List page: Display all messages in descending order of priority
@app.route('/listing', methods=['GET', 'POST'])
def listing_messages():
    # In descending order of priority (with high priority first)
    messages = SupportMessage.query.order_by(SupportMessage.priority.desc()).all()
    print("Number of messages retrieved：", len(messages))
    print("Message details：", messages)
    return render_template('listing.html', students=messages)


# Search page: Search for messages by teacher email
@app.route('/searching', methods=['GET', 'POST'])
def search_messages():
    email = request.args.get("email", "").strip().lower()
    course_name = request.args.get("course_name", "").strip().lower()
    message_title = request.args.get("message_title", "").strip().lower()
    query = SupportMessage.query

    # fuzzy search conditions
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
def file_upload():
    # create an object for your upload form
    form = TeacherUpload()
    filename = None
    # create the path for the json file to write uploads to
    file_path = os.path.join(
        current_app.root_path, 'static', 'uploads.json')
    try:
        with open(file_path, "r") as file:
            feedback_store = json.load(file)
    except FileNotFoundError:
        feedback_store = []

    # grab the upload and save to json file
    if form.validate_on_submit():
        upload_data = {
            "teacher_name": form.teacher_name.data,
            "course_name": form.course_name.data,
            "remark": form.remark.data,
            "filename": filename,
            "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        feedback_store.append(upload_data )
        with open(file_path, "w") as file:
            json.dump(feedback_store, file, indent=4)
        # get the file to upload / attach and upload the file to uploads /
        file = form.file.data
        # the if handles the uploading, after the if we prepare for the listing files and downloading
        if file:
            filename = secure_filename(file.filename) # secure_filename is used to make sure the file is safe to store on the browser
            uploaded_folder = current_app.config['UPLOAD_FOLDER'] # to give Flask the current_app that is handling this request
            file.save(os.path.join(uploaded_folder, filename))
            flash("File uploaded successfully!")
            return redirect(url_for("file_upload", filename=filename))
    # for the downloading of a file, get all the files that must be listed
    uploaded_folder = current_app.config['UPLOAD_FOLDER']
    #files = os.listdir(uploaded_folder)
    #files list ignore gitkeep
    files = [f for f in os.listdir(uploaded_folder) if f != ".gitkeep"]
    # download the file that has just been uploaded
    filename = request.args.get('filename')
    # this render_template works for both submitting the form, uploads and downloads
    return render_template("upload.html", form=form, filename=filename, files=files)

"""
Clicking the Download link triggers a GET request with the filename in the URL. 
Flask passes this filename to the download_file route, which returns the file to the browser as a download.
"""
@app.route('/uploads/<filename>')
def download_file(filename):
    uploaded_folder = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(
        uploaded_folder,
        filename,
        as_attachment=True)

# choose a file to download from the list of files that have been uploaded previously
@app.route('/downloads')
def downloads():
    uploaded_folder = current_app.config['UPLOAD_FOLDER']
    #files = os.listdir(uploaded_folder)
    # files list ignore gitkeep
    files = [f for f in os.listdir(uploaded_folder) if f != ".gitkeep"]
    files.sort(reverse=True)
    return render_template('downloads.html', files=files)



