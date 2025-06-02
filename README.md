# EduPresence

EduPresence is a next-generation learning management system (LMS) designed to streamline attendance tracking, course management, and student engagement in educational settings. Built as a Flask-based web application, it integrates advanced features like face recognition for attendance, QR code verification, live classes via Jitsi Meet, and secure authentication with Google OAuth. EduPresence aims to enhance learning efficiency with a secure, scalable, and user-friendly platform.

## Features

- **Secure Authentication**: Supports login via username/password and Google OAuth for students, instructors, and admins.
- **Role-Based Access Control (RBAC)**: Restricts endpoints to specific roles (student, instructor, admin) with session validation.
- **Attendance Tracking**:
  - Automated attendance using face recognition (`face_recognition` library).
  - QR code verification for secure attendance logging (stored in `static/qr_codes/`).
  - Manual attendance marking by instructors/admins.
- **Course Management**: Enables instructors/admins to create, update, and delete courses and videos.
- **Live Classes**: Integrates Jitsi Meet for scheduling and joining virtual classes with expiration tracking.
- **Performance Tracking**: Tracks attendance and class participation for data-driven insights.
- **User Interface**: Responsive design using Flask templates (`Jinja2`), with role-specific dashboards for students, instructors, and admins.
- **Database**: Uses PostgreSQL for robust data management, with support for soft deletion and foreign key constraints.
- **Security**:
  - CSRF protection with `Flask-WTF`.
  - Secure session management with `Flask-Session`.
  - Parameterized queries to prevent SQL injection.

## Prerequisites

Before setting up EduPresence, ensure you have the following installed:

- **Python**: Version 3.13 (as specified in the project requirements).
- **PostgreSQL**: Version 16 or later for database management.
- **Git**: For cloning the repository.
- **Web Browser**: Google Chrome (v136 or later recommended) for testing.
- **Operating System**:
  - Development: macOS Ventura (v13.6 or later) or equivalent.
  - Production: Ubuntu 22.04 LTS recommended.

### Hardware Requirements

- **Development**:
  - MacBook Pro (M2 Pro, 16GB RAM, 512GB SSD) or equivalent.
- **Production**:
  - Minimum: 4-core CPU, 8GB RAM, 100GB SSD.
  - Recommended: 8-core CPU, 16GB RAM, 200GB SSD.

## Installation

Follow these steps to set up EduPresence on your local machine:

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/aghasyedi/EduPresence.git
   cd EduPresence
   ```

2. **Set Up a Virtual Environment**:

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   The project dependencies are listed in `requirements.txt`. Install them using:

   ```bash
   pip install -r requirements.txt
   ```

   **Note**: `face_recognition` requires `dlib`, which may need additional setup on some systems:

   - On macOS/Linux, ensure you have `cmake` and `libopenblas` installed:
     ```bash
     brew install cmake  # On macOS
     sudo apt-get install build-essential cmake libopenblas-dev  # On Ubuntu
     ```
   - On Windows, you may need to install Visual Studio Build Tools and `cmake`.

4. **Set Up PostgreSQL Database**:

   - Install PostgreSQL if not already installed.
   - Create a database for EduPresence:
     ```sql
     CREATE DATABASE edupresence;
     ```
   - Configure the database connection in a `.env` file (see Environment Variables below).
   - Initialize the database schema by running the SQL scripts in the `database` folder (if provided) or creating the necessary tables manually:
     ```sql
     CREATE TABLE users (
         id SERIAL PRIMARY KEY,
         username VARCHAR(255) NOT NULL,
         email VARCHAR(255) NOT NULL,
         role VARCHAR(50) NOT NULL,
         password VARCHAR(255),
         google_id VARCHAR(255),
         profile_picture VARCHAR(255),
         face_embedding TEXT,
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         deleted_at TIMESTAMP
     );
     -- Add other tables to DB: students, instructors, admins, courses, videos, attendance, live_classes, etc.
     ```

5. **Set Up Environment Variables**:
   Create a `.env` file in the project root and add the following variables:
   ```env
   APP_SECRET_KEY=your-secret-key
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   SERVER_METADATA_URL=https://accounts.google.com/.well-known/openid-configuration
   DATABASE_URL=postgresql://username:password@localhost:5432/edupresence
   ```
   - Replace `your-secret-key` with a secure random string.
   - Obtain `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from the Google Cloud Console.
   - Update `DATABASE_URL` with your PostgreSQL credentials.

