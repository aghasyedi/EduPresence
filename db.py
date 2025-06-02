from datetime import timedelta
import psycopg2, os
from contextlib import contextmanager

from datetime import datetime, timedelta

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access environment variables
DBhostname = os.getenv('DB_HOSTNAME')
DBdatabase = os.getenv('DB_DATABASE')
DBusername = os.getenv('DB_USERNAME')
DBpassword = os.getenv('DB_PASSWORD')
DBport_id = os.getenv('DB_PORT')


class Database:
    # Database.connect_db()
    # Purpose: Establishes a connection to the PostgreSQL database.
    # Parameters: None
    # Returns: A psycopg2 connection object
    # Detailed Explanation:
    #   - This function is a static method of the Database class, meaning it can be called without creating an instance of Database.
    #   - It uses predefined constants (DBhostname, DBdatabase, DBusername, DBpassword, DBport_id) to connect to a PostgreSQL database running on localhost (127.0.0.1) with the database name 'student'.
    #   - The psycopg2.connect() method creates a connection to the database using these credentials.
    #   - If the connection fails (e.g., wrong password or database not found), it raises an exception that must be handled by the caller.
    #   - This function is used by other methods (like get_cursor()) to interact with the database.
    # Related: get_cursor()
    @staticmethod
    def connect_db():
        """Establishes and returns a database connection."""
        return psycopg2.connect(
            host=DBhostname,
            dbname=DBdatabase,
            user=DBusername,
            password=DBpassword,
            port=DBport_id
        )
    
    # Database.get_cursor()
    # Purpose: Provides a context manager for database cursors to execute queries safely.
    # Parameters: None
    # Returns: Yields a psycopg2 cursor object; manages connection and transaction
    # Detailed Explanation:
    #   - This is a static method decorated with @contextmanager, allowing it to be used in a 'with' statement for safe resource management.
    #   - It calls Database.connect_db() to get a database connection.
    #   - Creates a cursor (cur) from the connection, which is used to execute SQL queries.
    #   - The 'try' block yields the cursor to the caller, allowing them to run queries.
    #   - If the queries succeed, the transaction is committed (conn.commit()).
    #   - If an exception occurs, the transaction is rolled back (conn.rollback()) to prevent partial changes.
    #   - The 'finally' block ensures the cursor and connection are closed, preventing resource leaks.
    #   - Example usage: 'with Database.get_cursor() as cur: cur.execute(query)'.
    # Related: connect_db(), used by all database-interacting methods (e.g., create_tables(), Student.register_student())
    @staticmethod
    @contextmanager
    def get_cursor():

        conn = Database.connect_db()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cur.close()
            conn.close()

    # Database.create_tables()
    # Purpose: Creates all necessary database tables if they don't already exist.
    # Parameters: None
    # Returns: None
    # Detailed Explanation:
    #   - This static method defines a list of SQL queries to create tables for instructors, courses, batches, batch_courses, enrollments, students, admins, videos, student_progress, and attendance.
    #   - Each query uses 'CREATE TABLE IF NOT EXISTS' to avoid errors if tables already exist.
    #   - Tables include primary keys (mostly UUIDs), foreign keys (e.g., course.instructor_id references instructors.id), and constraints (e.g., unique usernames, phone number format).
    #   - Uses Database.get_cursor() to get a cursor and execute each query in a loop.
    #   - If any query fails, an exception is raised, and the transaction is rolled back (handled by get_cursor()).
    #   - This is typically called during application setup to initialize the database schema.
    # Related: get_cursor()
    @staticmethod
    def create_tables():
        queries = [

            """
            CREATE TABLE IF NOT EXISTS instructors (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                username VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                phone VARCHAR(15) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                profile_picture TEXT,
                role VARCHAR(20) DEFAULT 'instructor',
                status VARCHAR(10) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS courses (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                course_name VARCHAR(255) UNIQUE NOT NULL,
                instructor_id UUID NOT NULL,
                description TEXT,
                status VARCHAR(20) DEFAULT 'active',
                category VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL,
                FOREIGN KEY (instructor_id) REFERENCES instructors(id) ON DELETE SET NULL
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS batches (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                batch_name VARCHAR(255) UNIQUE NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS batch_courses (
                batch_id UUID NOT NULL,
                course_id UUID NOT NULL,
                order_num INT,
                PRIMARY KEY (batch_id, course_id),
                FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS enrollments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                username VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                phone VARCHAR(15) UNIQUE NOT NULL CHECK (phone ~ '^[0-9]+$'),
                enrollment_id VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(100) NOT NULL,
                profile_picture TEXT,
                face_embedding TEXT,  -- New column for face embedding
                status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'verified', 'rejected')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL
            );
            """

            ,
            """
            CREATE TABLE IF NOT EXISTS students (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                username VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                phone VARCHAR(15) UNIQUE NOT NULL CHECK (phone ~ '^[0-9]{10,15}$'),
                enrollment_id VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(100) NOT NULL,
                profile_picture TEXT,
                batch_id UUID,  -- Removed UNIQUE constraint to allow multiple students per batch
                role VARCHAR(20) DEFAULT 'student' CHECK (role IN ('student', 'admin', 'moderator')),
                status VARCHAR(15) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
                face_embedding TEXT,  
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,  -- Removed default, will be updated via trigger
                deleted_at TIMESTAMP NULL,
                FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE SET NULL
            );

            """

            """
            CREATE TABLE IF NOT EXISTS admins (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                phone VARCHAR(15) UNIQUE NOT NULL,
                username VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                profile_picture TEXT,
                role VARCHAR(20) DEFAULT 'admin',
                status VARCHAR(10) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP NULL
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS videos (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                course_id UUID NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                url VARCHAR(255) NOT NULL,
                thumbnail VARCHAR(255),
                duration INT,
                order_num INT NOT NULL,
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS student_progress (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                student_id UUID NOT NULL,  -- FIXED: Changed from INT to UUID
                video_id UUID NOT NULL,
                progress DECIMAL(5,2) DEFAULT 0.00, -- % watched
                completed BOOLEAN DEFAULT FALSE,
                last_watched TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,  -- Ensuring UUID match
                FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE
            );
            """,

            """
            CREATE TABLE attendance (
                id SERIAL PRIMARY KEY,
                student_id VARCHAR(36),
                batch_id VARCHAR(36),
                timestamp TIMESTAMP NOT NULL,
                image_path VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            );
            """
        ]

        with Database.get_cursor() as cur:
            for query in queries:
                cur.execute(query)

    # Database.drop_tables()
    # Purpose: Drops all database tables in the correct order to handle foreign key dependencies.
    # Parameters: None
    # Returns: None
    # Detailed Explanation:
    #   - This static method defines a list of 'DROP TABLE IF EXISTS ... CASCADE' queries to remove tables.
    #   - The order is important: tables with foreign keys (e.g., student_progress, batch_courses) are dropped before their referenced tables (e.g., students, courses) to avoid dependency errors.
    #   - The 'CASCADE' option ensures that dependent objects (like foreign key constraints) are also dropped.
    #   - Uses Database.get_cursor() to execute queries in a transaction.
    #   - If all queries succeed, prints "All tables dropped successfully."
    #   - If any query fails, prints an error message and raises the exception, with the transaction rolled back by get_cursor().
    #   - This is useful for resetting the database during development or testing.
    # Related: get_cursor()
    @staticmethod
    def drop_tables():
        """
        Drops all tables in the database in the correct order to handle foreign key dependencies.

        This method executes a series of DROP TABLE statements with the CASCADE option to remove
        all tables, including their constraints, in a single transaction. It ensures dependent
        tables are dropped before their referenced tables.

        Raises:
            Exception: If any query fails, the transaction is rolled back, and the error is raised.

        Returns:
            None
        """

        table_drop_queries = [
            "DROP TABLE IF EXISTS student_progress CASCADE",
            "DROP TABLE IF EXISTS videos CASCADE",
            "DROP TABLE IF EXISTS enrollments CASCADE",
            "DROP TABLE IF EXISTS batch_courses CASCADE",
            "DROP TABLE IF EXISTS batches CASCADE",
            "DROP TABLE IF EXISTS courses CASCADE",
            "DROP TABLE IF EXISTS instructors CASCADE",
            "DROP TABLE IF EXISTS students CASCADE",
            "DROP TABLE IF EXISTS admins CASCADE"
        ]

        try:
            with Database.get_cursor() as cur:

                for query in table_drop_queries:
                    cur.execute(query)
                print("All tables dropped successfully.")
        except Exception as e:

            print(f"Failed to drop tables: {e}")
            raise

