from flask import Flask, jsonify, render_template, redirect, send_from_directory, url_for, request, session, flash
from datetime import datetime, timedelta
import functools, db, timeago, hashlib, hmac, os, base64, face_recognition
from authlib.integrations.flask_client import OAuth
from flask_wtf.csrf import CSRFProtect, generate_csrf
from werkzeug.exceptions import BadRequest
from flask_session import Session
from threading import Lock
import json, random
import numpy as np
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("APP_SECRET_KEY")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=3)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

csrf = CSRFProtect(app)
app.config['WTF_CSRF_CHECK_DEFAULT'] = True
app.config['WTF_CSRF_METHODS'] = ['POST', 'PUT', 'PATCH', 'DELETE']
app.config['WTF_CSRF_FIELD_NAME'] = 'csrf_token'
app.config['WTF_CSRF_HEADERS'] = ['X-CSRF-Token']
csrf.init_app(app)

app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ATTENDANCE_FOLDER'] = 'static/attendance'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['ATTENDANCE_FOLDER'], exist_ok=True)

JITSI_MEET_BASE_URL = "https://meet.jit.si"

oauth = OAuth(app)

load_dotenv()
google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url=os.getenv("SERVER_METEDATA_URL"),
    client_kwargs={"scope": "openid email profile"},
)

def role_required(*allowed_roles):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if 'username' not in session:

                refer_url = request.full_path  
                flash('Please log in first!', 'warning')
                return redirect(url_for('login', refer=refer_url))
            role = check_session_and_role()
            if isinstance(role, str) and role in allowed_roles:
                return f(*args, **kwargs)
            flash(f'Access denied. Need one of these roles: {", ".join(allowed_roles)}', 'danger')
            return redirect(url_for('dashboard'))
        return wrapper
    return decorator

login_required = role_required('student', 'instructor', 'admin')
instructor_required = role_required('instructor')
student_required = role_required('student')
admin_required = role_required('admin')
student_or_instructor_or_admin_required = role_required('student', 'instructor', 'admin')
instructor_or_admin_required = role_required('instructor', 'admin')

ROLE_TEMPLATES = {
    'student': {'dashboard': 'student_dashboard.html', 'home': 'student/home.html'},
    'instructor': {'dashboard': 'instructor_dashboard.html', 'home': 'instructor/home.html'},
    'admin': {'dashboard': 'admin_dashboard.html', 'home': 'admin/home.html'}
}

# check_session_and_role()
# Purpose: Verifies the user's session and role, ensuring the account is valid and not deleted
# Parameters: None (uses session object for user info)
# Returns: The user's role if valid, or redirects to login page with a flash message on error
# Related: login(), logout(), db.Database.get_cursor()
def check_session_and_role():
    if 'role_checked' not in session:
        if 'info' not in session or 'role' not in session['info']:
            flash('Session expired. Log in again!', 'warning')
            return redirect(url_for('login'))

        user_id = session['info']['id']
        role = session['info']['role']
        valid_roles = {'student': 'students', 'instructor': 'instructors', 'admin': 'admins'}

        if role not in valid_roles:
            session.clear()
            flash('Invalid role, dude. Logging out!', 'danger')
            return redirect(url_for('login'))

        table = valid_roles[role]
        try:
            with db.Database.get_cursor() as cur:
                cur.execute(f"SELECT deleted_at FROM {table} WHERE id = %s", (user_id,))
                result = cur.fetchone()
                if result and result[0] is not None:
                    session.clear()
                    flash('Account deleted. Logging out!', 'warning')
                    return redirect(url_for('login'))
        except Exception as e:
            flash(f'DB error: {str(e)}. Try again later!', 'danger')
            return redirect(url_for('login'))

        session['role_checked'] = role
    return session['role_checked']


# about()
# Purpose: Renders the mainReload
# Parameters: None
# Returns: Rendered 'index.html' template for the application's about page
# Related: None
@app.route('/')
def about():
    return render_template('index.html')

# login()
# Purpose: Handles user login via form submission or redirects if already logged in
# Parameters: None (uses request object for form data and session)
# Returns: Rendered 'login.html' template for GET, JSON response for POST with login status
# Related: check_session_and_role(), db.Auth.login()
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))

    refer_url = request.args.get('refer', url_for('dashboard'))  
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        refer_url = request.form.get('refer', refer_url)  
        if not (username and password):
            return jsonify({'success': False, 'error': 'Missing creds!'}), 400

        response, status = db.Auth.login(username, password)
        if status == 1:
            session.permanent = True
            session['username'] = username
            session['info'] = response
            session.pop('role_checked', None)
            redirect_url = refer_url if refer_url.startswith('/') else url_for('dashboard')
            resp = jsonify({'success': True, 'redirect': redirect_url})
            resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
            return resp
        else:
            resp = jsonify({'success': False, 'error': response})
            resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
            return resp, 401

    return render_template('login.html', csrf_token=generate_csrf(), refer_url=refer_url)

# login_google()
# Purpose: Initiates Google OAuth login flow
# Parameters: None
# Returns: Redirect to Google's authorization URL
# Related: authorize()
@app.route('/login-google')
def login_google():
    return google.authorize_redirect(url_for("authorize", _external=True))

# authorize()
# Purpose: Handles Google OAuth callback, processes user info, and logs in or redirects to registration
# Parameters: None (uses request object for token and user info)
# Returns: Redirect to dashboard if login successful, else to register
# Related: login_google(), register(), db.Auth.login()
@app.route("/login/callback")
def authorize():
    token = google.authorize_access_token()
    user_info = google.get("https://www.googleapis.com/oauth2/v2/userinfo").json()

    email = user_info.get("email")
    google_id = user_info.get("id")
    name = user_info.get("name")
    profile_picture = user_info.get("picture")

    if not email or not google_id:
        flash("Google login failed. Try again!", "danger")
        return redirect(url_for("login"))

    response, status = db.Auth.login(google_id, None)
    print(response, status)
    if status == 1:
        session.permanent = True
        session["info"] = response
        session["username"] = email
        return redirect(url_for("dashboard"))

    session["pending_registration"] = {"email": email, "google_id": google_id, "name": name, "profile_picture": profile_picture}
    return redirect(url_for("register"))

# register()
# Purpose: Handles user registration, either via Google OAuth or form submission
# Parameters: None (uses session and request object for data)
# Returns: Rendered 'login.html' with register mode for GET, JSON response for POST
# Related: login(), authorize(), db.Enrollment.register_user()
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' in session:
        return redirect(url_for('dashboard'))

    google_data = session.get("pending_registration", {})

    if request.method == 'POST':
        data = {
            "username": google_data.get("email") or request.form.get("username"),
            "name": google_data.get("name") or request.form.get("name"),
            "email": google_data.get("email") or request.form.get("email"),
            "phone": request.form.get("phone"),
            "enrollment_id": request.form.get("enrollment_id"),
            "password": None if google_data else request.form.get("password"),
            "google_id": google_data.get("google_id"),
            "profile_picture": google_data.get("profile_picture"),
        }

        if not all([data["username"], data["name"], data["email"], data["phone"], data["enrollment_id"]]):
            return jsonify(success=False, error="All fields required!")
        print(data)
        response, status = db.Enrollment.register_user(**data)  
        if status == 1:

            flash('Registration successful! Awaiting verification...', 'success')
            session.pop("pending_registration", None)

            return jsonify(success=True, redirect=url_for('login'))
        return jsonify(success=False, error=response)

    return render_template('login.html', register_mode=True, google_data=google_data, csrf_token=generate_csrf())

