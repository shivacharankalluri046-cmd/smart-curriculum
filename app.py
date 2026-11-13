
import os
from datetime import date
from functools import wraps

import mysql.connector
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, session
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv(
    "SECRET_KEY",
    "smart_curriculum_secret_key"
)


# DATABASE CONNECTION
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "smart_curriculum")
    )


# LOGIN REQUIRED
def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "error")
            return redirect(url_for("login"))
        return function(*args, **kwargs)
    return wrapper


# DASHBOARD
@app.route("/")
@login_required
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT a.id, a.title, a.description,
                   a.status, a.due_date, s.subject_name
            FROM assignments a
            LEFT JOIN subjects s ON a.subject_id = s.id
            WHERE a.user_id = %s
            ORDER BY a.due_date ASC
        """, (session["user_id"],))

        activities = cursor.fetchall()
        today = date.today()

        total = len(activities)
        completed = sum(
            1 for a in activities
            if a["status"] == "Completed"
        )
        pending = sum(
            1 for a in activities
            if a["status"] == "Pending"
        )
        overdue = sum(
            1 for a in activities
            if a["due_date"]
            and a["due_date"] < today
            and a["status"] != "Completed"
        )
        due_today = sum(
            1 for a in activities
            if a["due_date"] == today
            and a["status"] != "Completed"
        )
        upcoming = sum(
            1 for a in activities
            if a["due_date"]
            and a["due_date"] > today
            and a["status"] != "Completed"
        )

        progress = round(completed / total * 100) if total else 0

        return render_template(
            "index.html",
            activities=activities,
            total_activities=total,
            completed_activities=completed,
            pending_activities=pending,
            overdue_activities=overdue,
            due_today=due_today,
            upcoming_activities=upcoming,
            progress=progress
        )
    finally:
        cursor.close()
        conn.close()


# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill all fields.", "error")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
            return redirect(url_for("register"))

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT id FROM users WHERE email = %s",
                (email,)
            )

            if cursor.fetchone():
                flash("Email already registered.", "error")
                return redirect(url_for("register"))

            hashed_password = generate_password_hash(password)

            cursor.execute("""
                INSERT INTO users (name, email, password, role)
                VALUES (%s, %s, %s, 'Student')
            """, (name, email, hashed_password))

            conn.commit()

            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))
        finally:
            cursor.close()
            conn.close()

    return render_template("register.html")


# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT id, name, email, password, role
                FROM users
                WHERE email = %s
            """, (email,))

            user = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]

            return redirect(url_for("home"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


# ADD ACTIVITY
@app.route("/add", methods=["POST"])
@login_required
def add_activity():
    title = request.form.get("title", "").strip()
    subject = request.form.get("subject", "").strip()
    description = request.form.get("description", "").strip()
    due_date = request.form.get("deadline") or None

    if not title or not subject:
        flash("Title and subject are required.", "error")
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id FROM subjects WHERE subject_name = %s",
            (subject,)
        )
        result = cursor.fetchone()

        if result:
            subject_id = result[0]
        else:
            cursor.execute(
                "INSERT INTO subjects (subject_name) VALUES (%s)",
                (subject,)
            )
            subject_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO assignments
            (user_id, title, description, subject_id, status, due_date)
            VALUES (%s, %s, %s, %s, 'Pending', %s)
        """, (
            session["user_id"],
            title,
            description,
            subject_id,
            due_date
        ))

        conn.commit()
        flash("Activity added successfully.", "success")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("home"))


# EDIT ACTIVITY
@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_activity(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT a.*, s.subject_name
            FROM assignments a
            LEFT JOIN subjects s ON a.subject_id = s.id
            WHERE a.id = %s AND a.user_id = %s
        """, (id, session["user_id"]))

        activity = cursor.fetchone()

        if not activity:
            flash("Activity not found.", "error")
            return redirect(url_for("home"))

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            subject = request.form.get("subject", "").strip()
            description = request.form.get("description", "").strip()
            due_date = request.form.get("deadline") or None

            if not title or not subject:
                flash("Title and subject are required.", "error")
                return redirect(url_for("edit_activity", id=id))

            cursor.execute(
                "SELECT id FROM subjects WHERE subject_name = %s",
                (subject,)
            )
            result = cursor.fetchone()

            if result:
                subject_id = result["id"]
            else:
                cursor.execute(
                    "INSERT INTO subjects (subject_name) VALUES (%s)",
                    (subject,)
                )
                subject_id = cursor.lastrowid

            cursor.execute("""
                UPDATE assignments
                SET title=%s, description=%s,
                    subject_id=%s, due_date=%s
                WHERE id=%s AND user_id=%s
            """, (
                title,
                description,
                subject_id,
                due_date,
                id,
                session["user_id"]
            ))

            conn.commit()
            flash("Activity updated successfully.", "success")
            return redirect(url_for("home"))

        return render_template("edit.html", activity=activity)
    finally:
        cursor.close()
        conn.close()