## Running the Application

1. **Activate the Virtual Environment** (if not already activated):

   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Run the Flask Application**:

   ```bash
   python app.py
   ```

   The app will start on `http://localhost:2910` by default (as specified in `app.py`).

3. **Access the Application**:
   - Open your browser and navigate to `http://localhost:2910`.
   - The landing page (`/`) renders `index.html`, providing an overview of EduPresence.
   - Navigate to `/login` to log in or register a new user.

## Usage

### Login and Registration

- **Login**: Access `/login` to log in with a username/password or Google OAuth.
- **Google OAuth**: Click "Login with Google" to authenticate using a Google account.
- **Registration**: New users can register at `/register`. Admins/instructors must verify enrollments before students can access the platform.

### Role-Specific Features

- **Students**:
  - View courses and videos on the dashboard (`/dashboard`).
  - Join live classes (`/student/live-classes`) via Jitsi Meet links.
  - Mark attendance using face recognition or QR codes (`/attendance`).
- **Instructors**:
  - Manage courses and videos (`/manage-classes`).
  - Create live classes (`/instructor/create-live-class`).
  - Verify student registrations (`/instructor/registrations`) and mark attendance (`/attendance`).
- **Admins**:
  - Manage users (`/admin/users`), verify enrollments (`/admin/verify-enrollments`), and update student batches (`/instructor/students`).
  - Full access to all courses, videos, and live classes.

### Attendance Tracking

- **Face Recognition**: Students can mark attendance by uploading a photo (`/verify/student/<student_id>/_verify.edupresence`).
- **QR Code**: Generate a QR code (`/qr/<student_id>`) for verification, then scan to redirect to face verification.
- **Manual Marking**: Instructors/admins can manually mark attendance (`/mark-attendance`).

### Live Classes

- Create a live class (`/instructor/create-live-class`) to generate a Jitsi Meet link.
- Students and instructors can join live classes (`/join-live-class/<class_id>`) before the expiration time.

## Project Structure

```
EduPresence/
├── app.py                          # Main Flask application
├── db.py                           # Database connection and query utilities
├── flask_session/                  # Server-side session storage
│   ├── 0a5410d6c9c97cad51c5c7119f6f38c1
│   └── 0cbd5c27a657e760bb4a4f93de4d891a
├── project_tree.txt                # Generated project tree (can be removed)
├── README.markdown                 # Project documentation (Markdown format)
├── Readme.md                       # Alternative README file (can be consolidated)
├── requirements.txt                # Project dependencies
├── static/                         # Static files (CSS, JS, images)
│   ├── admin/                      # Admin-specific static assets
│   │   ├── css/
│   │   │   └── admin_users.css
│   │   └── js/
│   │       └── admin_users.js
│   ├── attendance/                 # Attendance images
│   │   └── 5a8d4884-5e08-4dd8-8ed8-4e1d128df445/
│   ├── attendance_images/          # Additional attendance image storage
│   ├── css/                        # General CSS files
│   │   ├── dashboard.css
│   │   ├── index.css
│   │   └── login.css
│   ├── dashboard/                  # Dashboard-related static files
│   │   └── right-content.html
│   ├── default-avatar.png          # Default avatar image
│   ├── default.jpg                 # Default image
│   ├── instructor/                 # Instructor-specific static assets
│   │   ├── css/
│   │   │   ├── edit-course-video.css
│   │   │   ├── home.css
│   │   │   └── manage-class-cards.css
│   │   ├── js/
│   │   │   ├── attendance.js
│   │   │   ├── edit-course-video.js
│   │   │   ├── home.js
│   │   │   ├── manage-class-cards.js
│   │   │   └── manage-classes.js
│   │   └── student/                # Nested student-specific assets
│   │       └── js/
│   │           └── attendance.js
│   ├── js/                         # General JavaScript files
│   │   ├── script.js
│   │   └── service-worker.js
│   ├── logo_dark.png               # Dark theme logo
│   ├── logo_full.png               # Full logo
│   ├── logo.png                    # Standard logo
│   ├── logo.svg                    # SVG logo
│   ├── profile/                    # Profile images
│   │   └── student/
│   ├── qr_codes/                   # Generated QR codes for attendance
│   │   ├── 1.png
│   │   ├── 2.png
│   │   └── 5043a51c-e438-4984-844a-7c9cd2032254.png
│   └── uploads/                    # Uploaded images (e.g., profile pictures)
│       └── 5a8d4884-5e08-4dd8-8ed8-4e1d128df445_20250311_143322.jpg
├── templates/                      # HTML templates (Jinja2)
│   ├── admin/                      # Admin-specific templates
│   │   ├── admin_students.html
│   │   ├── admin_users copy.html
│   │   └── admin_users.html
│   ├── admin_dashboard.html        # Admin dashboard template
│   ├── index.html                  # Landing page
│   ├── instructor/                 # Instructor-specific templates
│   │   ├── attendance-left.html
│   │   ├── attendance.html
│   │   ├── course-videos.html
│   │   ├── create_live_class.html
│   │   ├── edit-course-video.html
│   │   ├── home.html
│   │   ├── instructor_registrations.html
│   │   ├── live_classes.html
│   │   ├── manage-class-cards.html
│   │   ├── manage-classes.html
│   │   ├── verify-face.html
│   │   └── verify-qr-scanner.html
│   ├── instructor_dashboard.html   # Instructor dashboard template
│   ├── login.html                  # Login/registration page
│   ├── student/                    # Student-specific templates
│   │   ├── attendance.html
│   │   ├── batches-cards.html
│   │   ├── batches.html
│   │   ├── class-video.html
│   │   ├── class.html
│   │   ├── course-videos.html
│   │   ├── course.html
│   │   ├── home.html
│   │   ├── live_classes.html
│   │   └── live-chat.html
│   └── student_dashboard.html      # Student dashboard template
├── timeago.py                      # Time formatting utility
└── uploads/                        # Additional uploads directory
    └── young-bearded-man-with-striped-shirt_273609-5677.avif
```