# manage_registrations()
# Purpose: Allows instructors to view and verify/reject pending registrations
# Parameters: None (uses request object for form data)
# Returns: Rendered 'instructor_registrations.html' for GET, JSON response for POST
# Related: reject_registration(), db.Student.verify_and_move_to_students()
@app.route('/instructor/registrations', methods=['GET', 'POST'])
def manage_registrations():

    if request.method == 'POST':
        enrollment_id = request.form.get('enrollment_id')
        if not enrollment_id:
            return jsonify(success=False, error="Enrollment ID required")

        response, status = db.Student.verify_and_move_to_students(enrollment_id)
        if status == 1:
            return jsonify(success=True, message=response)
        return jsonify(success=False, error=response)

    try:
        with db.Database.get_cursor() as cur:
            cur.execute("""
                SELECT id, username, name, email, phone, enrollment_id, created_at 
                FROM enrollments 
                WHERE status = 'pending' AND deleted_at IS NULL 
                ORDER BY created_at DESC
            """)
            pending_registrations = cur.fetchall()
    except Exception as e:
        flash(f"Error loading registrations: {e}", 'error')
        pending_registrations = []

    return render_template(
        'instructor/instructor_registrations.html',
        registrations=pending_registrations,
        csrf_token=generate_csrf()
    )

# reject_registration()
# Purpose: Rejects a pending registration by marking it as rejected in the database
# Parameters: None (uses request.form for enrollment_id)
# Returns: JSON response indicating success or failure
# Related: manage_registrations()
@app.route('/instructor/registrations/reject', methods=['POST'])
def reject_registration():
    enrollment_id = request.form.get('enrollment_id')
    if not enrollment_id:
        return jsonify(success=False, error="Enrollment ID required")

    try:
        with db.Database.get_cursor() as cur:
            cur.execute("""
                UPDATE enrollments 
                SET status = 'rejected', deleted_at = CURRENT_TIMESTAMP 
                WHERE id = %s AND status = 'pending' AND deleted_at IS NULL
            """, (enrollment_id,))
            if cur.rowcount == 0:
                return jsonify(success=False, error="Enrollment not found or already processed")
            return jsonify(success=True, message="Registration rejected successfully")
    except Exception as e:
        return jsonify(success=False, error=str(e))