# DELETE ACTIVITY
@app.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete_activity(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM results
            WHERE assignment_id = %s AND user_id = %s
        """, (id, session["user_id"]))

        cursor.execute("""
            DELETE FROM assignments
            WHERE id = %s AND user_id = %s
        """, (id, session["user_id"]))

        conn.commit()

        if cursor.rowcount:
            flash("Activity deleted successfully.", "success")
        else:
            flash("Activity not found.", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("home"))


# COMPLETE ACTIVITY
@app.route("/complete/<int:id>", methods=["POST"])
@login_required
def complete_activity(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE assignments
            SET status = 'Completed'
            WHERE id = %s AND user_id = %s
        """, (id, session["user_id"]))

        conn.commit()

        if cursor.rowcount:
            flash("Activity completed successfully.", "success")
        else:
            flash("Activity not found.", "error")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("home"))


# PROFILE
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, name, email, role, password
            FROM users
            WHERE id = %s
        """, (session["user_id"],))

        user = cursor.fetchone()

        if not user:
            session.clear()
            return redirect(url_for("login"))

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")

            if not name or not email:
                flash("Name and email are required.", "error")
                return redirect(url_for("profile"))

            cursor.execute("""
                SELECT id FROM users
                WHERE email = %s AND id != %s
            """, (email, session["user_id"]))

            if cursor.fetchone():
                flash("Email already in use.", "error")
                return redirect(url_for("profile"))

            if new_password:
                if not check_password_hash(
                    user["password"], current_password
                ):
                    flash("Current password is incorrect.", "error")
                    return redirect(url_for("profile"))

                if len(new_password) < 8:
                    flash(
                        "New password must be at least 8 characters.",
                        "error"
                    )
                    return redirect(url_for("profile"))

                hashed_password = generate_password_hash(new_password)

                cursor.execute("""
                    UPDATE users
                    SET name=%s, email=%s, password=%s
                    WHERE id=%s
                """, (
                    name,
                    email,
                    hashed_password,
                    session["user_id"]
                ))
            else:
                cursor.execute("""
                    UPDATE users
                    SET name=%s, email=%s
                    WHERE id=%s
                """, (name, email, session["user_id"]))

            conn.commit()
            session["user_name"] = name

            flash("Profile updated successfully.", "success")
            return redirect(url_for("profile"))

        return render_template("profile.html", user=user)
    finally:
        cursor.close()
        conn.close()


# REPORT
@app.route("/report")
@login_required
def report():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT a.title, a.description, a.status,
                   a.due_date, s.subject_name
            FROM assignments a
            LEFT JOIN subjects s ON a.subject_id = s.id
            WHERE a.user_id = %s
            ORDER BY a.due_date ASC
        """, (session["user_id"],))

        activities = cursor.fetchall()

        total = len(activities)
        completed = sum(
            1 for a in activities
            if a["status"] == "Completed"
        )
        pending = sum(
            1 for a in activities
            if a["status"] == "Pending"
        )

        progress = round(completed / total * 100) if total else 0

        return render_template(
            "report.html",
            activities=activities,
            total=total,
            completed=completed,
            pending=pending,
            progress=progress
        )
    finally:
        cursor.close()
        conn.close()


# RUN APPLICATION
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
