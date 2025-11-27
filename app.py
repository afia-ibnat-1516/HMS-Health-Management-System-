from flask import Flask, request, redirect, send_from_directory, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"

# -----------------------------
# Project Folder
# -----------------------------
BASE_FOLDER = r"D:\SD2 Project"  # change to your project path

# -----------------------------
# MySQL Connection
# -----------------------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="naifa19",  # your password
    database="hms_db"
)
cursor = db.cursor(dictionary=True)

# -----------------------------
# Routes - Static Pages
# -----------------------------
@app.route("/")
def home():
    return send_from_directory(BASE_FOLDER, "index.html")

@app.route("/index.html")
def index():
    return send_from_directory(BASE_FOLDER, "index.html")

@app.route("/login.html")
def login_page():
    return send_from_directory(BASE_FOLDER, "login.html")

@app.route("/main.html")
def main_page():
    if "user_id" not in session:
        return redirect("/login.html")
    return send_from_directory(BASE_FOLDER, "main.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(BASE_FOLDER, filename)

# -----------------------------
# Signup
# -----------------------------
@app.route("/signup", methods=["POST"])
def signup():
    full_name = request.form["full_name"]
    email = request.form["email"]
    password = request.form["password"]
    hashed = generate_password_hash(password)

    try:
        cursor.execute(
            "INSERT INTO users (full_name, email, password) VALUES (%s, %s, %s)",
            (full_name, email, hashed)
        )
        db.commit()
        return redirect("/login.html")
    except mysql.connector.IntegrityError:
        return "Email already exists!"

# -----------------------------
# Login
# -----------------------------
@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()

    if user and check_password_hash(user["password"], password):
        session["user_id"] = user["id"]
        session["full_name"] = user["full_name"]
        return redirect("/main.html")
    return "Invalid email or password!"

@app.route('/profile')
def profile_page():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"})

    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT full_name, email, password FROM users WHERE id=%s",
        (session['user_id'],)
    )
    user = cursor.fetchone()

    if user:
        # return full_name as 'name' so JS can use it
        return jsonify({
            "name": user['full_name'],
            "email": user['email'],
            "password": user['password']
        })
    return jsonify({"error": "user not found"})

@app.route('/update_password', methods=['POST'])
def update_password():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Not logged in"})

    data = request.get_json()
    new_pass = data.get('new_password')
    confirm_pass = data.get('confirm_password')

    if not new_pass or new_pass != confirm_pass:
        return jsonify({"status": "error", "message": "Passwords do not match"})

    cursor = db.cursor()
    cursor.execute(
        "UPDATE users SET password=%s WHERE id=%s",
        (new_pass, session['user_id'])
    )
    db.commit()

    return jsonify({"status": "success", "message": "Password updated successfully"})


# -----------------------------
# Logout
# -----------------------------
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()  # Remove all session data
    return jsonify({"status": "success", "message": "Logged out successfully"})

# ------------------- Nutrition Records -------------------
@app.route('/nutrition/add', methods=['POST'])
def add_nutrition():
    if 'user_id' not in session:
        return jsonify({"status":"fail","message":"Login required"}), 401

    data = request.get_json()
    cursor.execute(
        "INSERT INTO nutrition_records (user_id, food_item, record_date, calorie) VALUES (%s, %s, %s, %s)",
        (session['user_id'], data['food_item'], data['record_date'], data['calorie'])
    )
    db.commit()
    return jsonify({"status":"success"})

@app.route('/nutrition/list', methods=['GET'])
def list_nutrition():
    if 'user_id' not in session:
        return jsonify([])
    cursor.execute("SELECT * FROM nutrition_records WHERE user_id=%s ORDER BY record_date DESC", (session['user_id'],))
    return jsonify(cursor.fetchall())

# DELETE a nutrition record (only if it belongs to logged-in user)
@app.route('/nutrition/delete/<int:record_id>', methods=['DELETE'])
def delete_nutrition(record_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401

    try:
        # Note: using the global cursor (dictionary=True) is fine for deletes
        cursor.execute(
            "DELETE FROM nutrition_records WHERE id = %s AND user_id = %s",
            (record_id, session['user_id'])
        )
        db.commit()

        if cursor.rowcount == 0:
            # nothing deleted — either id doesn't exist or belongs to another user
            return jsonify({'status': 'error', 'message': 'Record not found or not allowed'}), 404

        return jsonify({'status': 'success'})
    except Exception as e:
        # log error to server console for debugging
        print("Delete error:", e)
        return jsonify({'status': 'error', 'message': 'Server error'}), 500

# ------------------- Medication Records -------------------

@app.route('/medication/add', methods=['POST'])
def add_medication():
    if 'user_id' not in session:
        return jsonify({"status": "fail", "message": "Login required"}), 401

    data = request.get_json()

    cursor.execute("""
        INSERT INTO medication_history 
        (user_id, name, age, gender, medication, dosage, time_taken, date_taken, exercise_per_day, exercise_per_week)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        session['user_id'],
        data['name'],
        data['age'],
        data['gender'],
        data['medication'],
        data['dosage'],
        data['time'],
        data['date'],
        data['exercisePerDay'],
        data['exercisePerWeek']
    ))
    db.commit()

    return jsonify({"status": "success"})

@app.route('/medication/list')
def list_medication():
    if 'user_id' not in session:
        return jsonify([])

    cursor.execute("""
        SELECT * FROM medication_history 
        WHERE user_id=%s ORDER BY id DESC
    """, (session['user_id'],))

    return jsonify(cursor.fetchall())

@app.route('/medication/delete/<int:record_id>', methods=['DELETE'])
def delete_medication(record_id):
    if 'user_id' not in session:
        return jsonify({"status": "fail"}), 401

    cursor.execute("DELETE FROM medication_history WHERE id=%s AND user_id=%s",
                   (record_id, session['user_id']))
    db.commit()

    return jsonify({"status": "success"})

# ------------------- SYMPTOM TRACKER -------------------

@app.route('/symptom/add', methods=['POST'])
def add_symptom():
    if 'user_id' not in session:
        return jsonify({"status": "fail", "message": "Login required"}), 401

    data = request.get_json()

    cursor.execute("""
        INSERT INTO symptom_records (user_id, name, age, gender, symptoms)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        session['user_id'],
        data['name'],
        data['age'],
        data['gender'],
        data['symptoms']
    ))

    db.commit()

    return jsonify({"status": "success"})