# manage_students()
# Purpose: Allows admins to manage student statuses and batch assignments
# Parameters: None (uses request object for form data)
# Returns: Rendered 'admin_students.html' for GET, JSON response for POST
# Related: update_student_batch(), db.Student.verify_and_move_to_students()
@app.route('/instructor/students', methods=['GET', 'POST'])
@admin_required  
def manage_students():
    if request.method == 'POST':
        enrollment_id = request.form.get('enrollment_id')
        new_status = request.form.get('status')
        batch_id = request.form.get('batch_id')  

        if not enrollment_id or not new_status:
            return jsonify(success=False, error="Enrollment ID and status required")

        try:
            with db.Database.get_cursor() as cur:
                if new_status == 'verified':

                    response, status = db.Student.verify_and_move_to_students(enrollment_id)

                    if status == 1:

                        if batch_id:
                            cur.execute("""
                                UPDATE students 
                                SET batch_id = %s, updated_at = CURRENT_TIMESTAMP
                                WHERE enrollment_id = %s
                            """, (batch_id, enrollment_id))

                        return jsonify(success=True, message="Student verified and batch assigned")

                    return jsonify(success=False, error=response)

                elif new_status in ['pending', 'rejected']:

                    cur.execute("""
                        UPDATE enrollments 
                        SET status = %s, deleted_at = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (new_status, 'CURRENT_TIMESTAMP' if new_status == 'rejected' else None, enrollment_id))

                    cur.execute("""
                        DELETE FROM students WHERE enrollment_id = %s
                    """, (enrollment_id,))

                    if cur.rowcount == 0:
                        return jsonify(success=False, error="Enrollment not found or no change needed")

                    return jsonify(success=True, message=f"Student status updated to {new_status}")

                else:
                    return jsonify(success=False, error="Invalid status")
        except Exception as e:
            return jsonify(success=False, error=str(e))

    try:
        with db.Database.get_cursor() as cur:

            cur.execute("""
                SELECT 
                    enrollments.id, 
                    enrollments.username, 
                    enrollments.name, 
                    enrollments.email, 
                    enrollments.phone, 
                    enrollments.enrollment_id, 
                    enrollments.status, 
                    enrollments.created_at, 
                    enrollments.deleted_at, 
                    students.batch_id
                FROM enrollments 
                LEFT JOIN students 
                ON enrollments.enrollment_id = students.enrollment_id
            """)
            all_registrations = cur.fetchall()
            all_registrations.sort(key=lambda student: student[7], reverse=True)

            cur.execute("""
                SELECT id, batch_name 
                FROM batches 
                WHERE deleted_at IS NULL
                ORDER BY batch_name
            """)
            batches = cur.fetchall()  

    except Exception as e:
        flash(f"Error loading data: {e}", 'error')
        all_registrations = []
        batches = []

    return render_template(
        'admin/admin_students.html',  
        students=all_registrations,
        batches=batches,  
        csrf_token=generate_csrf()
    )

# update_student_batch()
# Purpose: Updates the batch assignment for a student
# Parameters: None (uses request.form for enrollment_id and batch_id)
# Returns: JSON response indicating success or failure
# Related: manage_students()
@app.route('/admin/update-student-batch', methods=['POST'])
@admin_required
def update_student_batch():
    enrollment_id = request.form.get('enrollment_id')
    batch_id = request.form.get('batch_id')

    if not enrollment_id or not batch_id:
        return jsonify({'success': False, 'error': 'Enrollment ID and batch ID are required'}), 400

    try:
        with db.Database.get_cursor() as cur:

            cur.execute("""
                SELECT name FROM students WHERE enrollment_id = %s AND deleted_at IS NULL
            """, (enrollment_id,))
            student = cur.fetchone()
            if not student:
                return jsonify({'success': False, 'error': 'Student not found'}), 404

            student_name = student[0]

            cur.execute("""
                UPDATE students 
                SET batch_id = %s, updated_at = CURRENT_TIMESTAMP
                WHERE enrollment_id = %s
            """, (batch_id, enrollment_id))

            if cur.rowcount == 0:
                return jsonify({'success': False, 'error': 'No changes made to the student record'}), 400

        return jsonify({
            'success': True,
            'message': f'Batch updated successfully for {student_name}'
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# logout()
# Purpose: Clears session and logs out the user
# Parameters: None
# Returns: Redirect to login page
# Related: None
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out!', 'info')
    return redirect(url_for('login'))

# service_worker()
# Purpose: Serves the service worker JavaScript file
# Parameters: None
# Returns: File response for 'service-worker.js'
# Related: None
@app.route('/service-worker.js')
@csrf.exempt
def service_worker():
    return send_from_directory('static/js', 'service-worker.js', mimetype='application/javascript')

# dashboard()
# Purpose: Renders role-specific dashboard based on user role
# Parameters: None (uses session for role)
# Returns: Rendered role-specific dashboard template
# Related: check_session_and_role(), ROLE_TEMPLATES
@app.route('/dashboard')
@login_required
def dashboard():

    role = check_session_and_role()
    if isinstance(role, str) and role in ROLE_TEMPLATES:
        return render_template(ROLE_TEMPLATES[role]['dashboard'], csrf_token=generate_csrf())
    flash('Unauthorized, dude. Logging out!', 'danger')
    return redirect(url_for('logout'))

# dashboard_home()
# Purpose: Renders role-specific home page with videos and live classes
# Parameters: None (uses session for user_id and role)
# Returns: Rendered role-specific home template
# Related: db.Student.get_student_data(), db.Instructor.get_instructor_data(), db.LiveClass.get_live_classes_for_batch(), db.LiveClass.get_live_classes_for_instructor()
@app.route('/dashboard/home')
@login_required
def dashboard_home():
    role = check_session_and_role()
    if isinstance(role, str) and role in ROLE_TEMPLATES:
        user_id = session['info']['id']
        if role == 'student':
            data, status = db.Student.get_student_data(user_id)
            videos = data['videos'] if status == 1 else []
        elif role == 'instructor':
            data, status = db.Instructor.get_instructor_data(user_id)
            videos = data['videos'] if status == 1 else []
        else:
            videos = []
        live_classes = None
        if session['info']['role']=='student':
            student_data, status = db.Student.get_student_data(user_id)
            if status != 1:
                flash('Error fetching student data!', 'danger')
                return redirect(url_for('dashboard'))
            batch_id = student_data['batches'][0][0]
            if not batch_id:
                flash('No batch assigned!', 'danger')
                return redirect(url_for('dashboard'))
            live_classes, status = db.LiveClass.get_live_classes_for_batch(batch_id)
        elif session['info']['role']=='instructor':
            live_classes, status = db.LiveClass.get_live_classes_for_instructor(user_id)

        return render_template(ROLE_TEMPLATES[role]['home'], videos=videos, live_classes=live_classes,now=datetime.now)

    flash('Unauthorized. Logging out!', 'danger')
    return redirect(url_for('logout'))

# batch_default_right()
# Purpose: Displays videos for a student's batch
# Parameters: None (uses session for user_id)
# Returns: Rendered 'course-videos.html' with videos
# Related: db.Student.get_student_data()
@app.route('/batch-default-right')
@student_required
def batch_default_right():
    data, status = db.Student.get_student_data(session['info']['id'])
    videos = data['videos'] if status == 1 else []
    return render_template('student/course-videos.html', videos=videos)

# batches_cards()
# Purpose: Displays batch and course cards for a student
# Parameters: None (uses session for user_id)
# Returns: Rendered 'batches-cards.html' with batches and courses
# Related: db.Student.get_student_data()
@app.route('/batches-cards')
@student_required
def batches_cards():
    data, status = db.Student.get_student_data(session['info']['id'])
    if status != 1:
        flash('Error fetching data!', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('student/batches-cards.html', 
                         batches=[dict(zip(('id', 'name', 'start_date', 'end_date'), b)) for b in data['batches']],
                         courses=[dict(zip(('id', 'name', 'description', 'instructor'), c)) for c in data['courses']],
                         videos=[dict(zip(('id', 'title', 'description', 'url', 'thumbnail', 'duration', 'course', 'instructor'), v)) for v in data['videos']])

# get_batch_students()
# Purpose: Fetches students in a specific batch
# Parameters: batch_id (URL parameter)
# Returns: JSON response with list of students
# Related: db.Student.get_students_by_batch()
@app.route('/get_batch_students/<batch_id>')
@student_or_instructor_or_admin_required
def get_batch_students(batch_id):

    if session['info']['role'] == 'student':
        student_id = session['info']['id']
    else:
        student_id = None
    students, status = db.Student.get_students_by_batch(batch_id, student_id)
    if status != 1:
        return jsonify({'error': students}), 400  
    return jsonify({'students': students})  

# course_page()
# Purpose: Displays details for a specific course
# Parameters: id (query parameter)
# Returns: Rendered 'course.html' with course details or 404
# Related: db.Course.get_course(), db.Instructor.get_instructor()
@app.route('/course')
@student_or_instructor_or_admin_required
def course_page():
    id = request.args.get('id')
    if id:
        course, status = db.Course.get_course(id)
        if status == 1:
            instructor_data, instr_status = db.Instructor.get_instructor(course[2])
            instructor_name = instructor_data['name'] if instr_status == 1 else "Unknown"
            return render_template('student/course.html', course={
                'id': course[0], 'name': course[1], 'instructor': instructor_name,
                'duration': '6 Months', 'description': course[3]
            })
    return 'Course not found!', 404

# manage_classes()
# Purpose: Renders the manage classes page for instructors
# Parameters: None
# Returns: Rendered 'manage-classes.html'
# Related: None
@app.route('/manage-classes')
@instructor_required
def manage_classes():
    return render_template('instructor/manage-classes.html')

# manage_class_cards()
# Purpose: Displays batch, course, and video cards for instructors
# Parameters: None (uses session for user_id)
# Returns: Rendered 'manage-class-cards.html'
# Related: db.Instructor.get_instructor_data()
@app.route('/manage-class-cards')
@instructor_required
def manage_class_cards():
    user_id = session['info']['id']
    data, status = db.Instructor.get_instructor_data(user_id)
    if status != 1:
        flash('Error fetching data!', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('instructor/manage-class-cards.html', 
                           batches=tuple(set(data['batches'])), courses=data['courses'], videos=data['videos'])

# manage_class_default_right()
# Purpose: Displays videos for instructor's courses
# Parameters: None (uses session for user_id)
# Returns: Rendered 'course-videos.html' with videos
# Related: db.Instructor.get_instructor_data()
@app.route('/manage-class-default-right')
@instructor_required
def manage_class_default_right():
    data, status = db.Instructor.get_instructor_data(session['info']['id'])
    videos = data['videos'] if status == 1 else []
    return render_template('instructor/course-videos.html', videos=videos)

# edit_course_video()
# Purpose: Allows instructors/admins to edit course or video details
# Parameters: None (uses request.form for data, query parameter for id)
# Returns: Rendered 'edit-course-video.html' for GET, JSON response for POST
# Related: db.Course.update_course(), db.Video.update_video()
@app.route('/edit-course-video', methods=['GET', 'POST'])
@instructor_or_admin_required
def edit_course_video():
    if request.method == 'GET':
        user_role = session['info']['role']
        user_id = session['info']['id']
        if user_role == 'instructor':
            data, status = db.Instructor.get_instructor_data(user_id)
            if status != 1:
                flash('Error fetching data!', 'danger')
                return redirect(url_for('dashboard'))
            seen_courses = set()
            courses = [c for c in data['courses'] if not (c[0] in seen_courses or seen_courses.add(c[0]))]
            return render_template('instructor/edit-course-video.html', user_id=user_id, 
                                   batches=tuple(set(data['batches'])), courses=courses,
                                   videos=[v for i, v in enumerate(data['videos']) if v[0] not in {x[0] for x in data['videos'][:i]}], 
                                   url_id=request.args.get('id'), csrf_token=generate_csrf(), admin=0)
        elif user_role == 'admin':
            data, status = db.Admin.get_all_batches_courses_videos()
            if status != 1:
                flash('Error fetching data!', 'danger')
                return redirect(url_for('dashboard'))
            seen_courses = set()
            courses = [c for c in data['courses'] if not (c[0] in seen_courses or seen_courses.add(c[0]))]
            return render_template('instructor/edit-course-video.html', user_id=user_id, 
                                batches=tuple(set(data['batches'])), instructors=data['instructors'], courses=courses,
                                videos=[v for i, v in enumerate(data['videos']) if v[0] not in {x[0] for x in data['videos'][:i]}],
                                url_id=request.args.get('id'), csrf_token=generate_csrf(), admin=1)

    else:
        data = request.form
        try:
            if 'courseId' in data:
                if not all(data.get(k) for k in ['courseTitle', 'courseDescription', 'instructorAdditional']):
                    return jsonify({'message': 'Missing course fields!'}), 400
                instructor_id = data['instructorAdditional'] if session['info']['role'] == 'admin' else None
                result, status = db.Course.update_course(data['courseId'], data['courseTitle'], data['courseDescription'], instructor_id)
                return jsonify({'message': 'Course updated!' if status == 1 else result})
            elif 'videoId' in data:
                if not all(data.get(k) for k in ['videoTitle', 'videoDescription', 'videoUrl', 'videoThumbnail', 'videoDuration']):
                    return jsonify({'message': 'Missing video fields, dude!'}), 400
                result, status = db.Video.update_video(data['videoId'], data.get('videoTitle'), data.get('videoDescription'), 
                                                      data.get('videoUrl'), data.get('videoThumbnail'), data.get('videoDuration'))
                return jsonify({'message': 'Video updated!' if status == 1 else result})
            return jsonify({'message': 'No valid data!'}), 400
        except Exception as e:
            app.logger.error(f"Error updating: {str(e)}")
            return jsonify({'message': f'Error: {str(e)}'}), 500

# delete_course_video()
# Purpose: Deletes a course or video
# Parameters: None (uses request.form for type and id)
# Returns: JSON response indicating success or failure
# Related: db.Video.delete_video(), db.Course.delete_course()
@app.route('/delete-course-video', methods=['POST'])
@instructor_or_admin_required
def delete_course_video():
    typei = request.form.get('type')
    id = request.form.get('id')
    if typei == 'video':
        print(id)
        result, status = db.Video.delete_video(id)
        print(status)
        return jsonify({'message': result if status == 1 else 'Video deletion failed!'}), 400 if status == 0 else 200
    if typei == 'course' and session['info']['role'] == 'admin':
        result, status = db.Course.delete_course(id)
        return jsonify({'message': result if status == 1 else 'Course deletion failed!'}), 400 if status == 0 else 200
    return jsonify({'message': 'Not a course or video!'}), 400

# add_video_course()
# Purpose: Adds a new video or course
# Parameters: None (uses request.form for data)
# Returns: JSON response indicating success or failure
# Related: db.Video.add_video(), db.Course.add_course(), db.BatchCourse.add_batch_course()
@app.route('/add-video-course', methods=['POST'])
@instructor_or_admin_required
def add_video_course():
    data = request.form
    try:
        if 'addVideoCourseId' in data:
            required_fields = ['addVideoCourseId', 'addVideoTitle', 'addVideoUrl', 'addVideoThumbnail', 'addVideoDuration']
            if not all(data.get(k) for k in required_fields):
                return jsonify({'message': 'Missing video fields, dude!'}), 400
            result, status = db.Video.add_video(
                data['addVideoCourseId'], data['addVideoTitle'], data.get('addVideoDescription', ''),
                data['addVideoUrl'], data['addVideoThumbnail'], data['addVideoDuration'], 1
            )

            return jsonify({'message': result if status == 1 else 'Video add failed!'}), 400 if status == 0 else 200

        if 'courseTitle' in data:
            required_fields = ['courseTitle', 'courseDescription', 'addCourseBatch', 'instructorId']
            if not all(data.get(k) for k in required_fields):
                return jsonify({'message': 'Missing course fields!'}), 400
            if session['info']['role'] == 'instructor':
                data = dict(data)
                data['instructorId'] = session['info']['id']
            course_res, course_status = db.Course.add_course(data['courseTitle'], data['courseDescription'], data['instructorId'])
            if course_status == 1:
                batch_res, batch_status = db.BatchCourse.add_batch_course(data['addCourseBatch'], course_res, 0)
                return jsonify({'message': 'Course added!' if batch_status == 1 else batch_res}), 400 if batch_status == 0 else 200
            return jsonify({'message': course_res}), 400
        return jsonify({'message': 'Invalid request, dude!'}), 400
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

# get_attendance_summary()
# Purpose: Fetches attendance summary for a student
# Parameters: None (uses session for student_id)
# Returns: JSON response with total classes and days attended
# Related: None
@app.route('/get_attendance_summary', methods=['GET'])
@student_required
def get_attendance_summary():
    """Fetch the total classes and unique days attended for the logged-in student."""
    student_id = session['info']['id']

    try:
        with db.Database.get_cursor() as cur:

            cur.execute("""
                SELECT COUNT(DISTINCT bc.course_id) 
                FROM batch_courses bc
                INNER JOIN batches b ON bc.batch_id = b.id
                INNER JOIN students s ON s.batch_id = b.id
                WHERE s.id = %s AND s.deleted_at IS NULL AND b.deleted_at IS NULL
            """, (student_id,))
            total_classes = cur.fetchone()[0] or 0

            cur.execute("""
                SELECT COUNT(DISTINCT DATE(timestamp)) 
                FROM attendance 
                WHERE student_id = %s
            """, (student_id,))
            total_attended = cur.fetchone()[0] or 0

        return jsonify({
            'success': True,
            'total_attended': total_attended,
            'total_classes': total_classes
        })
    except Exception as e:
        app.logger.error(f"Error fetching attendance summary: {str(e)}")
        return jsonify({'success': False, 'message': 'Error fetching attendance data'}), 500

# attendance()
# Purpose: Handles attendance page rendering for students, instructors, and admins
# Parameters: None (uses session for user_id and role)
# Returns: Rendered role-specific attendance template
# Related: db.Student.get_student_courses_and_batches(), db.Instructor.get_instructor_data(), db.Admin.get_all_batches_courses_videos()
@app.route('/attendance', methods=['POST', 'GET'])
@student_or_instructor_or_admin_required
def attendance():
    user_id = session['info']['id']
    user_role = session['info']['role']

    if user_role == 'student':
        try:
            with db.Database.get_cursor() as cur:

                cur.execute("SELECT batch_id FROM students WHERE id = %s AND deleted_at IS NULL", (user_id,))
                result = cur.fetchone()
                if not result:
                    flash('Student batch not found!', 'danger')
                    return redirect(url_for('dashboard'))
                batch_id = result[0]

                cur.execute("""
                    SELECT COUNT(DISTINCT DATE(timestamp)) 
                    FROM attendance 
                    WHERE batch_id = %s
                """, (batch_id,))
                total_classes = cur.fetchone()[0] or 0

                cur.execute("""
                    SELECT COUNT(DISTINCT DATE(timestamp)) 
                    FROM attendance 
                    WHERE student_id = %s
                """, (user_id,))
                total_attended = cur.fetchone()[0] or 0

                today = datetime.now().date()
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM attendance 
                    WHERE student_id = %s 
                    AND DATE(timestamp) = %s
                """, (user_id, today))
                today_attendance_count = cur.fetchone()[0]
                today_attendance_recorded = today_attendance_count > 0

            return render_template('student/attendance.html', 
                                total_attended=total_attended, 
                                total_classes=total_classes, 
                                today_attendance_recorded=today_attendance_recorded,
                                csrf_token=generate_csrf())
        except Exception as e:
            app.logger.error(f"Error rendering student attendance: {e}")
            flash('Error loading attendance data!', 'danger')
            return redirect(url_for('dashboard'))

    try:
        with db.Database.get_cursor() as cur:
            if user_role == 'admin':
                cur.execute("""
                    SELECT id, username, email, 'student' AS role, name, profile_picture
                    FROM enrollments WHERE deleted_at IS NULL and status = 'verified'
                    UNION
                    SELECT id, username, email, role, name, profile_picture
                    FROM instructors 
                    WHERE deleted_at IS NULL;
                """)
            elif user_role == 'instructor':
                cur.execute("""
                    SELECT DISTINCT s.id, s.username, s.email, s.role, s.name, s.profile_picture
                    FROM students s
                    INNER JOIN batches b ON s.batch_id = b.id
                    INNER JOIN batch_courses bc ON b.id = bc.batch_id
                    INNER JOIN courses c ON bc.course_id = c.id
                    WHERE c.instructor_id = %s AND s.deleted_at IS NULL AND b.deleted_at IS NULL AND c.deleted_at IS NULL
                """, (user_id,))
            students = cur.fetchall()
            instructor_students = [
                {'id': str(s[0]), 'username': s[1], 'email': s[2], 'role': s[3], 'name': s[4], 'profile_picture': s[5]}
                for s in students
            ]
        admin = user_role == 'admin'
        users = db.Auth.get_all_users()
        students, courses, batches = [], [], []

        if admin:
            students = []
            for user in users:
                if user['role'] == 'student':
                    student_data, s_status = db.Student.get_student_courses_and_batches(user['id'])
                    if s_status == 1:
                        batch_ids = {b['batch_id'] for c in student_data['courses'].values() for b in c['batches']}
                        students.append({
                            'id': user['id'],
                            'name': user['name'],
                            'username': user['username'],
                            'email': user['email'],
                            'batch_ids': list(batch_ids)
                        })
            data, status = db.Admin.get_all_batches_courses_videos()
            if status == 1:
                courses = data['courses']
                batches = data['batches']
        else:
            data, status = db.Instructor.get_instructor_data(user_id)
            if status != 1:
                return render_template('instructor/attendance-left.html', students=[], batches=[], courses=[], csrf_token=generate_csrf(), admin=admin)
            seen_courses = set()
            courses = [c for c in data['courses'] if not (c[0] in seen_courses or seen_courses.add(c[0]))]
            batches = list(set(data['batches']))
            instructor_batch_ids = {b[0] for b in batches}
            for user in users:
                if user['role'] == 'student':
                    student_data, s_status = db.Student.get_student_courses_and_batches(user['id'])
                    if s_status == 1:
                        batch_ids = {b['batch_id'] for c in student_data['courses'].values() for b in c['batches']}
                        if batch_ids & instructor_batch_ids:
                            students.append({
                                'id': user['id'], 
                                'name': user['name'], 
                                'username': user['username'], 
                                'email': user['email'], 
                                'batch_ids': list(batch_ids)
                            })

    except Exception as e:
        app.logger.error(f"Error fetching students: {e}")
        instructor_students = []

    return render_template('instructor/attendance.html', csrf_token=generate_csrf(), users=instructor_students, students=students, batches=batches, courses=courses, admin=admin)