class Student:
    # Student.register_student()
    # Purpose: Registers a new student in the students table after checking for duplicates.
    # Parameters: username (str), name (str), email (str), phone (str), enrollment_id (str), password (str, optional), google_id (str, optional), profile_picture (str, optional), face_embedding (str, optional)
    # Returns: Tuple (message, status) - message describes result, status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Checks for duplicate username, email, phone, or enrollment_id in the students table using a SELECT query.
    #   - If a duplicate is found, returns an error message indicating which field is already registered.
    #   - If no duplicates, inserts a new student record with provided details using an INSERT query.
    #   - The INSERT query returns the new student’s UUID (id), included in the success message.
    #   - Uses Database.get_cursor() to execute queries safely.
    #   - If an exception occurs (e.g., database error), returns an error message with the exception details.
    #   - This is used when moving a verified enrollment to the students table or registering a student directly.
    # Related: Database.get_cursor(), verify_and_move_to_students()
    @staticmethod
    def register_student(username, name, email, phone, enrollment_id, password=None, google_id=None, profile_picture=None, face_embedding=None):
        """Registers a new student after checking for duplicate fields."""
        try:
            with Database.get_cursor() as cur:

                cur.execute("""
                    SELECT username, email, phone, enrollment_id 
                    FROM students 
                    WHERE username = %s OR email = %s OR phone = %s OR enrollment_id = %s
                """, (username, email, phone, enrollment_id))
                existing = cur.fetchone()
                if existing:
                    errors = {
                        "Username": existing[0] == username,
                        "Email": existing[1] == email,
                        "Phone number": existing[2] == phone,
                        "Enrollment ID": existing[3] == enrollment_id,
                    }
                    for field, condition in errors.items():
                        if condition:
                            return (f"Error: {field} is already registered!", 0)

                cur.execute("""
                    INSERT INTO students (username, name, email, phone, enrollment_id, password, google_id, profile_picture, face_embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (username, name, email, phone, enrollment_id, password, google_id, profile_picture, face_embedding))
                student_id = cur.fetchone()[0]
                return (f"Student {username} registered successfully! ID: {student_id}", 1)
        except Exception as e:
            return (f"Error: {e}", 0)
        
    # Student.get_student()
    # Purpose: Fetches details of a student by their ID.
    # Parameters: student_id (UUID)
    # Returns: Tuple (student data or error message, status) - student data is a tuple of column values, status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Executes a SELECT query to fetch all columns (id, username, name, etc.) from the students table where id matches and deleted_at is NULL (not soft-deleted).
    #   - If a student is found, returns the row data as a tuple.
    #   - If no student is found, returns "Student not found".
    #   - If an exception occurs, returns the error message.
    #   - Uses Database.get_cursor() for database interaction.
    #   - This is used to retrieve student details for display or verification (e.g., in verify_face() in the Flask app).
    # Related: Database.get_cursor(), verify_face() (Flask app)
    @staticmethod
    def get_student(student_id):
        """Fetches student details by student id."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("""
                    SELECT id, username, name, email, phone, enrollment_id, password, profile_picture, batch_id, role, 
                        status, face_embedding, created_at, updated_at, deleted_at 
                    FROM students 
                    WHERE id = %s AND deleted_at IS NULL
                """, (student_id,))
                student = cur.fetchone()
            return (student, 1) if student else ("Student not found", 0)
        except Exception as e:
            return (f"Error: {e}", 0)

    # Student.get_student_by_email()
    # Purpose: Fetches student details by their email address.
    # Parameters: email (str)
    # Returns: Tuple (student data or error message, status) - student data is a tuple, status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Similar to get_student(), but queries the students table by email instead of ID.
    #   - Ensures deleted_at is NULL to exclude soft-deleted records.
    #   - Returns the student’s row data if found, or "Student not found" if not.
    #   - Catches and returns any database errors.
    #   - Uses Database.get_cursor() for safe query execution.
    #   - Useful for login or lookup by email.
    # Related: Database.get_cursor(), Auth.login()
    @staticmethod
    def get_student_by_email(email):
        """Fetches student details by email."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("SELECT * FROM students WHERE email = %s AND deleted_at IS NULL", (email,))
                student = cur.fetchone()
            return (student, 1) if student else ("Student not found", 0)
        except Exception as e:
            return (f"Error: {e}", 0)

    # Student.update_student()
    # Purpose: Updates specific fields of a student’s record.
    # Parameters: student_id (UUID), name (str, optional), email (str, optional), phone (str, optional), password (str, optional), profile_picture (str, optional), face_embedding (str, optional)
    # Returns: Tuple (message, status) - status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Builds a dynamic UPDATE query based on provided parameters (e.g., only update name if name is provided).
    #   - If no fields are provided, returns "No changes provided".
    #   - Constructs the query with a list of updates (e.g., "name = %s") and corresponding values.
    #   - Includes updated_at = CURRENT_TIMESTAMP to track changes.
    #   - Ensures the student is not soft-deleted (deleted_at IS NULL).
    #   - Uses Database.get_cursor() to execute the query.
    #   - Returns a success message if updated, or an error message if an exception occurs.
    #   - Used for updating student profiles (e.g., after uploading a new profile picture).
    # Related: Database.get_cursor(), upload_student_image() (Flask app)
    @staticmethod
    def update_student(student_id, name=None, email=None, phone=None, password=None, profile_picture=None, face_embedding=None):
        """Updates student details."""
        try:
            with Database.get_cursor() as cur:
                updates = []
                values = []
                if name:
                    updates.append("name = %s")
                    values.append(name)
                if email:
                    updates.append("email = %s")
                    values.append(email)
                if phone:
                    updates.append("phone = %s")
                    values.append(phone)
                if password:
                    updates.append("password = %s")
                    values.append(password)
                if profile_picture:
                    updates.append("profile_picture = %s")
                    values.append(profile_picture)
                if face_embedding is not None:  
                    updates.append("face_embedding = %s")
                    values.append(face_embedding)

                if not updates:
                    return ("No changes provided", 0)

                query = f"UPDATE students SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s AND deleted_at IS NULL"
                values.append(student_id)
                cur.execute(query, tuple(values))
                return ("Student updated successfully!", 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    # Student.delete_student()
    # Purpose: Soft-deletes a student by setting deleted_at to the current timestamp.
    # Parameters: student_id (UUID)
    # Returns: Tuple (message, status) - status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Executes an UPDATE query to set deleted_at = CURRENT_TIMESTAMP for the student with the given ID, if not already deleted.
    #   - Checks cur.rowcount to confirm if the update affected any rows.
    #   - Returns "Student deleted successfully!" if successful, or "Student not found or already deleted" if no rows were updated.
    #   - Uses Database.get_cursor() for safe execution.
    #   - If an exception occurs, returns the error message.
    #   - Soft deletion ensures data is retained but marked as inactive.
    # Related: Database.get_cursor(), check_session_and_role() (Flask app)
    @staticmethod
    def delete_student(student_id):
        """Soft deletes a student from the database."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("UPDATE students SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND deleted_at IS NULL", (student_id,))
                if cur.rowcount > 0:
                    return ("Student deleted successfully!", 1)
                else:
                    return ("Student not found or already deleted", 0)
        except Exception as e:
            return (f"Error: {e}", 0)

    # Student.get_student_data()
    # Purpose: Fetches related data (videos, courses, batches) for a student.
    # Parameters: student_id (UUID), data_type (str, default="all") - specifies which data to fetch ("videos", "courses", "batches", or "all")
    # Returns: Tuple (data or error message, status) - data is a dict or list, status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Defines three SQL queries to fetch videos, courses, or batches associated with the student via their batch.
    #   - For "videos", joins students, batches, batch_courses, courses, videos, and instructors to get video details.
    #   - For "courses", joins to get course details and instructor names.
    #   - For "batches", fetches batch details (id, name, start_date, end_date).
    #   - If data_type is "all", executes all queries and returns a dictionary with keys "videos", "courses", "batches".
    #   - If a specific data_type is provided, executes only that query.
    #   - Ensures deleted_at is NULL for all relevant tables.
    #   - Uses Database.get_cursor() for query execution.
    #   - Returns an error if data_type is invalid or an exception occurs.
    #   - Used to populate student dashboards with relevant content.
    # Related: Database.get_cursor(), dashboard_home() (Flask app)
    @staticmethod
    def get_student_data(student_id, data_type="all"):
        """Fetches student-related data based on the current schema."""
        try:
            with Database.get_cursor() as cur:
                queries = {
                    "videos": """
                        SELECT 
                            v.id AS video_id, v.title AS video_title, v.description AS video_description, 
                            v.url AS video_url, v.thumbnail AS video_thumbnail, v.duration AS video_duration, 
                            v.course_id, c.course_name AS course_name, i.name AS instructor_name
                        FROM students s
                        INNER JOIN batches b ON s.batch_id = b.id
                        INNER JOIN batch_courses bc ON b.id = bc.batch_id
                        INNER JOIN courses c ON bc.course_id = c.id
                        INNER JOIN videos v ON c.id = v.course_id
                        INNER JOIN instructors i ON c.instructor_id = i.id
                        WHERE s.id = %s AND s.deleted_at IS NULL;
                    """,
                    "courses": """
                        SELECT 
                            c.id AS course_id, c.course_name AS course_name, c.description AS course_description, 
                            i.name AS instructor_name
                        FROM students s
                        INNER JOIN batches b ON s.batch_id = b.id
                        INNER JOIN batch_courses bc ON b.id = bc.batch_id
                        INNER JOIN courses c ON bc.course_id = c.id
                        INNER JOIN instructors i ON c.instructor_id = i.id
                        WHERE s.id = %s AND s.deleted_at IS NULL;
                    """,
                    "batches": """
                        SELECT 
                            b.id AS batch_id, b.batch_name AS batch_name, b.start_date, b.end_date
                        FROM students s
                        INNER JOIN batches b ON s.batch_id = b.id
                        WHERE s.id = %s AND s.deleted_at IS NULL;
                    """
                }

                if data_type == "all":
                    result = {}
                    for key, query in queries.items():
                        cur.execute(query, (student_id,))
                        result[key] = cur.fetchall()
                    return (result, 1)

                if data_type in queries:
                    cur.execute(queries[data_type], (student_id,))
                    return (cur.fetchall(), 1)

                return ("Invalid data type requested", 0)
        except Exception as e:
            return (f"Error: {e}", 0)

    # Student.get_student_courses_and_batches()
    # Purpose: Retrieves all courses and their associated batches for a student.
    # Parameters: student_id (UUID)
    # Returns: Tuple (student_data or error message, status) - student_data is a dict, status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Executes a query joining students, batches, batch_courses, and courses to fetch course and batch details.
    #   - Filters for non-deleted records (deleted_at IS NULL).
    #   - Organizes results into a dictionary with courses as keys, each containing course details and a list of associated batches.
    #   - If no results are found, returns "No courses or batches found for this student".
    #   - Uses Database.get_cursor() for safe query execution.
    #   - Handles exceptions by returning an error message.
    #   - Used to display a student’s enrolled courses and batches (e.g., in the attendance page).
    # Related: Database.get_cursor(), attendance() (Flask app)
    @staticmethod
    def get_student_courses_and_batches(student_id):
        """
        Retrieves all courses and associated batches for a given student.

        Args:
            student_id (UUID): The ID of the student

        Returns:
            Tuple: (result, status)
                - result: Dictionary containing courses and their batches
                - status: 1 for success, 0 for failure
        """
        try:
            with Database.get_cursor() as cur:
                query = """
                    SELECT 
                        c.id AS course_id,
                        c.course_name,
                        c.description,
                        b.id AS batch_id,
                        b.batch_name,
                        b.start_date,
                        b.end_date
                    FROM students s
                    INNER JOIN batches b ON s.batch_id = b.id
                    INNER JOIN batch_courses bc ON b.id = bc.batch_id
                    INNER JOIN courses c ON bc.course_id = c.id
                    WHERE s.id = %s 
                    AND s.deleted_at IS NULL
                    AND b.deleted_at IS NULL
                    AND c.deleted_at IS NULL
                    ORDER BY b.start_date, c.course_name
                """
                cur.execute(query, (student_id,))
                results = cur.fetchall()

                if not results:
                    return ("No courses or batches found for this student", 0)

                student_data = {
                    "student_id": student_id,
                    "courses": {}
                }

                for row in results:
                    course_id = str(row[0])  
                    if course_id not in student_data["courses"]:
                        student_data["courses"][course_id] = {
                            "course_name": row[1],
                            "description": row[2],
                            "batches": []
                        }

                    student_data["courses"][course_id]["batches"].append({
                        "batch_id": str(row[3]),
                        "batch_name": row[4],
                        "start_date": row[5],
                        "end_date": row[6]
                    })

                return (student_data, 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    # Student.get_student_course_progress()
    # Purpose: Retrieves progress details for a student’s courses, including video completion.
    # Parameters: student_id (UUID)
    # Returns: Tuple (progress_data or error message, status) - progress_data is a dict, status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Executes a complex query joining students, enrollments, batches, batch_courses, courses, videos, and student_progress.
    #   - Groups results by course and batch, calculating:
    #     - Total videos per course (COUNT(v.id)).
    #     - Completed videos (SUM of completed field in student_progress).
    #     - Average video progress (AVG of progress field).
    #     - Enrollment progress and completion status.
    #   - Organizes results into a dictionary with courses, each containing course details, batch info, and progress metrics.
    #   - If no results are found, returns "No course progress found for this student".
    #   - Uses Database.get_cursor() for execution.
    #   - Converts numeric fields to float for JSON compatibility.
    #   - Used to show students their course progress.
    # Related: Database.get_cursor()
    @staticmethod
    def get_student_course_progress(student_id):
        """
        Retrieves course progress details for a given student, including video completion status.

        Args:
            student_id (UUID): The ID of the student

        Returns:
            Tuple: (result, status)
                - result: Dictionary containing courses with progress details
                - status: 1 for success, 0 for failure
        """
        try:
            with Database.get_cursor() as cur:
                query = """
                    SELECT 
                        c.id AS course_id,
                        c.course_name,
                        c.description,
                        b.id AS batch_id,
                        b.batch_name,
                        COUNT(v.id) AS total_videos,
                        SUM(CASE WHEN sp.completed THEN 1 ELSE 0 END) AS completed_videos,
                        COALESCE(AVG(sp.progress), 0) AS avg_video_progress,
                        e.progress AS enrollment_progress,
                        e.completed AS enrollment_completed
                    FROM students s
                    INNER JOIN enrollments e ON s.id = e.student_id
                    INNER JOIN batches b ON e.batch_id = b.id
                    INNER JOIN batch_courses bc ON b.id = bc.batch_id
                    INNER JOIN courses c ON bc.course_id = c.id
                    LEFT JOIN videos v ON c.id = v.course_id
                    LEFT JOIN student_progress sp ON v.id = sp.video_id AND sp.student_id = s.id
                    WHERE s.id = %s 
                    AND s.deleted_at IS NULL
                    AND b.deleted_at IS NULL
                    AND c.deleted_at IS NULL
                    AND (v.deleted_at IS NULL OR v.id IS NULL)
                    GROUP BY c.id, c.course_name, c.description, b.id, b.batch_name, e.progress, e.completed
                    ORDER BY c.course_name
                """
                cur.execute(query, (student_id,))
                results = cur.fetchall()

                if not results:
                    return ("No course progress found for this student", 0)

                progress_data = {
                    "student_id": student_id,
                    "courses": {}
                }

                for row in results:
                    course_id = str(row[0])
                    progress_data["courses"][course_id] = {
                        "course_name": row[1],
                        "description": row[2],
                        "batch": {
                            "batch_id": str(row[3]),
                            "batch_name": row[4]
                        },
                        "progress": {
                            "total_videos": row[5],
                            "completed_videos": row[6],
                            "avg_video_progress": float(row[7]),  
                            "enrollment_progress": float(row[8]),  
                            "enrollment_completed": row[9]
                        }
                    }

                return (progress_data, 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    # Student.verify_and_move_to_students()
    # Purpose: Moves a pending enrollment to the students table after verification.
    # Parameters: enrollment_id (UUID)
    # Returns: Tuple (message, status) - status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Queries the enrollments table for a pending enrollment (status = 'pending', deleted_at IS NULL).
    #   - If not found, returns "Enrollment not found or already processed".
    #   - Inserts the enrollment data (username, name, email, etc.) into the students table using an INSERT query.
    #   - Updates the enrollments table to set status = 'verified' and updated_at to the current timestamp.
    #   - Uses Database.get_cursor() for transactional safety.
    #   - Returns the new student ID in the success message.
    #   - If an exception occurs, returns the error message.
    #   - Used by admins or instructors to approve registrations.
    # Related: Database.get_cursor(), manage_registrations(), manage_students() (Flask app)
    @staticmethod
    def verify_and_move_to_students(enrollment_id):
        """Moves a verified enrollment to the students table."""
        try:
            with Database.get_cursor() as cur:

                cur.execute("""
                    SELECT username, name, email, phone, enrollment_id, password, profile_picture, face_embedding, google_id
                    FROM enrollments 
                    WHERE id = %s AND status = 'pending' AND deleted_at IS NULL
                """, (enrollment_id,))
                enrollment = cur.fetchone()
                if not enrollment:
                    return ("Enrollment not found or already processed", 0)

                cur.execute("""
                    INSERT INTO students (username, name, email, phone, enrollment_id, password, profile_picture, face_embedding, google_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, enrollment)
                student_id = cur.fetchone()[0]

                cur.execute("""
                    UPDATE enrollments SET status = 'verified', updated_at = CURRENT_TIMESTAMP 
                    WHERE id = %s
                """, (enrollment_id,))

                return (f"Student verified and moved successfully! Student ID: {student_id}", 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    # Student.assign_batch()
    # Purpose: Assigns a batch to a student (admin-only).
    # Parameters: student_id (UUID), batch_id (UUID)
    # Returns: Tuple (message, status) - status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Checks if the student already has a batch assigned by querying the students table.
    #   - If a batch exists, returns "Student already assigned to a batch".
    #   - Updates the students table to set batch_id and updated_at for the given student_id.
    #   - Ensures the student is not soft-deleted.
    #   - Uses Database.get_cursor() for execution.
    #   - Returns "Batch assigned successfully!" if updated, or "Student not found" if no rows were affected.
    #   - Handles exceptions by returning an error message.
    #   - Used by admins to assign students to batches.
    # Related: Database.get_cursor(), update_student_batch() (Flask app)
    @staticmethod
    def assign_batch(student_id, batch_id):
        """Assigns a batch to a student (admin only)."""
        try:
            with Database.get_cursor() as cur:

                cur.execute("SELECT batch_id FROM students WHERE id = %s AND deleted_at IS NULL", (student_id,))
                existing_batch = cur.fetchone()
                if existing_batch and existing_batch[0]:
                    return ("Student already assigned to a batch", 0)

                cur.execute("""
                    UPDATE students SET batch_id = %s, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = %s AND deleted_at IS NULL
                """, (batch_id, student_id))
                if cur.rowcount > 0:
                    return ("Batch assigned successfully!", 1)
                else:
                    return ("Student not found", 0)
        except Exception as e:
            return (f"Error: {e}", 0)
        
    # Student.get_students_by_batch()
    # Purpose: Fetches all students in a specific batch.
    # Parameters: batch_id (UUID), requesting_student_id (UUID, optional) - for security check
    # Returns: Tuple (students or error message, status) - students is a list of dicts, status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - If requesting_student_id is provided, verifies that the requesting student is in the same batch.
    #   - Queries the students table for all students with the given batch_id, excluding soft-deleted records.
    #   - Returns a list of dictionaries with student id, name, and email.
    #   - If no students are found, returns "No students found in this batch".
    #   - Uses Database.get_cursor() for safe execution.
    #   - Handles exceptions by returning an error message.
    #   - Used to display batch members (e.g., in get_batch_students() in the Flask app).
    # Related: Database.get_cursor(), get_batch_students() (Flask app)
    @staticmethod
    def get_students_by_batch(batch_id, requesting_student_id=None):
        """
        Fetches all students enrolled in a specific batch.

        Args:
            batch_id (UUID): The ID of the batch to fetch students from
            requesting_student_id (UUID, optional): The ID of the student making the request, 
                to verify they belong to the same batch (optional security check)

        Returns:
            Tuple: (result, status)
                - result: List of student dictionaries with id, name, and email
                - status: 1 for success, 0 for failure
        """
        try:
            with Database.get_cursor() as cur:

                if requesting_student_id:
                    cur.execute("""
                        SELECT id 
                        FROM students 
                        WHERE id = %s AND batch_id = %s AND deleted_at IS NULL
                    """, (requesting_student_id, batch_id))
                    if not cur.fetchone():
                        return ("Unauthorized: You are not enrolled in this batch", 0)

                cur.execute("""
                    SELECT id, name, email 
                    FROM students 
                    WHERE batch_id = %s AND deleted_at IS NULL
                """, (batch_id,))
                students = cur.fetchall()

                if not students:
                    return ("No students found in this batch", 0)

                result = [
                    {"id": str(student[0]), "name": student[1], "email": student[2]}
                    for student in students
                ]
                return (result, 1)

        except Exception as e:
            return (f"Error: {e}", 0)

class Course:
    # Course.add_course()
    # Purpose: Adds a new course to the courses table.
    # Parameters: course_name (str), description (str), instructor_id (UUID)
    # Returns: Tuple (course_id or error message, status) - status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Inserts a new course record with the provided course_name, description, and instructor_id.
    #   - Uses an INSERT query that returns the new course’s UUID (id).
    #   - Uses Database.get_cursor() for execution.
    #   - Returns the course_id on success, or an error message if an exception occurs (e.g., duplicate course_name).
    #   - Used when instructors or admins create new courses.
    # Related: Database.get_cursor(), add_video_course() (Flask app)
    @staticmethod
    def add_course(course_name, description, instructor_id):
        """Adds a new course."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO courses (course_name, description,instructor_id)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (course_name, description,instructor_id))
                course_id = cur.fetchone()[0]
            return (course_id, 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    # Course.get_course()
    # Purpose: Fetches a course by its ID.
    # Parameters: course_id (UUID)
    # Returns: Tuple (course data or error message, status) - course data is a tuple, status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Queries the courses table for a course with the given ID, excluding soft-deleted records.
    #   - Returns the course row if found, or "Course not found" if not.
    #   - Uses Database.get_cursor() for execution.
    #   - Handles exceptions by returning an error message.
    #   - Used to display course details (e.g., in course_page() in the Flask app).
    # Related: Database.get_cursor(), course_page() (Flask app)
    @staticmethod
    def get_course(course_id):
        """Fetches a course by its id."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("SELECT * FROM courses WHERE id = %s AND deleted_at IS NULL", (course_id,))
                course = cur.fetchone()
            if course:
                return (course, 1)
            else:
                return ("Course not found", 0)
        except Exception as e:
            return (f"Error: {e}", 0)

    # Course.update_course()
    # Purpose: Updates specific fields of a course.
    # Parameters: course_id (UUID), course_name (str, optional), description (str, optional), instructor_id (UUID, optional)
    # Returns: Tuple (message, status) - status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Builds a dynamic UPDATE query based on provided parameters.
    #   - If no fields are provided, returns "No updates provided".
    #   - Includes updated_at = CURRENT_TIMESTAMP in the query.
    #   - Uses Database.get_cursor() for execution.
    #   - Returns "Course updated successfully" if updated, or an error message if an exception occurs.
    #   - Used to modify course details (e.g., in edit_course_video() in the Flask app).
    # Related: Database.get_cursor(), edit_course_video() (Flask app)
    @staticmethod
    def update_course(course_id, course_name=None, description=None, instructor_id=None):
        """Updates course details."""
        try:
            updates = []
            values = []
            if course_name:
                updates.append("course_name = %s")
                values.append(course_name)
            if description:
                updates.append("description = %s")
                values.append(description)
            if instructor_id:
                updates.append("instructor_id = %s")
                values.append(instructor_id)
            if not updates:
                return ("No updates provided", 0)

            values.append(course_id)
            query = f"UPDATE courses SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s"

            with Database.get_cursor() as cur:
                cur.execute(query, tuple(values))
            return ("Course updated successfully", 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    # Course.delete_course()
    # Purpose: Soft-deletes a course by setting deleted_at.
    # Parameters: course_id (UUID)
    # Returns: Tuple (message, status) - status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Updates the courses table to set deleted_at = CURRENT_TIMESTAMP for the given course_id.
    #   - Ensures the course is not already deleted.
    #   - Returns "Course deleted successfully!" if updated, or "Course not found" if no rows were affected.
    #   - Uses Database.get_cursor() for execution.
    #   - Handles exceptions by returning an error message.
    #   - Used to remove courses (e.g., in delete_course_video() in the Flask app).
    # Related: Database.get_cursor(), delete_course_video() (Flask app)
    @staticmethod
    def delete_course(course_id):
        """Deletes a course by its id."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("UPDATE courses SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND deleted_at IS NULL", (course_id,))
                if cur.rowcount > 0:
                    return ("Course deleted successfully", 1)
                else:
                    return ("Course not found", 0)
        except Exception as e:
            return (f"Error: {e}", 0)

class Instructor:
    # Instructor.add_instructor()
    # Purpose: Adds a new instructor to the instructors table.
    # Parameters: username (str), name (str), email (str), phone (str), password (str)
    # Returns: Tuple (message, status) - status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Inserts a new instructor record with the provided details.
    #   - Returns the new instructor’s UUID in the success message.
    #   - Uses Database.get_cursor() for execution.
    #   - If an exception occurs (e.g., duplicate username), returns an error message.
    #   - Used by admins to create instructor accounts.
    # Related: Database.get_cursor(), add_user() (Flask app)
    @staticmethod
    def add_instructor(username, name, email, phone, password):
        """Adds a new instructor."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO instructors (username, name, email, phone, password)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (username, name, email, phone, password))
                instructor_id = cur.fetchone()[0]
            return (f"Instructor '{username}' added successfully! ID: {instructor_id}", 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    # Instructor.get_instructor()
    # Purpose: Fetches an instructor by their ID.
    # Parameters: instructor_id (UUID)
    # Returns: Tuple (instructor_data or error message, status) - instructor_data is a dict, status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Queries the instructors table for the given ID, excluding soft-deleted records.
    #   - Returns a dictionary with instructor details (id, username, name, etc.) if found.
    #   - Returns "Instructor not found" if no record is found.
    #   - Uses Database.get_cursor() for execution.
    #   - Handles exceptions by returning an error message.
    #   - Used to display instructor details (e.g., in course_page() in the Flask app).
    # Related: Database.get_cursor(), course_page() (Flask app)
    @staticmethod
    def get_instructor(instructor_id):
        """Fetches an instructor by its id."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("""
                    SELECT id, username, name, email, phone, created_at, updated_at 
                    FROM instructors 
                    WHERE id = %s AND deleted_at IS NULL
                """, (instructor_id,))
                instructor = cur.fetchone()
            if instructor:
                instructor_data = {
                    "id": instructor[0],
                    "username": instructor[1],
                    "name": instructor[2],
                    "email": instructor[3],
                    "phone": instructor[4],
                    "created_at": instructor[5],
                    "updated_at": instructor[6]
                }
                return (instructor_data, 1)
            else:
                return ("Instructor not found", 0)
        except Exception as e:
            return (f"Error: {e}", 0)

    # Instructor.update_instructor()
    # Purpose: Updates specific fields of an instructor’s record.
    # Parameters: instructor_id (UUID), username (str, optional), name (str, optional), email (str, optional), phone (str, optional), password (str, optional)
    # Returns: Tuple (message, status) - status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Builds a dynamic UPDATE query based on provided parameters.
    #   - If no fields are provided, returns "No updates provided".
    #   - Includes updated_at = CURRENT_TIMESTAMP.
    #   - Uses Database.get_cursor() for execution.
    #   - Returns "Instructor updated successfully" if updated, or an error message if an exception occurs.
    #   - Used to modify instructor profiles.
    # Related: Database.get_cursor()
    @staticmethod
    def update_instructor(instructor_id, username=None, name=None, email=None, phone=None, password=None):
        """Updates instructor details."""
        try:
            updates = []
            values = []
            if username:
                updates.append("username = %s")
                values.append(username)
            if name:
                updates.append("name = %s")
                values.append(name)
            if email:
                updates.append("email = %s")
                values.append(email)
            if phone:
                updates.append("phone = %s")
                values.append(phone)
            if password:
                updates.append("password = %s")
                values.append(password)
            if not updates:
                return ("No updates provided", 0)

            query = f"UPDATE instructors SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
            values.append(instructor_id)

            with Database.get_cursor() as cur:
                cur.execute(query, tuple(values))
            return ("Instructor updated successfully", 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    # Instructor.delete_instructor()
    # Purpose: Soft-deletes an instructor.
    # Parameters: instructor_id (UUID)
    # Returns: Tuple (message, status) - status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Updates the instructors table to set deleted_at = CURRENT_TIMESTAMP.
    #   - Ensures the instructor is not already deleted.
    #   - Returns "Instructor deleted successfully!" if updated, or "Instructor not found" if no rows were affected.
    #   - Uses Database.get_cursor() for execution.
    #   - Handles exceptions by returning an error message.
    #   - Used to remove instructors.
    # Related: Database.get_cursor()
    @staticmethod
    def delete_instructor(instructor_id):
        """Deletes an instructor by its id."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("UPDATE instructors SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND deleted_at IS NULL", (instructor_id,))
                if cur.rowcount > 0:
                    return ("Instructor deleted successfully", 1)
                else:
                    return ("Instructor not found", 0)
        except Exception as e:
            return (f"Error: {e}", 0)

    # Instructor.get_instructor_data()
    # Purpose: Fetches related data (courses, batches, videos) for an instructor.
    # Parameters: instructor_id (UUID), data_type (str, default="all") - specifies data to fetch ("courses", "batches", "videos", or "all")
    # Returns: Tuple (data or error message, status) - data is a dict or list, status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Defines queries to fetch courses, batches, or videos associated with the instructor.
    #   - For "courses", fetches course details and associated batch IDs.
    #   - For "batches", fetches batches linked to the instructor’s courses.
    #   - For "videos", fetches videos from the instructor’s courses.
    #   - If data_type is "all", executes all queries and returns a dictionary.
    #   - Ensures deleted_at is NULL where applicable.
    #   - Uses Database.get_cursor() for execution.
    #   - Returns an error if data_type is invalid or an exception occurs.
    #   - Used to populate instructor dashboards.
    # Related: Database.get_cursor(), dashboard_home(), manage_class_cards() (Flask app)
    @staticmethod
    def get_instructor_data(instructor_id, data_type="all"):
        try:
            with Database.get_cursor() as cur:
                queries = {
                    "courses": """
                        SELECT 
                            c.id AS course_id, c.course_name AS course_name, c.description AS course_description,
                            bc.batch_id AS batch_id, c.instructor_id AS course_instructor
                        FROM courses c
                        LEFT JOIN batch_courses bc ON c.id = bc.course_id
                        WHERE c.instructor_id = %s  AND c.deleted_at IS NULL;
                    """,
                    "batches": """
                        SELECT 
                            b.id AS batch_id, b.batch_name AS batch_name, b.start_date, b.end_date
                        FROM batches b
                        INNER JOIN batch_courses bc ON b.id = bc.batch_id
                        INNER JOIN courses c ON bc.course_id = c.id
                        WHERE c.instructor_id = %s  AND b.deleted_at IS NULL;
                    """,

                    "videos": """
                        SELECT 
                            v.id AS video_id, v.course_id AS course_id, v.title AS video_title, v.description AS video_description, 
                            v.url AS video_url, v.thumbnail AS video_thumbnail, v.duration AS video_duration
                        FROM videos v
                        INNER JOIN courses c ON v.course_id = c.id
                        WHERE c.instructor_id = %s;
                    """
                }

                if data_type == "all":
                    result = {}
                    for key, query in queries.items():
                        cur.execute(query, (instructor_id,))
                        result[key] = cur.fetchall()

                    return (result, 1)

                if data_type in queries:
                    cur.execute(queries[data_type], (instructor_id,))
                    return (cur.fetchall(), 1)

                return ("Invalid data type requested", 0)

        except Exception as e:
            return (f"Error: {e}", 0)

    # Instructor.add_live_class()
    # Purpose: Adds a new live class to the live_classes table.
    # Parameters: room_name (str), instructor_id (UUID), batch_id (UUID, optional), course_id (UUID, optional)
    # Returns: Tuple (class_id, status) - status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Inserts a new live class record with the provided details.
    #   - Returns the new class’s UUID.
    #   - Uses Database.get_cursor() for execution.
    #   - If an exception occurs, it is not explicitly handled here (handled by get_cursor()).
    #   - Note: This function seems incomplete as the live_classes table is not defined in create_tables(), and it’s not used in the Flask app provided.
    # Related: Database.get_cursor()
    @staticmethod
    def add_live_class(room_name, instructor_id, batch_id=None, course_id=None):
        with Database.get_cursor() as cur:
            cur.execute(
                "INSERT INTO live_classes (room_name, instructor_id, batch_id, course_id, created_at) "
                "VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP) RETURNING id",
                (room_name, instructor_id, batch_id, course_id)
            )
            return cur.fetchone()[0], 1

class Batch:
    # Batch.add_batch()
    # Purpose: Adds a new batch to the batches table.
    # Parameters: batch_name (str), start_date (date), end_date (date)
    # Returns: Tuple (message, status) - status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Inserts a new batch record with the provided details.
    #   - Returns the new batch’s UUID in the success message.
    #   - Uses Database.get_cursor() for execution.
    #   - If an exception occurs (e.g., duplicate batch_name), returns an error message.
    #   - Used to create new batches for course assignments.
    # Related: Database.get_cursor(), add_video_course() (Flask app)
    @staticmethod
    def add_batch(batch_name, start_date, end_date):
        """Adds a new batch."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO batches (batch_name, start_date, end_date)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (batch_name, start_date, end_date))
                batch_id = cur.fetchone()[0]
            return (f"Batch '{batch_name}' added successfully! ID: {batch_id}", 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    # Batch.get_batch()
    # Purpose: Fetches a batch by its ID.
    # Parameters: batch_id (UUID)
    # Returns: Tuple (batch data or error message, status) - batch data is a tuple, status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Queries the batches table for the given ID, excluding soft-deleted records.
    #   - Returns the batch row if found, or "Batch not found" if not.
    #   - Uses Database.get_cursor() for execution.
    #   - Handles exceptions by returning an error message.
    #   - Used to retrieve batch details.
    # Related: Database.get_cursor()
    @staticmethod
    def get_batch(batch_id):
        """Fetches a batch by its id."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("SELECT * FROM batches WHERE id = %s AND deleted_at IS NULL", (batch_id,))
                batch = cur.fetchone()
            if batch:
                return (batch, 1)
            else:
                return ("Batch not found", 0)
        except Exception as e:
            return (f"Error: {e}", 0)

    # Batch.update_batch()
    # Purpose: Updates specific fields of a batch.
    # Parameters: batch_id (UUID), batch_name (str, optional), start_date (date, optional), end_date (date, optional)
    # Returns: Tuple (message, status) - status is 1 (success) or 0 (failure)
    # Detailed Explanation:
    #   - Builds a dynamic UPDATE query based on provided parameters.
    #   - If no fields are provided, returns "No changes provided".
    #   - Includes updated_at = CURRENT_TIMESTAMP.
    #   - Uses Database.get_cursor() for execution.
    #   - Returns "Batch updated successfully!" if updated, or an error message if an exception occurs.
    #   - Used to modify batch details.
    # Related: Database.get_cursor()
    @staticmethod
    def update_batch(batch_id, batch_name=None, start_date=None, end_date=None,):
        """Updates batch details."""
        try:
            updates = []
            values = []
            if batch_name:
                updates.append("batch_name = %s")
                values.append(batch_name)
            if start_date:
                updates.append("start_date = %s")
                values.append(start_date)
            if end_date:
                updates.append("end_date = %s")
                values.append(end_date)
            if not updates:
                return ("No changes provided", 0)

            query = f"UPDATE batches SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
            values.append(batch_id)
            with Database.get_cursor() as cur:
                cur.execute(query, tuple(values))
            return ("Batch updated successfully!", 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    @staticmethod
    def delete_batch(batch_id):
        """Deletes a batch by its id."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("UPDATE batches SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND deleted_at IS NULL", (batch_id,))
                if cur.rowcount > 0:
                    return ("Batch deleted successfully!", 1)
                else:
                    return ("Batch not found", 0)
        except Exception as e:
            return (f"Error: {e}", 0)

class Video:
    @staticmethod
    def add_video(course_id, title, description, url, thumbnail, duration, order_num):
        try:
            with Database.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO videos (course_id, title, description, url, thumbnail, duration, order_num)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (course_id, title, description, url, thumbnail, duration, order_num))
                video_id = cur.fetchone()[0]
            return (f"Video '{title}' added successfully! ID: {video_id}", 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    @staticmethod
    def get_video(video_id):

        try:
            with Database.get_cursor() as cur:
                cur.execute("SELECT * FROM videos WHERE id = %s", (video_id,))
                video = cur.fetchone()
            if video:
                return (video, 1)
            else:
                return ("Video not found", 0)
        except Exception as e:
            return (f"Error: {e}", 0)

    @staticmethod
    def update_video(video_id, title=None, description=None, url=None, thumbnail=None, duration=None):

        try:
            updates = []
            values = []
            if title:
                updates.append("title = %s")
                values.append(title)
            if description:
                updates.append("description = %s")
                values.append(description)
            if url:
                updates.append("url = %s")
                values.append(url)
            if thumbnail:
                updates.append("thumbnail = %s")
                values.append(thumbnail)
            if duration:
                updates.append("duration = %s")
                values.append(duration)

            if not updates:
                return ("No changes provided", 0)

            query = f"UPDATE videos SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
            values.append(video_id)
            with Database.get_cursor() as cur:
                cur.execute(query, tuple(values))
            return ("Video updated successfully!", 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    @staticmethod
    def delete_video(video_id):
        """
        Deletes a video by its id.

        :param video_id: UUID of the video.
        :return: Tuple with success message and status code.
        """
        try:
            with Database.get_cursor() as cur:
                cur.execute("""
                DELETE FROM videos
                WHERE id = %s
            """, (video_id,))
                if cur.rowcount > 0:
                    return ("Video deleted successfully!", 1)
                else:
                    return ("Video not found", 0)
        except Exception as e:
            print(e)
            return (f"Error: {e}", 0)

class Admin:

    @staticmethod
    def add_admin(phone, username, name, email, password):
        """Adds a new admin."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO admins (phone, username, name, email, password)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (phone, username, name, email, password))
                admin_id = cur.fetchone()[0]
            return (f"Admin '{username}' added successfully! ID: {admin_id}", 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    @staticmethod
    def get_admin(admin_id):
        """Fetches an admin by its id."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("SELECT * FROM admins WHERE id = %s AND deleted_at IS NULL", (admin_id,))
                admin = cur.fetchone()
            if admin:
                return (admin, 1)
            else:
                return ("Admin not found", 0)
        except Exception as e:
            return (f"Error: {e}", 0)

    @staticmethod
    def update_admin(admin_id, phone=None, username=None, name=None, email=None, password=None):
        """Updates admin details."""
        try:
            updates = []
            values = []
            if phone:
                updates.append("phone = %s")
                values.append(phone)
            if username:
                updates.append("username = %s")
                values.append(username)
            if name:
                updates.append("name = %s")
                values.append(name)
            if email:
                updates.append("email = %s")
                values.append(email)
            if password:
                updates.append("password = %s")
                values.append(password)
            if not updates:
                return ("No updates provided", 0)

            query = f"UPDATE admins SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
            values.append(admin_id)
            with Database.get_cursor() as cur:
                cur.execute(query, tuple(values))
            return ("Admin updated successfully", 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    @staticmethod
    def delete_admin(admin_id):
        """Deletes an admin by its id."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("UPDATE admins SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s AND deleted_at IS NULL", (admin_id,))
                if cur.rowcount > 0:
                    return ("Admin deleted successfully", 1)
                else:
                    return ("Admin not found", 0)
        except Exception as e:
            return (f"Error: {e}", 0)

    @staticmethod  
    def get_all_batches_courses_videos(data_type="all"):
        """Fetches all batches, courses, videos, and instructors."""
        try:
            with Database.get_cursor() as cur:
                queries = {
                    "batches": """
                        SELECT 
                            b.id AS batch_id, b.batch_name AS batch_name, 
                            b.start_date, b.end_date,
                            COUNT(DISTINCT bc.course_id) AS course_count
                        FROM batches b
                        LEFT JOIN batch_courses bc ON b.id = bc.batch_id
                        WHERE b.deleted_at IS NULL
                        GROUP BY b.id, b.batch_name, b.start_date, b.end_date;
                    """,
                    "courses": """
                        SELECT 
                            c.id AS course_id, 
                            c.course_name AS course_name, 
                            c.description AS course_description, 
                            bc.batch_id AS batch_ids, 
                            c.instructor_id AS course_instructor
                        FROM courses c
                        LEFT JOIN batch_courses bc ON c.id = bc.course_id
                        WHERE c.deleted_at IS NULL;
                    """,
                    "videos": """
                        SELECT 
                            v.id AS video_id, v.course_id AS course_id, 
                            v.title AS video_title, v.description AS video_description,
                            v.url AS video_url, v.thumbnail AS video_thumbnail, 
                            v.duration AS video_duration
                        FROM videos v
                        INNER JOIN courses c ON v.course_id = c.id
                        WHERE c.deleted_at IS NULL;  -- Filter by course deletion instead
                    """,
                    "instructors": """
                        SELECT 
                            i.id AS instructor_id, 
                            i.username, 
                            i.name AS instructor_name
                        FROM instructors i
                        WHERE i.deleted_at IS NULL;
                    """
                }

                if data_type == "all":
                    result = {}
                    for key, query in queries.items():
                        cur.execute(query)
                        result[key] = cur.fetchall()
                    return (result, 1)

                if data_type in queries:
                    cur.execute(queries[data_type])
                    return (cur.fetchall(), 1)

                return ("Invalid data type requested", 0)

        except Exception as e:
            return (f"Error: {e}", 0)
    @staticmethod
    def verify_enrollment(enrollment_id):
        """Admin verifies an enrollment."""
        result, status = Student.verify_and_move_to_students(enrollment_id)
        return result, status

    @staticmethod
    def assign_student_batch(student_id, batch_id):
        """Admin assigns a batch to a student."""
        result, status = Student.assign_batch(student_id, batch_id)
        return result, status

class  Enrollment:

    @staticmethod
    def add_enrollment(student_id, batch_id, status):
        """Adds a new enrollment."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO enrollments (student_id, batch_id, status)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (student_id, batch_id, status))
                enrollment_id = cur.fetchone()[0]
            return (f"Enrollment added successfully! ID: {enrollment_id}", 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    @staticmethod
    def register_user(username, name, email, phone, enrollment_id, password=None, profile_picture=None, face_embedding=None, google_id=None):
        """Registers a new user in the enrollments table."""
        try:

            if not password and not google_id:
                return ("Error: Either password or google_id is required.", 0)

            with Database.get_cursor() as cur:

                cur.execute("""
                    SELECT username, email, phone, enrollment_id 
                    FROM enrollments 
                    WHERE username = %s OR email = %s OR phone = %s OR enrollment_id = %s
                """, (username, email, phone, enrollment_id))
                existing = cur.fetchone()
                if existing:
                    errors = {
                        "Username": existing[0] == username,
                        "Email": existing[1] == email,
                        "Phone": existing[2] == phone,
                        "Enrollment ID": existing[3] == enrollment_id,
                    }
                    for field, condition in errors.items():
                        if condition:
                            return (f"Error: {field} is already registered!", 0)

                cur.execute("""
                    INSERT INTO enrollments (username, name, email, phone, enrollment_id, password, profile_picture, face_embedding, google_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (username, name, email, phone, enrollment_id, password, profile_picture, face_embedding, google_id))

                new_enrollment_id = cur.fetchone()[0]
                print('aa')
                return (f"User {username} registered successfully! Enrollment ID: {new_enrollment_id}", 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    @staticmethod
    def get_enrollment(enrollment_id):
        """Fetches an enrollment by ID."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("SELECT * FROM enrollments WHERE id = %s AND deleted_at IS NULL", (enrollment_id,))
                enrollment = cur.fetchone()
            return (enrollment, 1) if enrollment else ("Enrollment not found", 0)
        except Exception as e:
            return (f"Error: {e}", 0)

    @staticmethod
    def update_enrollment(enrollment_id, status=None):
        """Updates an enrollment’s status."""
        try:
            if status is None:
                return ("No updates provided", 0)
            with Database.get_cursor() as cur:
                cur.execute("""
                    UPDATE enrollments
                    SET status = %s
                    WHERE id = %s
                """, (status, enrollment_id))
            return ("Enrollment updated successfully", 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    @staticmethod
    def delete_enrollment(enrollment_id):
        """Deletes an enrollment by its id."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("DELETE FROM enrollments WHERE id = %s", (enrollment_id,))
                if cur.rowcount > 0:
                    return ("Enrollment deleted successfully", 1)
                else:
                    return ("Enrollment not found", 0)
        except Exception as e:
            return (f"Error: {e}", 0)

class BatchCourse:

    @staticmethod
    def add_batch_course(batch_id, course_id, order_num):
        try:
            with Database.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO batch_courses (batch_id, course_id, order_num)
                    VALUES (%s, %s, %s)
                """, (batch_id, course_id, order_num))
            return ("BatchCourse entry added successfully", 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    @staticmethod
    def get_batch_course(batch_id, course_id):
        """Fetches a batch_course entry by its composite key."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("""
                    SELECT * FROM batch_courses WHERE batch_id = %s AND course_id = %s
                """, (batch_id, course_id))
                entry = cur.fetchone()
            if entry:
                return (entry, 1)
            else:
                return ("BatchCourse entry not found", 0)
        except Exception as e:
            return (f"Error: {e}", 0)

    @staticmethod
    def update_batch_course(batch_id, course_id, order_num=None):
        try:
            updates = []
            values = []
            if order_num is not None:
                updates.append("order_num = %s")
                values.append(order_num)
            if not updates:
                return ("No updates provided", 0)
            values.extend([batch_id, course_id])
            query = f"UPDATE batch_courses SET {', '.join(updates)} WHERE batch_id = %s AND course_id = %s"
            with Database.get_cursor() as cur:
                cur.execute(query, tuple(values))
            return ("BatchCourse entry updated successfully", 1)
        except Exception as e:
            return (f"Error: {e}", 0)

    @staticmethod
    def delete_batch_course(batch_id, course_id):
        """Deletes a batch_course entry."""
        try:
            with Database.get_cursor() as cur:
                cur.execute("DELETE FROM batch_courses WHERE batch_id = %s AND course_id = %s", (batch_id, course_id))
                if cur.rowcount > 0:
                    return ("BatchCourse entry deleted successfully", 1)
                else:
                    return ("BatchCourse entry not found", 0)
        except Exception as e:
            return (f"Error: {e}", 0)

class LiveClass:
    @staticmethod
    def create_live_class(batch_id, course_id, instructor_id, title, description, scheduled_at, jitsi_link):
        try:
            with Database.get_cursor() as cur:

                expired_at = scheduled_at + timedelta(hours=6)
                cur.execute("""
                    INSERT INTO live_classes (batch_id, course_id, instructor_id, title, description, scheduled_at, jitsi_link, expired_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (batch_id, course_id, instructor_id, title, description, scheduled_at, jitsi_link, expired_at))
                return cur.fetchone()[0], 1
        except Exception as e:
            return str(e), 0

    @staticmethod
    def delete_live_class(class_id, instructor_id):
        try:
            with Database.get_cursor() as cur:
                cur.execute("""
                    UPDATE live_classes
                    SET deleted_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND instructor_id = %s AND deleted_at IS NULL
                """, (class_id, instructor_id))
                return "Class deleted successfully", 1 if cur.rowcount > 0 else 0
        except Exception as e:
            return str(e), 0

    @staticmethod
    def filter_upcoming_classes(live_classes):
        current_time = datetime.now()
        three_hours_before = timedelta(hours=5)

        return [
            live_class for live_class in live_classes
            if live_class[5] > current_time - three_hours_before and (live_class[7] is None or live_class[7] > current_time)
        ]

    @staticmethod
    def get_live_classes_for_instructor(instructor_id):
        try:
            with Database.get_cursor() as cur:
                cur.execute("""
                    SELECT id, batch_id, course_id, title, description, scheduled_at, jitsi_link, expired_at
                    FROM live_classes
                    WHERE instructor_id = %s AND deleted_at IS NULL
                    ORDER BY scheduled_at ASC
                """, (instructor_id,))
                live_classes = cur.fetchall()

                live_classes = LiveClass.filter_upcoming_classes(live_classes)

                return live_classes, 1
        except Exception as e:
            return str(e), 0

    @staticmethod
    def get_live_classes_for_batch(batch_id):
        try:
            with Database.get_cursor() as cur:
                cur.execute("""
                    SELECT id, batch_id, course_id, title, description, scheduled_at, jitsi_link, expired_at
                    FROM live_classes
                    WHERE batch_id = %s AND deleted_at IS NULL
                    ORDER BY scheduled_at ASC
                """, (batch_id,))
                live_classes = cur.fetchall()

                live_classes = LiveClass.filter_upcoming_classes(live_classes)

                return live_classes, 1
        except Exception as e:
            return str(e), 0

class Auth:
    @staticmethod
    def login(identifier, password=None):
        print('a')
        """Authenticates a user across students, instructors, and admins."""
        try:
            with Database.get_cursor() as cur:
                user_data = None
                role = None

                if password:  
                    cur.execute("""
                        SELECT id, username, name, email, phone, enrollment_id, face_embedding 
                        FROM students 
                        WHERE (username = %s OR email = %s OR phone = %s OR id::TEXT = %s) 
                        AND password = %s AND deleted_at IS NULL
                    """, (identifier, identifier, identifier, identifier, password))
                else:  
                    cur.execute("""
                        SELECT id, username, name, email, phone, enrollment_id, face_embedding 
                        FROM students 
                        WHERE (username = %s OR email = %s OR google_id = %s) 
                        AND deleted_at IS NULL
                    """, (identifier, identifier, identifier))
                user = cur.fetchone()
                if user:
                    role = "student"
                    user_data = {
                        "role": role,
                        "id": user[0],
                        "username": user[1],
                        "name": user[2],
                        "email": user[3],
                        "phone": user[4],
                        "enrollment_id": user[5],
                        "face_embedding": user[6]  
                    }

                if not user_data:
                    if password:  
                        cur.execute("""
                            SELECT id, name, email, phone, username 
                            FROM instructors 
                            WHERE (username = %s OR email = %s OR phone = %s OR id::TEXT = %s) 
                            AND password = %s AND deleted_at IS NULL
                        """, (identifier, identifier, identifier, identifier, password))
                    else:  
                        cur.execute("""
                            SELECT id, name, email, phone, username 
                            FROM instructors 
                            WHERE (username = %s OR email = %s OR google_id = %s) 
                            AND deleted_at IS NULL
                        """, (identifier, identifier, identifier))
                    user = cur.fetchone()
                    if user:
                        role = "instructor"
                        user_data = {
                            "role": role,
                            "id": user[0],
                            "name": user[1],
                            "email": user[2],
                            "phone": user[3],
                            "username": user[4]
                        }

                if not user_data:
                    if password:  
                        cur.execute("""
                            SELECT id, username, name, email, phone 
                            FROM admins 
                            WHERE (username = %s OR email = %s OR phone = %s OR id::TEXT = %s) 
                            AND password = %s AND deleted_at IS NULL
                        """, (identifier, identifier, identifier, identifier, password))
                    else:  
                        cur.execute("""
                            SELECT id, username, name, email, phone 
                            FROM admins 
                            WHERE (username = %s OR email = %s OR google_id = %s) 
                            AND deleted_at IS NULL
                        """, (identifier, identifier, identifier))
                    user = cur.fetchone()
                    if user:
                        role = "admin"
                        user_data = {
                            "role": role,
                            "id": user[0],
                            "username": user[1],
                            "name": user[2],
                            "email": user[3],
                            "phone": user[4]
                        }

            if user_data:
                return (user_data, 1)
            else:
                return ("Invalid login credentials", 0)
        except Exception as e:
            return (f"Error: {e}", 0)

    @staticmethod
    def get_all_users():
        try:
            with Database.get_cursor() as cur:
                cur.execute("""
                    SELECT id, username, email, role, name, profile_picture 
                    FROM students WHERE deleted_at IS NULL
                    UNION
                    SELECT id, username, email, role, name, profile_picture 
                    FROM instructors WHERE deleted_at IS NULL
                    UNION
                    SELECT id, username, email, role, name, profile_picture 
                    FROM admins WHERE deleted_at IS NULL
                """)
                users = cur.fetchall()
                return [{'id': str(row[0]),
                         'username': row[1],
                         'email': row[2], 
                         'role': row[3], 
                         'name': row[4], 
                         'profile_picture': row[5]
                         } for row in users]
        except Exception as e:
            print(f"Error fetching users: {e}")
            return []

    @staticmethod
    def update_user_role(user_id, new_role):
        """Updates user role by moving them to the appropriate table and soft-deleting from the old one."""
        try:
            with Database.get_cursor() as cur:

                current_table = None
                user_data = None
                for table in ['students', 'instructors', 'admins']:
                    cur.execute(f"""
                        SELECT id, username, name, email, phone, password, profile_picture, role, google_id 
                        FROM {table} 
                        WHERE id = %s AND deleted_at IS NULL
                    """, (user_id,))
                    result = cur.fetchone()
                    if result:
                        current_table = table
                        user_data = {
                            'id': result[0],
                            'username': result[1],
                            'name': result[2],
                            'email': result[3],
                            'phone': result[4],
                            'password': result[5],
                            'profile_picture': result[6],
                            'role': result[7],
                            'google_id': result[8]
                        }
                        break

                if not user_data:
                    return False, "User not found"

                if user_data['role'] == new_role:
                    return True, "Role unchanged"

                target_table = {
                    'student': 'students',
                    'instructor': 'instructors',
                    'admin': 'admins'
                }.get(new_role)

                if not target_table:
                    return False, "Invalid role specified"

                if current_table != target_table:

                    cur.execute(f"""
                        SELECT id 
                        FROM {target_table} 
                        WHERE (username = %s OR email = %s OR google_id = %s) 
                        AND deleted_at IS NOT NULL
                    """, (user_data['username'], user_data['email'], user_data['google_id']))
                    existing_record = cur.fetchone()

                    new_id = None
                    if existing_record:

                        cur.execute(f"""
                            UPDATE {target_table}
                            SET role = %s, 
                                google_id = %s, 
                                phone = %s, 
                                name = %s, 
                                email = %s, 
                                username = %s, 
                                password = %s, 
                                profile_picture = %s, 
                                deleted_at = NULL, 
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                            RETURNING id
                        """, (new_role, user_data['google_id'], user_data['phone'], user_data['name'], 
                              user_data['email'], user_data['username'], user_data['password'], 
                              user_data['profile_picture'], existing_record[0]))
                        new_id = cur.fetchone()[0]
                    else:

                        if target_table == 'admins':
                            cur.execute("""
                                INSERT INTO admins (phone, username, name, email, password, profile_picture, role, google_id)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                RETURNING id
                            """, (user_data['phone'], user_data['username'], user_data['name'], user_data['email'],
                                  user_data['password'], user_data['profile_picture'], new_role, user_data['google_id']))
                        elif target_table == 'instructors':
                            cur.execute("""
                                INSERT INTO instructors (username, name, email, phone, password, profile_picture, role, google_id)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                RETURNING id
                            """, (user_data['username'], user_data['name'], user_data['email'], user_data['phone'],
                                  user_data['password'], user_data['profile_picture'], new_role, user_data['google_id']))
                        elif target_table == 'students':

                            cur.execute("""
                                INSERT INTO students (username, name, email, phone, enrollment_id, password, profile_picture, role, google_id)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                RETURNING id
                            """, (user_data['username'], user_data['name'], user_data['email'], user_data['phone'],
                                  f"ENR-{user_data['id']}", user_data['password'], user_data['profile_picture'], new_role, user_data['google_id']))
                        new_id = cur.fetchone()[0]

                    cur.execute(f"""
                        UPDATE {current_table} 
                        SET deleted_at = CURRENT_TIMESTAMP 
                        WHERE id = %s
                    """, (user_id,))

                    return True, f"User moved to {target_table} with ID: {new_id}"
                else:

                    cur.execute(f"""
                        UPDATE {current_table} 
                        SET role = %s, google_id = %s, updated_at = CURRENT_TIMESTAMP 
                        WHERE id = %s
                    """, (new_role, user_data['google_id'], user_id))
                    return True, "Role updated in same table"

        except Exception as e:
            print(f"Error updating user role: {e}")
            return False, str(e)

    @staticmethod
    def delete_user(user_id):
        """Soft deletes a user from their respective table."""
        try:
            with Database.get_cursor() as cur:
                for table in ['students', 'instructors', 'admins']:
                    cur.execute(f"""
                        UPDATE {table} 
                        SET deleted_at = CURRENT_TIMESTAMP 
                        WHERE id = %s AND deleted_at IS NULL
                    """, (user_id,))
                    if cur.rowcount > 0:
                        return True
                return False
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False