@app.route('/symptom/list')
def symptom_list():
    if 'user_id' not in session:
        return jsonify([])

    cursor.execute("""
        SELECT * FROM symptom_records
        WHERE user_id = %s
        ORDER BY id DESC
    """, (session['user_id'],))

    records = cursor.fetchall()

    return jsonify(records)

@app.route('/symptom/delete/<int:record_id>', methods=['DELETE'])
def symptom_delete(record_id):
    if 'user_id' not in session:
        return jsonify({"status": "fail"}), 401

    cursor.execute("""
        DELETE FROM symptom_records
        WHERE id = %s AND user_id = %s
    """, (record_id, session['user_id']))

    db.commit()

    return jsonify({"status": "success"})

# ------------------- Appointment Records -------------------

@app.route('/appointments/add', methods=['POST'])
def add_appointment():
    if 'user_id' not in session:
        return jsonify({"status": "fail", "message": "Login required"}), 401

    data = request.get_json()
    name = data.get("patient_name")
    if not name:
        return jsonify({"status": "fail", "message": "Appointment name required"}), 400

    cursor.execute(
        "INSERT INTO appointments (user_id, patient_name) VALUES (%s, %s)",
        (session['user_id'], name)
    )
    db.commit()
    return jsonify({"status": "success"})

# -----------------------------
# List Appointments
# -----------------------------
@app.route('/appointments/list', methods=['GET'])
def list_appointments():
    if 'user_id' not in session:
        return jsonify([]), 401

    cursor.execute(
        "SELECT id, patient_name FROM appointments WHERE user_id=%s ORDER BY id DESC",
        (session['user_id'],)
    )
    records = cursor.fetchall()
    return jsonify(records)

# -----------------------------
# Delete Appointment (optional)
# -----------------------------
@app.route('/appointments/delete/<int:record_id>', methods=['DELETE'])
def delete_appointment(record_id):
    if 'user_id' not in session:
        return jsonify({"status": "fail"}), 401

    cursor.execute(
        "DELETE FROM appointments WHERE id=%s AND user_id=%s",
        (record_id, session['user_id'])
    )
    db.commit()
    return jsonify({"status": "success"})


# ------------------- Workout Plans -------------------
@app.route('/workout/add', methods=['POST'])
def add_workout():
    if 'user_id' not in session:
        return jsonify({"status": "fail", "message": "Login required"}), 401

    data = request.get_json()
    cursor.execute("""
        INSERT INTO workout_plans (user_id, age, exercise_type, duration)
        VALUES (%s, %s, %s, %s)
    """, (
        session['user_id'],
        data['age'],
        data['exerciseType'],
        data['duration']
    ))
    db.commit()
    return jsonify({"status": "success"})


@app.route('/workout/list', methods=['GET'])
def list_workouts():
    if 'user_id' not in session:
        return jsonify([])

    dict_cursor = db.cursor(dictionary=True)
    dict_cursor.execute("""
        SELECT * FROM workout_plans
        WHERE user_id=%s
        ORDER BY created_at DESC
    """, (session['user_id'],))
    workouts = dict_cursor.fetchall()
    dict_cursor.close()

    return jsonify(workouts)


@app.route('/workout/delete/<int:record_id>', methods=['DELETE'])
def delete_workout(record_id):
    if 'user_id' not in session:
        return jsonify({"status": "fail", "message": "Unauthorized"}), 401

    try:
        cursor.execute("""
            DELETE FROM workout_plans
            WHERE id=%s AND user_id=%s
        """, (record_id, session['user_id']))
        db.commit()

        if cursor.rowcount == 0:
            return jsonify({'status': 'fail', 'message': 'Record not found or not allowed'}), 404

        return jsonify({'status': 'success'})
    except Exception as e:
        print("DeleteWorkout error:", e)
        return jsonify({'status': 'error', 'message': 'Server error'}), 500

# ------------------- Serve all other files -------------------
@app.route("/<path:filename>")
def serve_file(filename):
    return send_from_directory(BASE_FOLDER, filename)

# ------------------- Run App -------------------
if __name__ == "__main__":
    app.run(debug=True)