# mark_attendance()
# Purpose: Manually marks attendance for a student on a specific date
# Parameters: None (uses request.form for student_id, date, status)
# Returns: JSON response indicating success or failure
# Related: None
@app.route('/mark-attendance', methods=['POST'])
@instructor_or_admin_required  
@csrf.exempt
def mark_attendance():
    """Mark attendance manually for a student on a specific date."""
    try:

        data = request.form
        student_id = data.get('student_id')
        date_str = data.get('date')  
        status = data.get('status')  

        if not all([student_id, date_str, status]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        if status not in ['present', 'absent']:
            return jsonify({'success': False, 'message': 'Invalid status'}), 400

        try:
            attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid date format (use YYYY-MM-DD)'}), 400

        with db.Database.get_cursor() as cur:
            cur.execute(
                "SELECT name, batch_id FROM students WHERE id = %s AND deleted_at IS NULL",
                (student_id,)
            )
            student = cur.fetchone()
            if not student:
                return jsonify({'success': False, 'message': 'Student not found'}), 404
            student_name, batch_id = student

            cur.execute(
                "SELECT COUNT(*) FROM attendance WHERE student_id = %s AND DATE(timestamp) = %s",
                (student_id, attendance_date)
            )
            if cur.fetchone()[0] > 0:
                return jsonify({'success': False, 'message': f'Attendance already marked for {student_name} on {date_str}'}), 400

            timestamp = datetime.combine(attendance_date, datetime.min.time())  
            cur.execute(
                "INSERT INTO attendance (student_id, batch_id, timestamp, image_path) VALUES (%s, %s, %s, %s)",
                (student_id, batch_id, timestamp, "Attendance marked by " + session['info']['name'] if 'info' in session and 'name' in session['info'] else 'Unknown')  
            )

        flash(f'Attendance marked as {status} for {student_name}', 'success')
        return jsonify({'success': True, 'message': f'Attendance marked as {status} for {student_name}'}), 200

    except Exception as e:
        app.logger.error(f"Error marking attendance: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# attendance_left()
# Purpose: Renders the left panel of the attendance page for instructors/admins
# Parameters: None (uses session for user_id and role)
# Returns: Rendered 'attendance-left.html'
# Related: db.Student.get_student_courses_and_batches(), db.Instructor.get_instructor_data(), db.Admin.get_all_batches_courses_videos()
@app.route('/attendance-left')
@instructor_or_admin_required
def attendance_left():
    user_id = session['info']['id']
    user_role = session['info']['role']
    admin = user_role == 'admin'
    users = db.Auth.get_all_users()
    students, courses, batches = [], [], []

    if admin:
        students = []
        for user in users:
            if user['role'] == 'student':
                student_data, s_status = db.Student.get_student_courses_and_batches(user['id'])
                if s_status == 1:

                    batch_ids = {b['batch_id'] for c in student_data['courses'].values() for b in c['batches']}
                    students.append({
                        'id': user['id'],
                        'name': user['name'],
                        'username': user['username'],
                        'email': user['email'],
                        'batch_ids': list(batch_ids)
                    })
        data, status = db.Admin.get_all_batches_courses_videos()
        if status == 1:
            courses = data['courses']
            batches = data['batches']

    else:
        data, status = db.Instructor.get_instructor_data(user_id)
        if status != 1:
            return render_template('instructor/attendance-left.html', students=[], batches=[], courses=[], csrf_token=generate_csrf(), admin=admin)
        seen_courses = set()
        courses = [c for c in data['courses'] if not (c[0] in seen_courses or seen_courses.add(c[0]))]
        batches = list(set(data['batches']))
        instructor_batch_ids = {b[0] for b in batches}
        for user in users:
            if user['role'] == 'student':
                student_data, s_status = db.Student.get_student_courses_and_batches(user['id'])
                if s_status == 1:
                    batch_ids = {b['batch_id'] for c in student_data['courses'].values() for b in c['batches']}
                    if batch_ids & instructor_batch_ids:
                        students.append({
                            'id': user['id'], 
                            'name': user['name'], 
                            'username': user['username'], 
                            'email': user['email'], 
                            'batch_ids': list(batch_ids)
                        })

    return render_template('instructor/attendance-left.html', students=students, batches=batches, courses=courses, csrf_token=generate_csrf(), admin=admin)

# get_students()
# Purpose: Fetches students for a specific date, batch, or course
# Parameters: date, batch, course (query parameters)
# Returns: JSON response with list of students and attendance status
# Related: db.Instructor.get_instructor_data()
@app.route('/get-students', methods=['GET'])
@instructor_or_admin_required
def get_students():
    date_str = request.args.get('date')
    batch_id = request.args.get('batch')
    course_id = request.args.get('course')
    if not date_str:
        return jsonify({'success': False, 'message': 'Date required!'}), 400
    try:
        query_date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date format! Use YYYY-MM-DD'}), 400

    user_id = session['info']['id']
    user_role = session['info']['role']

    with db.Database.get_cursor() as cur:
        if user_role == 'admin':

            query = """
                SELECT DISTINCT s.id, s.username, s.name, s.email
                FROM students s
                INNER JOIN batches b ON s.batch_id = b.id
                WHERE s.deleted_at IS NULL
            """
            params = []
        else:

            data, status = db.Instructor.get_instructor_data(user_id)
            instructor_batch_ids = {b[0] for b in data['batches']} if status == 1 else set()
            if not instructor_batch_ids:
                return jsonify({'success': True, 'students': [], 'count': 0, 'date': date_str, 'batch_id': batch_id, 'course_id': course_id})

            query = """
                SELECT DISTINCT s.id, s.username, s.name, s.email
                FROM students s
                INNER JOIN batches b ON s.batch_id = b.id
                WHERE s.deleted_at IS NULL AND b.id IN %s
            """
            params = [tuple(instructor_batch_ids)]

        if batch_id:
            if batch_id != 'undefined': 
                query += " AND b.id = %s"
                params.append(batch_id)
        if course_id:
            if course_id != 'undefined': 
                query += " AND b.id IN (SELECT batch_id FROM batch_courses WHERE course_id = %s)"
                params.append(course_id)

        query += " ORDER BY s.name"
        cur.execute(query, params)
        all_students = cur.fetchall()

        students = []
        for student in all_students:
            student_id, username, name, email = student
            cur.execute("SELECT COUNT(*) FROM attendance WHERE student_id = %s AND DATE(timestamp) = %s", 
                       (str(student_id), query_date.date()))
            attended = cur.fetchone()[0] > 0
            students.append({'id': str(student_id), 'username': username, 'name': name, 'email': email, 'attended': attended})

        return jsonify({
            'success': True, 
            'students': students, 
            'count': len(students), 
            'date': date_str, 
            'batch_id': batch_id, 
            'course_id': course_id
        })

recognition_lock = Lock()

# verify()
# Purpose: Verifies a student's QR code and redirects to face verification
# Parameters: student_id (URL parameter with HMAC)
# Returns: Redirect to verify_face() or JSON error
# Related: verify_face()
@app.route('/verify/student/<student_id>', methods=['GET'])
@student_or_instructor_or_admin_required
def verify(student_id):
    """Verify student QR code and redirect to face verification if valid."""

    student_id, hmac_code = student_id[:36], student_id[36:]
    secret_key = "QgZJ#fp3CbG5xxgZj[(h,#p;IOzjm-1LW%BtC+&9}t}r@]Ri2b"
    date = datetime.now().strftime("%Y%m%d")
    data = f"{student_id}-{date}"
    hmac_obj = hmac.new(
        secret_key.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    )
    expected_hmac = hmac_obj.hexdigest()[:16]  

    if hmac_code == expected_hmac:

        return redirect(url_for('verify_face', student_id=student_id))
    else:
        return jsonify({'success': False, 'message': 'Invalid QR code!'}), 400

# upload_student_image()
# Purpose: Uploads and processes a student's profile image for face recognition
# Parameters: None (uses request.files for image, request.form for student_id)
# Returns: Redirect to dashboard or rendered 'upload_image.html'
# Related: verify_face()
@app.route('/upload-student-image', methods=['GET', 'POST'])
@instructor_or_admin_required
def upload_student_image():
    role = check_session_and_role()

    if request.method == 'POST':

        student_id = request.form.get('student_id') if role in ['instructor', 'admin'] else session['info']['id']
        if not student_id:
            flash('Student ID required!', 'danger')
            return redirect(url_for('dashboard'))

        student_data, status = db.Student.get_student(student_id)
        if status != 1:
            flash('Student not found!', 'danger')
            return redirect(url_for('dashboard'))

        if 'image' not in request.files or request.files['image'].filename == '':
            flash('No image provided, dude!', 'danger')
            return redirect(request.url)

        image = request.files['image']
        filename = secure_filename(f"{student_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
        temp_image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(temp_image_path)

        with recognition_lock:
            img = face_recognition.load_image_file(temp_image_path)
            embeddings = face_recognition.face_encodings(img)

        if not embeddings:
            os.remove(temp_image_path)
            flash('No face detected!', 'danger')
            return redirect(request.url)

        embedding_json = json.dumps(embeddings[0].tolist())  

        try:
            with db.Database.get_cursor() as cur:
                cur.execute(
                    "UPDATE students SET profile_picture = %s, face_embedding = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (filename, embedding_json, student_id)
                )
            flash('Image uploaded and face data saved successfully!', 'success')
        except Exception as e:
            flash(f'Error saving image, dude: {str(e)}', 'danger')
        finally:
            os.remove(temp_image_path)  

        return redirect(url_for('dashboard') + '#attendance')

    student_id = request.args.get('student_id') if role in ['instructor', 'admin'] else session['info']['id']
    return render_template('student/upload_image.html', student_id=student_id, csrf_token=generate_csrf())

# verify_face()
# Purpose: Verifies a student's face for attendance using face recognition
# Parameters: student_id (URL parameter)
# Returns: Rendered 'verify-face.html' for GET, JSON response for POST
# Related: verify(), upload_student_image()
@app.route('/verify/student/<student_id>/_verify.edupresence', methods=['GET', 'POST'])
@csrf.exempt
@student_or_instructor_or_admin_required
def verify_face(student_id):
    user_id = session['info']['id']
    if user_id != student_id:
        return jsonify({'success': False, 'message': 'ID mismatch. Please log in with the correct one!'}), 404
    student_data, status = db.Student.get_student(student_id)
    if status != 1:
        return jsonify({'success': False, 'message': 'Student not found!'}), 404
    student = student_data

    if request.method == 'POST':
        with db.Database.get_cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) 
                FROM attendance 
                WHERE student_id = %s AND DATE(timestamp) = DATE(CURRENT_TIMESTAMP)
            """, (student_id,))
            if cur.fetchone()[0] > 0:
                return jsonify({'success': False, 'message': 'Attendance already marked for today!'}), 400

            cur.execute("SELECT batch_id FROM students WHERE id = %s", (student_id,))
            batch_id = cur.fetchone()[0]

        try:
            image_data = request.json['image'].split(',')[1]
            image_bytes = base64.b64decode(image_data)
        except (KeyError, IndexError, ValueError):
            return jsonify({'success': False, 'message': 'Invalid image data!'}), 400

        temp_image_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{student_id}_verify.jpg')
        with open(temp_image_path, 'wb') as f:
            f.write(image_bytes)

        with recognition_lock:
            img = face_recognition.load_image_file(temp_image_path)
            embeddings = face_recognition.face_encodings(img)

        if not embeddings:
            os.remove(temp_image_path)
            return jsonify({'success': False, 'message': 'No face detected!'})

        new_embedding = embeddings[0]
        stored_embedding_json = student[-4]
        if not stored_embedding_json:
            os.remove(temp_image_path)
            return jsonify({'success': False, 'message': 'No stored face data for this student'})

        stored_embedding = np.array(json.loads(stored_embedding_json))
        match = face_recognition.compare_faces([stored_embedding], new_embedding, tolerance=0.6)[0]

        if match:
            student_folder = os.path.join(app.config['ATTENDANCE_FOLDER'], str(student_id))
            os.makedirs(student_folder, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            attendance_image_path = os.path.join(student_folder, f'attendance_{timestamp}.jpg')
            os.rename(temp_image_path, attendance_image_path)

            try:
                with db.Database.get_cursor() as cur:
                    cur.execute(
                        "INSERT INTO attendance (student_id, batch_id, timestamp, image_path) VALUES (%s, %s, %s, %s)",
                        (student_id, batch_id, datetime.now(), attendance_image_path)
                    )
            except db.DatabaseError as e:
                return jsonify({'success': False, 'message': f'Failed to record attendance: {str(e)}'}), 500

            return jsonify({
                'success': True,
                'name': student[2],
                'email': student[3]
            })
        else:
            os.remove(temp_image_path)
            return jsonify({'success': False, 'message': 'Face does not match!'})

    student_dict = {
        'id': student[0],
        'username': student[1],
        'name': student[2],
        'email': student[3],
    }
    return render_template('instructor/verify-face.html', student=student_dict, csrf_token=generate_csrf())

# get_attendance_calendar()
# Purpose: Fetches attendance calendar data for a student's batch
# Parameters: None (uses session for student_id)
# Returns: JSON response with class and attended dates
# Related: None
@app.route('/get_attendance_calendar', methods=['GET'])
@student_required
def get_attendance_calendar():
    """Fetch attendance calendar data for the logged-in student's batch."""
    student_id = session['info']['id']

    try:
        with db.Database.get_cursor() as cur:

            cur.execute("SELECT batch_id FROM students WHERE id = %s AND deleted_at IS NULL", (student_id,))
            result = cur.fetchone()
            if not result:
                return jsonify({'success': False, 'message': 'Student batch not found!'}), 404
            batch_id = result[0]

            cur.execute("""
                SELECT DISTINCT DATE(timestamp) 
                FROM attendance 
                WHERE batch_id = %s
                ORDER BY DATE(timestamp)
            """, (batch_id,))
            class_dates = [row[0].isoformat() for row in cur.fetchall()]

            cur.execute("""
                SELECT DISTINCT DATE(timestamp) 
                FROM attendance 
                WHERE student_id = %s
                ORDER BY DATE(timestamp)
            """, (student_id,))
            attended_dates = set(row[0].isoformat() for row in cur.fetchall())

            events = []
            for date in class_dates:
                events.append({
                    'date': date,
                    'attended': date in attended_dates
                })

        return jsonify({
            'success': True,
            'events': events
        })
    except Exception as e:
        app.logger.error(f"Error fetching attendance calendar: {str(e)}")
        return jsonify({'success': False, 'message': 'Error fetching calendar data'}), 500

# generate_qr()
# Purpose: Generates a QR code link for student verification
# Parameters: student_id (URL parameter)
# Returns: JSON response with student_id and HMAC code
# Related: verify()
@app.route('/qr/<student_id>')
@student_or_instructor_or_admin_required
def generate_qr(student_id):

    student_data, status = db.Student.get_student(student_id)
    if status != 1:
        flash('Student not found!', 'danger')
        return redirect(url_for('dashboard'))

    student = student_data

    if session['info']['role'] == 'student':
        if session['info']['id'] == student_id:
            pass
        else:
            flash('Student not found!', 'danger')
            return redirect(url_for('dashboard'))

    secret_key = "QgZJ#fp3CbG5xxgZj[(h,#p;IOzjm-1LW%BtC+&9}t}r@]Ri2b"
    date = datetime.now().strftime("%Y%m%d")
    data = f"{student_id}-{date}"

    hmac_obj = hmac.new(
        secret_key.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    )
    hmac_code = hmac_obj.hexdigest()
    short_hmac_code = hmac_code[:16]  

    return {
        "student_id": student_id,
        "hmac_code": hmac_code[:16],  

    }

# admin_users()
# Purpose: Displays all users for admin management
# Parameters: None
# Returns: Rendered 'admin_users.html' or JSON response for AJAX
# Related: db.Auth.get_all_users()
@app.route('/admin/users', methods=['GET'])
@admin_required
def admin_users():
    users = db.Auth.get_all_users()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'users': users})
    return render_template('admin/admin_users.html', users=users, csrf_token=generate_csrf())