## Dependencies

Key dependencies include:

- `Flask==3.1.0`: Web framework for building the application.
- `Flask-WTF==1.2.2`: For CSRF protection and form handling.
- `Flask-Session==0.8.0`: For server-side session management.
- `face_recognition==1.3.0`: For facial recognition-based attendance.
- `psycopg2-binary==2.9.10`: PostgreSQL database adapter.
- `Authlib==1.5.1`: For Google OAuth integration.
- `qrcode==8.0` and `pyzbar==0.1.9`: For QR code generation and scanning.
- See `requirements.txt` for the full list.

## Security Features

- **CSRF Protection**: Enabled globally with `Flask-WTF` to secure form submissions.
- **Session Management**: Uses `Flask-Session` with a 3-hour lifetime, stored in `flask_session/`.
- **File Upload Security**: Limits upload size to 16MB and uses `secure_filename` to prevent path traversal.
- **Database Security**: Uses parameterized queries to prevent SQL injection.
- **Authentication Security**: Implements Google OAuth and HMAC for QR code verification.

## Troubleshooting

- **Face Recognition Issues**:
  - Ensure `dlib` and `face_recognition` are installed correctly (see Installation).
  - Verify that uploaded images contain a detectable face.
- **Database Connection Errors**:
  - Check the `DATABASE_URL` in `.env` and ensure PostgreSQL is running.
  - Verify the database schema matches the expected tables.
- **Google OAuth Errors**:
  - Confirm `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are correct.
  - Ensure the redirect URI (`/login/callback`) is registered in Google Cloud Console.
- **Jitsi Meet Issues**:
  - Ensure a stable internet connection for live classes.
  - Verify the Jitsi Meet link hasn’t expired.

## Future Improvements

- **Mobile App**: Develop iOS/Android apps for better accessibility.
- **AI Integration**: Add AI-driven analytics for personalized learning insights.
- **Cloud Hosting**: Transition to AWS with connection pooling for scalability.
- **Security Enhancements**: Implement password hashing (`bcrypt`) and multi-factor authentication.

## Snapshots
[EduPresence Snapshots.pdf](https://github.com/user-attachments/files/20544267/EduPresence.Snapshots.pdf)

## Contributors

- **Agha Tasheer Syedi**: Lead Developer [aghasyedi@gmail.com]