# verify_enrollments()
# Purpose: Allows admins to verify pending enrollments
# Parameters: None (uses request.form for enrollment_id)
# Returns: Rendered 'verify_enrollments.html' for GET, JSON response for POST
# Related: db.Admin.verify_enrollment()
@app.route('/admin/verify-enrollments', methods=['GET', 'POST'])
@admin_required
def verify_enrollments():
    if request.method == 'POST':
        enrollment_id = request.form.get('enrollment_id')
        if not enrollment_id:
            return jsonify({'success': False, 'message': 'Enrollment ID required!'}), 400
        result, status = db.Admin.verify_enrollment(enrollment_id)
        return jsonify({'success': status == 1, 'message': result})

    try:
        with db.Database.get_cursor() as cur:
            cur.execute("SELECT id, username, name, email, phone, enrollment_id, status FROM enrollments WHERE status = 'pending' AND deleted_at IS NULL")
            pending = cur.fetchall()
        enrollments = [{'id': str(row[0]), 'username': row[1], 'name': row[2], 'email': row[3], 'phone': row[4], 'enrollment_id': row[5], 'status': row[6]} for row in pending]
        return render_template('admin/verify_enrollments.html', enrollments=enrollments, csrf_token=generate_csrf())
    except Exception as e:
        flash(f'Error fetching enrollments: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

# add_user()
# Purpose: Adds a new user (student, instructor, or admin)
# Parameters: None (uses request.json for data)
# Returns: JSON response indicating success or failure
# Related: db.Enrollment.register_user(), db.Instructor.add_instructor(), db.Admin.add_admin()
@app.route('/admin/add-user', methods=['POST'])
@admin_required
def add_user():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    role = data.get('role')
    if not all([username, email, role]):
        return jsonify({'success': False, 'message': 'Missing fields!'}), 400

    if role == 'student':
        result, status = db.Enrollment.register_user(username, "New User", email, "00000000000", f"ENR-{username}", "defaultpass")
    elif role == 'instructor':
        result, status = db.Instructor.add_instructor(username, "New Instructor", email, "00000000000", "defaultpass", None)
    elif role == 'admin':
        result, status = db.Admin.add_admin("00000000000", username, "New Admin", email, "defaultpass")
    else:
        return jsonify({'success': False, 'message': 'Invalid role, dude!'}), 400

    return jsonify({'success': status == 1, 'message': result})

# admin_update_user()
# Purpose: Updates a user's role
# Parameters: None (uses request.form for user_id and role)
# Returns: JSON response indicating success or failure
# Related: db.Auth.update_user_role()
@app.route('/admin/update-user', methods=['POST'])
@admin_required
def admin_update_user():
    data = request.form
    user_id = data.get('user_id')
    new_role = data.get('role')
    success, message = db.Auth.update_user_role(user_id, new_role)
    return jsonify({'success': success, 'message': message})

# admin_delete_user()
# Purpose: Deletes a user
# Parameters: None (uses request.form for user_id)
# Returns: JSON response indicating success or failure
# Related: db.Auth.delete_user()
@app.route('/admin/delete-user', methods=['POST'])
@admin_required
def admin_delete_user():
    user_id = request.form.get('user_id')
    success = db.Auth.delete_user(user_id)
    return jsonify({'success': success, 'message': 'User deleted!' if success else 'Delete failed!'})

# admin_update_user_field()
# Purpose: Updates a specific field (username or email) for a user
# Parameters: None (uses request.form for user_id, field, value)
# Returns: JSON response indicating success or failure
# Related: None
@app.route('/admin/update-user-field', methods=['POST'])
@admin_required
def admin_update_user_field():
    user_id = request.form.get('user_id')
    field = request.form.get('field')
    value = request.form.get('value')
    with db.Database.get_cursor() as cur:
        cur.execute("SELECT role FROM students WHERE id = %s AND deleted_at IS NULL UNION SELECT role FROM instructors WHERE id = %s AND deleted_at IS NULL UNION SELECT role FROM admins WHERE id = %s AND deleted_at IS NULL", 
                    (user_id, user_id, user_id))
        current_role = cur.fetchone()
        if not current_role:
            return jsonify({'success': False, 'message': 'User not found!'}), 404
        table = {'student': 'students', 'instructor': 'instructors', 'admin': 'admins'}[current_role[0]]
        if field in ['username', 'email']:
            cur.execute(f"UPDATE {table} SET {field} = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (value, user_id))
            return jsonify({'success': True, 'message': f'{field.capitalize()} updated!'})
        return jsonify({'success': False, 'message': 'Invalid field, dude!'}), 400

# class_video()
# Purpose: Displays a specific video page
# Parameters: id (query parameter)
# Returns: Rendered 'class-video.html' or 404
# Related: db.Video.get_video()
@app.route('/class-video')
@student_or_instructor_or_admin_required
def class_video():
    video_data, status = db.Video.get_video(request.args.get('id'))
    if status != 1:
        return 'Video not found!', 404
    video = list(video_data)
    video[9] = timeago.time_ago(video[9])
    return render_template('student/class-video.html', id=request.args.get('id'), video=tuple(video))

# render_page()
# Purpose: Renders specific student pages (batches, live-chat, class)
# Parameters: page (URL parameter)
# Returns: Rendered template or 404
# Related: None
@app.route('/<page>')
@student_or_instructor_or_admin_required
def render_page(page):
    valid_pages = {'batches', 'live-chat', 'class'}
    if page in valid_pages:
        return render_template(f'student/{page}.html')
    return 'Page not found!', 404

JITSI_MEET_BASE_URL = "https://meet.jit.si"

# generate_jitsi_link()
# Purpose: Generates a Jitsi Meet link for a live class
# Parameters: class_id, title
# Returns: Jitsi Meet URL string
# Related: create_live_class()
def generate_jitsi_link(class_id, title):
    time_str = datetime.now().strftime("%Y%m%d%H%M")
    random_digits = f"{random.randint(0, 9999999):07d}"  
    secret_key = b"p3j!;;qxtiVNt9]"
    hmac_obj = hmac.new(secret_key, title.encode('utf-8'), hashlib.sha256)
    title_hash = hmac_obj.hexdigest()[:7]
    room_name = f"{class_id}_{title}_{time_str}_{random_digits}"
    return f"{JITSI_MEET_BASE_URL}/{room_name}"

# create_live_class()
# Purpose: Creates a new live class and generates a Jitsi link
# Parameters: None (uses request.form for data)
# Returns: Rendered 'create_live_class.html' for GET, JSON response for POST
# Related: generate_jitsi_link(), db.LiveClass.create_live_class()
@app.route('/instructor/create-live-class', methods=['GET', 'POST'])
@instructor_required
def create_live_class():
    instructor_id = session['info']['id']

    if request.method == 'POST':
        data = request.form
        batch_id = data.get('batch_id')
        course_id = data.get('course_id')
        title = data.get('title')
        description = data.get('description')
        scheduled_at = data.get('scheduled_at')

        if not all([batch_id, course_id, title, scheduled_at]):
            return jsonify({'success': False, 'message': 'Missing required fields!'}), 400

        try:
            scheduled_at_dt = datetime.strptime(scheduled_at, '%Y-%m-%dT%H:%M')
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid date format! Use YYYY-MM-DDTHH:MM'}), 400

        class_id, status = db.LiveClass.create_live_class(
            batch_id, course_id, instructor_id, title, description, scheduled_at_dt, "temp_link"
        )
        if status != 1:
            return jsonify({'success': False, 'message': class_id}), 500

        jitsi_link = generate_jitsi_link(class_id, title)
        with db.Database.get_cursor() as cur:
            cur.execute("UPDATE live_classes SET jitsi_link = %s WHERE id = %s", (jitsi_link, class_id))

        flash('Live class created successfully!', 'success')
        return jsonify({'success': True, 'message': 'Live class created!', 'jitsi_link': jitsi_link}), 200

    data, status = db.Instructor.get_instructor_data(instructor_id)
    if status != 1:
        flash('Error fetching data!', 'danger')
        return redirect(url_for('dashboard'))

    return render_template(
        'instructor/create_live_class.html',
        batches=data['batches'],
        courses=data['courses'],
        csrf_token=generate_csrf()
    )

# delete_live_class()
# Purpose: Deletes a live class
# Parameters: None (uses request.form for class_id)
# Returns: JSON response indicating success or failure
# Related: db.LiveClass.delete_live_class()
@app.route('/instructor/delete-live-class', methods=['POST'])
@instructor_required
def delete_live_class():
    instructor_id = session['info']['id']
    class_id = request.form.get('class_id')
    if not class_id:
        return jsonify({'success': False, 'message': 'Class ID required!'}), 400

    result, status = db.LiveClass.delete_live_class(class_id, instructor_id)
    if status == 1:
        flash('Live class deleted successfully!', 'success')
        return jsonify({'success': True, 'message': result}), 200
    else:
        return jsonify({'success': False, 'message': result}), 400

# instructor_live_classes()
# Purpose: Displays live classes for an instructor
# Parameters: None (uses session for instructor_id)
# Returns: Rendered 'live_classes.html' with upcoming and ongoing classes
# Related: db.LiveClass.get_live_classes_for_instructor()
@app.route('/instructor/live-classes', methods=['GET'])
@instructor_required
def instructor_live_classes():
    instructor_id = session['info']['id']
    live_classes, status = db.LiveClass.get_live_classes_for_instructor(instructor_id)
    if status != 1:
        flash('Error fetching live classes!', 'danger')
        live_classes = []

    now = datetime.now()
    upcoming = []
    ongoing = []
    for lc in live_classes:
        scheduled_at = lc[5]
        expired_at = lc[7]
        if now >= expired_at:
            continue  
        if scheduled_at > now:
            upcoming.append(lc)
        else:
            ongoing.append(lc)

    return render_template(
        'instructor/live_classes.html',
        upcoming=upcoming,
        ongoing=ongoing,
        csrf_token=generate_csrf()
    )

# student_live_classes()
# Purpose: Displays live classes for a student's batch
# Parameters: None (uses session for student_id)
# Returns: Rendered 'live_classes.html' with upcoming and ongoing classes
# Related: db.Student.get_student_data(), db.LiveClass.get_live_classes_for_batch()
@app.route('/student/live-classes', methods=['GET'])
@student_required
def student_live_classes():
    student_id = session['info']['id']
    student_data, status = db.Student.get_student_data(student_id)
    if status != 1:
        flash('Error fetching student data!', 'danger')
        return redirect(url_for('dashboard'))

    batch_id = student_data['batches'][0][0]
    if not batch_id:
        flash('No batch assigned!', 'danger')
        return redirect(url_for('dashboard'))

    live_classes, status = db.LiveClass.get_live_classes_for_batch(batch_id)

    if status != 1:
        flash('Error fetching live classes!', 'danger')
        live_classes = []

    now = datetime.now()
    upcoming = []
    ongoing = []
    for lc in live_classes:
        scheduled_at = lc[5]
        expired_at = lc[7]
        if now >= expired_at:
            continue  
        if scheduled_at > now:
            upcoming.append(lc)
        else:
            ongoing.append(lc)

    return render_template(
        'student/live_classes.html',
        upcoming=upcoming,
        ongoing=ongoing,
        csrf_token=generate_csrf()
    )

# join_live_class()
# Purpose: Redirects to the Jitsi Meet link for a live class
# Parameters: class_id (URL parameter)
# Returns: Redirect to Jitsi link or dashboard on error
# Related: None
@app.route('/join-live-class/<class_id>')
@student_or_instructor_or_admin_required
def join_live_class(class_id):
    with db.Database.get_cursor() as cur:
        cur.execute("""
            SELECT jitsi_link, scheduled_at, expired_at 
            FROM live_classes 
            WHERE id = %s AND deleted_at IS NULL
        """, (class_id,))
        result = cur.fetchone()
        if not result:
            flash('Live class not found!', 'danger')
            return redirect(url_for('dashboard'))
        jitsi_link, scheduled_at, expired_at = result

        now = datetime.now()
        if now >= expired_at:
            flash('This live class has expired!', 'danger')
            return redirect(url_for('dashboard'))

    return redirect(jitsi_link)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2910, debug=True)