# ============================================
# IMPORTS
# ============================================
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
from functools import wraps

# ============================================
# APP CONFIGURATION
# ============================================
app = Flask(__name__)
app.secret_key = 'change-this-secret-key-in-production'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'  # Enter your MySQL password
app.config['MYSQL_DB'] = 'project'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

# ============================================
# GLOBAL VARIABLES
# ============================================
SYMPTOMS = [
    'fever', 'headache', 'nausea', 'vomiting', 'fatigue',
    'joint_pain', 'skin_rash', 'cough', 'weight_loss', 'yellow_eyes'
]

# ============================================
# HELPER FUNCTIONS & DECORATORS
# ============================================
def format_time_from_timedelta(td):
    """Convert timedelta to formatted time string"""
    if td is None:
        return ""
    
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    # Convert to 12-hour format
    period = "AM"
    if hours >= 12:
        period = "PM"
        if hours > 12:
            hours -= 12
    elif hours == 0:
        hours = 12
    
    return f"{hours:02d}:{minutes:02d} {period}"

# Register Jinja filter
app.jinja_env.filters['format_time'] = format_time_from_timedelta

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        
        # Check if user is admin
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT is_admin FROM users WHERE user_id = %s', (session['user_id'],))
        user = cursor.fetchone()
        cursor.close()
        
        if not user or not user['is_admin']:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# AUTHENTICATION ROUTES
# ============================================

# Home route
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Please enter both email and password', 'error')
            return render_template('login.html')
        
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['full_name'] = user['full_name']
            session['email'] = user['email']
            session['is_admin'] = bool(user['is_admin'])
            flash(f'Welcome back, {user["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

# Admin Login (Separate)
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    # If already logged in as admin, redirect to reports
    if 'user_id' in session and session.get('is_admin'):
        return redirect(url_for('reports'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Please enter both email and password', 'error')
            return render_template('admin_login.html')
        
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        
        # Verify user exists, password matches, AND is admin
        if user and check_password_hash(user['password'], password):
            if user['is_admin']:
                # Set session
                session['user_id'] = user['user_id']
                session['full_name'] = user['full_name']
                session['email'] = user['email']
                session['is_admin'] = True
                
                flash(f'Welcome, Administrator {user["full_name"]}!', 'success')
                return redirect(url_for('reports'))  # Go directly to reports
            else:
                flash('Access denied. Admin privileges required.', 'error')
                return render_template('admin_login.html')
        else:
            flash('Invalid admin credentials', 'error')
            return render_template('admin_login.html')
    
    return render_template('admin_login.html')

# Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        age = request.form.get('age', '').strip()
        gender = request.form.get('gender', '')
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not all([full_name, email, phone, age, gender, password, confirm_password]):
            flash('Please fill in all fields', 'error')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('signup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return render_template('signup.html')
        
        try:
            age = int(age)
            if age < 1 or age > 150:
                flash('Please enter a valid age', 'error')
                return render_template('signup.html')
        except ValueError:
            flash('Please enter a valid age', 'error')
            return render_template('signup.html')
        
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT user_id FROM users WHERE email = %s', (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            flash('Email already registered. Please login.', 'error')
            cursor.close()
            return render_template('signup.html')
        
        hashed_password = generate_password_hash(password)
        
        try:
            cursor.execute('''
                INSERT INTO users (full_name, email, phone, age, gender, password)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (full_name, email, phone, age, gender, hashed_password))
            mysql.connection.commit()
            
            new_user_id = cursor.lastrowid
            cursor.close()
            
            session['success_message'] = f'🎉 Registration successful! Your User ID is: {new_user_id}'
            session['success_redirect'] = url_for('login')
            return redirect(url_for('success'))
            
        except Exception as e:
            mysql.connection.rollback()
            cursor.close()
            flash('Registration failed. Please try again.', 'error')
            print(f"Error: {e}")
            return render_template('signup.html')
    
    return render_template('signup.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

# ============================================
# DASHBOARD & PROFILE ROUTES
# ============================================

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login to access dashboard', 'error')
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    cursor.execute('''
        SELECT assessment_id, assessment_date, predicted_disease, match_percentage
        FROM assessments
        WHERE user_id = %s
        ORDER BY assessment_date DESC
        LIMIT 5
    ''', (session['user_id'],))
    recent_assessments = cursor.fetchall()
    cursor.close()
    
    return render_template('dashboard.html', 
                         user_id=session['user_id'],
                         full_name=session['full_name'],
                         recent_assessments=recent_assessments)

# Edit Profile
@app.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        age = request.form.get('age', '').strip()
        gender = request.form.get('gender', '')
        
        if not all([full_name, phone, age, gender]):
            flash('Please fill in all fields', 'error')
            return redirect(url_for('edit_profile'))
        
        try:
            age = int(age)
            if age < 1 or age > 150:
                flash('Please enter a valid age', 'error')
                return redirect(url_for('edit_profile'))
        except ValueError:
            flash('Please enter a valid age', 'error')
            return redirect(url_for('edit_profile'))
        
        try:
            cursor.execute('''
                UPDATE users 
                SET full_name = %s, phone = %s, age = %s, gender = %s
                WHERE user_id = %s
            ''', (full_name, phone, age, gender, session['user_id']))
            mysql.connection.commit()
            
            session['full_name'] = full_name
            session['success_message'] = '✅ Profile updated successfully!'
            session['success_redirect'] = url_for('dashboard')
            return redirect(url_for('success'))
        except Exception as e:
            mysql.connection.rollback()
            flash('Update failed. Please try again.', 'error')
            print(f"Error: {e}")
    
    cursor.execute('SELECT * FROM users WHERE user_id = %s', (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    
    return render_template('edit_profile.html', user=user)

# ============================================
# SYMPTOM CHECKER & ASSESSMENT ROUTES
# ============================================

# Symptom Checker
@app.route('/symptom-checker')
def symptom_checker():
    if 'user_id' not in session:
        flash('Please login to access symptom checker', 'error')
        return redirect(url_for('login'))
    
    return render_template('symptom_checker.html', symptoms=SYMPTOMS)

# Predict Disease
@app.route('/predict', methods=['POST'])
def predict():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    selected_symptoms = request.form.getlist('symptoms')
    
    if not selected_symptoms:
        flash('Please select at least one symptom', 'error')
        return redirect(url_for('symptom_checker'))
    
    user_symptoms = {}
    for symptom in SYMPTOMS:
        user_symptoms[symptom] = 1 if symptom in selected_symptoms else 0
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM disease_symptoms")
    all_patterns = cursor.fetchall()
    
    matches = []
    for pattern in all_patterns:
        score = 0
        total_symptoms = sum(user_symptoms.values())
        
        for symptom in SYMPTOMS:
            if user_symptoms[symptom] == 1 and pattern[symptom] == 1:
                score += 1
        
        if total_symptoms > 0:
            match_percentage = (score / total_symptoms) * 100
        else:
            match_percentage = 0
        
        if score > 0:
            matches.append({
                'disease': pattern['disease'],
                'match_percentage': round(match_percentage, 2),
                'matched_symptoms': score,
                'total_selected': total_symptoms
            })
    
    matches.sort(key=lambda x: x['match_percentage'], reverse=True)
    
    if matches:
        top_match = matches[0]
        
        cursor.execute('''
            INSERT INTO assessments (user_id, selected_symptoms, predicted_disease, match_percentage)
            VALUES (%s, %s, %s, %s)
        ''', (
            session['user_id'],
            json.dumps(selected_symptoms),
            top_match['disease'],
            top_match['match_percentage']
        ))
        mysql.connection.commit()
        assessment_id = cursor.lastrowid
        cursor.close()
        
        return render_template('results.html', 
                             matches=matches[:5],
                             selected_symptoms=selected_symptoms,
                             assessment_id=assessment_id)
    else:
        cursor.close()
        flash('No matching diseases found. Please consult a doctor.', 'error')
        return redirect(url_for('symptom_checker'))

# Assessment History
@app.route('/history')
def history():
    if 'user_id' not in session:
        flash('Please login to view history', 'error')
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    cursor.execute('''
        SELECT assessment_id, assessment_date, selected_symptoms, 
               predicted_disease, match_percentage
        FROM assessments
        WHERE user_id = %s
        ORDER BY assessment_date DESC
    ''', (session['user_id'],))
    assessments = cursor.fetchall()
    cursor.close()
    
    for assessment in assessments:
        assessment['selected_symptoms'] = json.loads(assessment['selected_symptoms'])
    
    return render_template('history.html', assessments=assessments)

# Delete Assessment
@app.route('/delete-assessment/<int:assessment_id>', methods=['POST'])
def delete_assessment(assessment_id):
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute('''
            DELETE FROM assessments 
            WHERE assessment_id = %s AND user_id = %s
        ''', (assessment_id, session['user_id']))
        mysql.connection.commit()
        cursor.close()
        
        flash('Assessment deleted successfully!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        flash('Deletion failed. Please try again.', 'error')
        print(f"Error: {e}")
    
    return redirect(url_for('history'))

# ============================================
# DOCTOR SEARCH & BOOKING ROUTES
# ============================================

# Find Doctors
@app.route('/find-doctors/<int:assessment_id>')
def find_doctors(assessment_id):
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    
    cursor.execute('''
        SELECT predicted_disease, selected_symptoms
        FROM assessments
        WHERE assessment_id = %s AND user_id = %s
    ''', (assessment_id, session['user_id']))
    assessment = cursor.fetchone()
    
    if not assessment:
        flash('Assessment not found', 'error')
        return redirect(url_for('dashboard'))
    
    disease_name = assessment['predicted_disease']
    selected_symptoms = json.loads(assessment['selected_symptoms'])
    
    city = request.args.get('city', '').strip()
    state = request.args.get('state', '').strip()
    
    doctors = []
    search_performed = False
    search_result_message = None
    
    if city:
        search_performed = True
        
        query = '''
            SELECT DISTINCT d.*, s.specialization_name
            FROM doctors d
            JOIN specializations s ON d.specialization_id = s.specialization_id
            JOIN disease_specialization ds ON s.specialization_id = ds.specialization_id
            WHERE ds.disease_name = %s
            AND LOWER(d.city) = LOWER(%s)
        '''
        params = [disease_name, city]
        
        if state:
            query += ' AND LOWER(d.state) = LOWER(%s)'
            params.append(state)
        
        query += ' ORDER BY d.rating DESC, d.experience_years DESC'
        
        cursor.execute(query, params)
        doctors = cursor.fetchall()
        
        if doctors:
            search_result_message = {
                'type': 'success',
                'text': f'Found {len(doctors)} specialist(s) in {city.title()}'
            }
        else:
            if state:
                cursor.execute('''
                    SELECT DISTINCT d.*, s.specialization_name
                    FROM doctors d
                    JOIN specializations s ON d.specialization_id = s.specialization_id
                    JOIN disease_specialization ds ON s.specialization_id = ds.specialization_id
                    WHERE ds.disease_name = %s
                    AND LOWER(d.state) = LOWER(%s)
                    AND LOWER(d.city) != LOWER(%s)
                    ORDER BY d.rating DESC, d.experience_years DESC
                    LIMIT 10
                ''', (disease_name, state, city))
                nearby_doctors = cursor.fetchall()
            else:
                nearby_doctors = []
            
            cursor.execute('''
                SELECT DISTINCT d.*, s.specialization_name
                FROM doctors d
                JOIN specializations s ON d.specialization_id = s.specialization_id
                JOIN disease_specialization ds ON s.specialization_id = ds.specialization_id
                WHERE ds.disease_name = %s
                AND (LOWER(d.city) != LOWER(%s) OR LOWER(d.state) != LOWER(%s))
                ORDER BY d.rating DESC, d.experience_years DESC
                LIMIT 15
            ''', (disease_name, city, state if state else ''))
            other_city_doctors = cursor.fetchall()
            
            if nearby_doctors:
                search_result_message = {
                    'type': 'warning',
                    'text': f'No specialists found in {city.title()}. Showing {len(nearby_doctors)} specialist(s) in other cities of {state.title()}'
                }
                doctors = nearby_doctors
            elif other_city_doctors:
                search_result_message = {
                    'type': 'info',
                    'text': f'No specialists found in {city.title()}. Showing {len(other_city_doctors)} specialist(s) from other cities across India'
                }
                doctors = other_city_doctors
            else:
                search_result_message = {
                    'type': 'error',
                    'text': f'No specialists found for {disease_name}. Please consult a general physician.'
                }
    
    cursor.close()
    
    return render_template('find_doctors.html',
                         assessment_id=assessment_id,
                         disease_name=disease_name,
                         doctors=doctors,
                         search_performed=search_performed,
                         search_result_message=search_result_message)
                         

# Book Appointment
@app.route('/book-appointment/<int:doctor_id>/<int:assessment_id>', methods=['GET', 'POST'])
def book_appointment(doctor_id, assessment_id):
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    
    cursor.execute('''
        SELECT d.*, s.specialization_name
        FROM doctors d
        JOIN specializations s ON d.specialization_id = s.specialization_id
        WHERE d.doctor_id = %s
    ''', (doctor_id,))
    doctor = cursor.fetchone()
    
    if not doctor:
        flash('Doctor not found', 'error')
        return redirect(url_for('dashboard'))
    
    cursor.execute('''
        SELECT predicted_disease, selected_symptoms
        FROM assessments
        WHERE assessment_id = %s AND user_id = %s
    ''', (assessment_id, session['user_id']))
    assessment = cursor.fetchone()
    
    if request.method == 'POST':
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        notes = request.form.get('notes', '')
        
        if not appointment_date or not appointment_time:
            flash('Please select date and time', 'error')
            return redirect(url_for('book_appointment', doctor_id=doctor_id, assessment_id=assessment_id))
        
        try:
            cursor.execute('''
                INSERT INTO appointments 
                (user_id, doctor_id, assessment_id, appointment_date, 
                 appointment_time, disease_name, symptoms, notes, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Pending')
            ''', (
                session['user_id'],
                doctor_id,
                assessment_id,
                appointment_date,
                appointment_time,
                assessment['predicted_disease'],
                json.dumps(json.loads(assessment['selected_symptoms'])),
                notes
            ))
            mysql.connection.commit()
            appointment_id = cursor.lastrowid
            cursor.close()
            
            session['success_message'] = f'✅ Appointment booked successfully! Appointment ID: #{appointment_id}'
            session['success_redirect'] = url_for('my_appointments')
            return redirect(url_for('success'))
            
        except Exception as e:
            mysql.connection.rollback()
            cursor.close()
            flash('Booking failed. Please try again.', 'error')
            print(f"Error: {e}")
            return redirect(url_for('book_appointment', doctor_id=doctor_id, assessment_id=assessment_id))
    
    min_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    cursor.close()
    
    return render_template('book_appointment.html',
                         doctor=doctor,
                         assessment_id=assessment_id,
                         disease_name=assessment['predicted_disease'],
                         symptoms=json.loads(assessment['selected_symptoms']),
                         min_date=min_date)

# ============================================
# APPOINTMENT MANAGEMENT ROUTES
# ============================================

# My Appointments
@app.route('/my-appointments')
def my_appointments():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    cursor.execute('''
        SELECT a.*, d.full_name as doctor_name, d.hospital_name, 
               d.city, s.specialization_name
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.doctor_id
        JOIN specializations s ON d.specialization_id = s.specialization_id
        WHERE a.user_id = %s
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
    ''', (session['user_id'],))
    appointments = cursor.fetchall()
    cursor.close()
    
    for appointment in appointments:
        appointment['symptoms'] = json.loads(appointment['symptoms'])
        
        time_obj = appointment['appointment_time']
        if time_obj:
            total_seconds = int(time_obj.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            
            period = "AM"
            display_hour = hours
            
            if hours >= 12:
                period = "PM"
                if hours > 12:
                    display_hour = hours - 12
            if hours == 0:
                display_hour = 12
                
            appointment['formatted_time'] = f"{display_hour:02d}:{minutes:02d} {period}"
        else:
            appointment['formatted_time'] = "N/A"
    
    return render_template('my_appointments.html', appointments=appointments)

# Reschedule Appointment
@app.route('/reschedule-appointment/<int:appointment_id>', methods=['GET', 'POST'])
def reschedule_appointment(appointment_id):
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    
    cursor.execute('''
        SELECT a.*, d.full_name as doctor_name, s.specialization_name
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.doctor_id
        JOIN specializations s ON d.specialization_id = s.specialization_id
        WHERE a.appointment_id = %s AND a.user_id = %s
    ''', (appointment_id, session['user_id']))
    appointment = cursor.fetchone()
    
    if not appointment:
        flash('Appointment not found', 'error')
        return redirect(url_for('my_appointments'))
    
    if request.method == 'POST':
        new_date = request.form.get('appointment_date')
        new_time = request.form.get('appointment_time')
        notes = request.form.get('notes', '')
        
        if not new_date or not new_time:
            flash('Please select new date and time', 'error')
            return redirect(url_for('reschedule_appointment', appointment_id=appointment_id))
        
        try:
            cursor.execute('''
                UPDATE appointments 
                SET appointment_date = %s, appointment_time = %s, notes = %s, status = 'Pending'
                WHERE appointment_id = %s AND user_id = %s
            ''', (new_date, new_time, notes, appointment_id, session['user_id']))
            mysql.connection.commit()
            cursor.close()
            
            flash('Appointment rescheduled successfully!', 'success')
            return redirect(url_for('my_appointments'))
        except Exception as e:
            mysql.connection.rollback()
            cursor.close()
            flash('Rescheduling failed. Please try again.', 'error')
            print(f"Error: {e}")
            return redirect(url_for('reschedule_appointment', appointment_id=appointment_id))
    
    cursor.close()
    min_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    return render_template('reschedule_appointment.html', 
                         appointment=appointment, 
                         min_date=min_date)

# Update Appointment Status
@app.route('/update-appointment-status/<int:appointment_id>/<status>')
def update_appointment_status(appointment_id, status):
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    allowed_statuses = ['Confirmed', 'Completed', 'Cancelled']
    if status not in allowed_statuses:
        flash('Invalid status', 'error')
        return redirect(url_for('my_appointments'))
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute('''
            UPDATE appointments 
            SET status = %s
            WHERE appointment_id = %s AND user_id = %s
        ''', (status, appointment_id, session['user_id']))
        mysql.connection.commit()
        cursor.close()
        
        flash(f'Appointment status updated to {status}!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        flash('Update failed. Please try again.', 'error')
        print(f"Error: {e}")
    
    return redirect(url_for('my_appointments'))

# Cancel Appointment
@app.route('/cancel-appointment/<int:appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute('''
            DELETE FROM appointments 
            WHERE appointment_id = %s AND user_id = %s
        ''', (appointment_id, session['user_id']))
        mysql.connection.commit()
        cursor.close()
        
        flash('Appointment cancelled successfully!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        flash('Cancellation failed. Please try again.', 'error')
        print(f"Error: {e}")
    
    return redirect(url_for('my_appointments'))

# ============================================
# ADMIN ROUTES
# ============================================

# Admin Panel
@app.route('/admin')
@admin_required
def admin_panel():
    cursor = mysql.connection.cursor()
    
    # Get all users
    cursor.execute('''
        SELECT user_id, full_name, email, phone, age, gender, 
               is_admin, created_at
        FROM users
        ORDER BY created_at DESC
    ''')
    all_users = cursor.fetchall()
    
    # Get system stats
    cursor.execute('''
        SELECT 
            (SELECT COUNT(*) FROM users) as total_users,
            (SELECT COUNT(*) FROM users WHERE is_admin = 1) as total_admins,
            (SELECT COUNT(*) FROM assessments) as total_assessments,
            (SELECT COUNT(*) FROM appointments) as total_appointments,
            (SELECT COUNT(*) FROM doctors) as total_doctors
    ''')
    stats = cursor.fetchone()
    
    cursor.close()
    
    return render_template('admin_panel.html', users=all_users, stats=stats)

# Make User Admin
@app.route('/admin/make-admin/<int:user_id>')
@admin_required
def make_admin(user_id):
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute('UPDATE users SET is_admin = 1 WHERE user_id = %s', (user_id,))
        mysql.connection.commit()
        cursor.close()
        flash('User granted admin privileges!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        flash('Failed to grant admin privileges', 'error')
        print(f"Error: {e}")
    
    return redirect(url_for('admin_panel'))

# Remove Admin
@app.route('/admin/remove-admin/<int:user_id>')
@admin_required
def remove_admin(user_id):
    if user_id == session['user_id']:
        flash('You cannot remove your own admin privileges', 'error')
        return redirect(url_for('admin_panel'))
    
    cursor = mysql.connection.cursor()
    
    try:
        cursor.execute('UPDATE users SET is_admin = 0 WHERE user_id = %s', (user_id,))
        mysql.connection.commit()
        cursor.close()
        flash('Admin privileges removed!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        flash('Failed to remove admin privileges', 'error')
        print(f"Error: {e}")
    
    return redirect(url_for('admin_panel'))

# ============================================
# REPORTS & ANALYTICS (ADMIN ONLY)
# ============================================

@app.route('/reports')
@admin_required
def reports():
    cursor = mysql.connection.cursor()
    
    # Aggregate 1: Total counts
    cursor.execute('''
        SELECT 
            (SELECT COUNT(*) FROM users) as total_users,
            (SELECT COUNT(*) FROM assessments) as total_assessments,
            (SELECT COUNT(*) FROM appointments) as total_appointments,
            (SELECT COUNT(*) FROM doctors) as total_doctors
    ''')
    totals = cursor.fetchone()
    
    # Aggregate 2: Disease frequency (GROUP BY + COUNT)
    cursor.execute('''
        SELECT predicted_disease, COUNT(*) as count
        FROM assessments
        GROUP BY predicted_disease
        ORDER BY count DESC
        LIMIT 10
    ''')
    disease_stats = cursor.fetchall()
    
    # Aggregate 3: Average match percentage by disease (AVG + GROUP BY)
    cursor.execute('''
        SELECT predicted_disease, 
               AVG(match_percentage) as avg_match,
               COUNT(*) as total_cases
        FROM assessments
        GROUP BY predicted_disease
        ORDER BY total_cases DESC
        LIMIT 10
    ''')
    avg_match_stats = cursor.fetchall()
    
    # Aggregate 4: Appointments by status (GROUP BY + COUNT)
    cursor.execute('''
        SELECT status, COUNT(*) as count
        FROM appointments
        GROUP BY status
    ''')
    appointment_status_stats = cursor.fetchall()
    
    # Aggregate 5: Top rated doctors (ORDER BY + LIMIT)
    cursor.execute('''
        SELECT d.full_name, s.specialization_name, d.city, d.rating, d.total_reviews
        FROM doctors d
        JOIN specializations s ON d.specialization_id = s.specialization_id
        ORDER BY d.rating DESC, d.total_reviews DESC
        LIMIT 10
    ''')
    top_doctors = cursor.fetchall()
    
    # Use Views: High risk patients
    cursor.execute('SELECT * FROM high_risk_patients LIMIT 10')
    high_risk = cursor.fetchall()
    
    # Use Views: Doctor workload
    cursor.execute('SELECT * FROM doctor_workload LIMIT 10')
    doctor_workload = cursor.fetchall()
    
    # Use Views: Disease statistics
    cursor.execute('SELECT * FROM disease_statistics')
    disease_statistics = cursor.fetchall()
    
    cursor.close()
    
    return render_template('reports.html',
                         totals=totals,
                         disease_stats=disease_stats,
                         avg_match_stats=avg_match_stats,
                         appointment_status_stats=appointment_status_stats,
                         top_doctors=top_doctors,
                         high_risk=high_risk,
                         doctor_workload=doctor_workload,
                         disease_statistics=disease_statistics)

# ============================================
# AI CHATBOT ROUTES (RULE-BASED - NO API)
# ============================================

@app.route('/chatbot')
def chatbot():
    if 'user_id' not in session:
        flash('Please login to access chatbot', 'error')
        return redirect(url_for('login'))
    
    return render_template('chatbot.html')

@app.route('/chatbot/send', methods=['POST'])
def chatbot_send():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip().lower()
        
        if not user_message:
            return jsonify({'error': 'Empty message'}), 400
        
        # Comprehensive medical knowledge base
        medical_responses = {
            # Neurological Conditions
            'stroke': '''**Understanding Stroke**

A stroke occurs when blood supply to part of the brain is interrupted or reduced, preventing brain tissue from getting oxygen and nutrients. Brain cells begin to die within minutes.

**Types of Stroke:**
• **Ischemic Stroke (87%)** - Caused by blocked artery
• **Hemorrhagic Stroke (13%)** - Caused by bleeding in the brain

**Warning Signs - Remember F.A.S.T:**
• **F**ace drooping - One side of face droops or is numb
• **A**rm weakness - One arm is weak or numb
• **S**peech difficulty - Speech is slurred or hard to understand
• **T**ime to call 911 - Every second counts!

**Risk Factors:**
• High blood pressure, diabetes, high cholesterol
• Smoking, obesity, physical inactivity
• Heart disease, family history
• Age (risk increases after 55)

**⚠️ EMERGENCY:** Stroke is a medical emergency! Call 911 immediately if you notice any symptoms. Treatment is most effective within 3-4.5 hours.

**Prevention:** Control blood pressure, don't smoke, exercise regularly, maintain healthy weight, limit alcohol, manage diabetes.''',

            'brain hemorrhage': '''**Brain Hemorrhage (Cerebral Hemorrhage)**

A brain hemorrhage is bleeding in or around the brain, a life-threatening type of stroke.

**Symptoms:**
• Sudden, severe headache (worst headache ever)
• Sudden weakness, numbness (face, arm, leg)
• Vision problems or loss
• Difficulty speaking or understanding
• Loss of balance, dizziness
• Seizures
• Nausea and vomiting
• Loss of consciousness

**Common Causes:**
• High blood pressure (hypertension) - #1 cause
• Head trauma or injury
• Aneurysm (weakened blood vessel)
• Blood vessel malformations
• Blood or bleeding disorders
• Liver disease
��� Brain tumors

**⚠️ MEDICAL EMERGENCY!** Call 911 immediately! Quick treatment can save lives and reduce brain damage.

**Risk Reduction:**
• Control blood pressure
• Avoid blood thinners unless prescribed
• Wear seatbelts and helmets
• Manage underlying conditions
• Don't smoke''',

            'paralysis': '''**Understanding Paralysis**

Paralysis is the loss of muscle function in part of your body, ranging from temporary to permanent.

**Types:**
• **Monoplegia** - One limb affected
• **Hemiplegia** - One side of body
• **Paraplegia** - Both legs and lower body
• **Quadriplegia** - All four limbs and torso

**Common Causes:**
• Stroke (most common)
• Spinal cord injury
• Multiple sclerosis
• Cerebral palsy
• Brain injury or tumor
• Guillain-Barré syndrome
• Polio

**Treatment Options:**
• Physical therapy and rehabilitation
• Occupational therapy
• Speech therapy (if needed)
• Medications to manage symptoms
• Assistive devices (wheelchairs, braces)
• Surgery (in some cases)

**Important:** Early intervention significantly improves outcomes. Work with neurologists, physiatrists, and rehabilitation specialists.

**Hope:** Many people with paralysis lead full, active lives with proper treatment and support.''',

            'headache': '''**Common Headaches**

Most headaches are not serious, but some require medical attention.

**Types:**
1. **Tension Headaches** (Most common)
   • Dull, aching pain across forehead
   • Tightness around head
   • Muscle tension in neck/shoulders

2. **Migraines**
   • Throbbing pain (often one-sided)
   • Nausea, vomiting
   • Sensitivity to light and sound
   • Can last 4-72 hours

3. **Cluster Headaches**
   • Severe pain around one eye
   • Watering eye, runny nose
   • Occur in clusters over weeks

**🚨 Seek Immediate Care If:**
• Sudden, severe "thunderclap" headache
• Headache with fever, stiff neck, confusion
• After head injury
• With vision changes, weakness, seizures
• Worst headache of your life
• Progressively worsening over days/weeks

**Home Treatment:**
• Rest in quiet, dark room
• Stay hydrated (drink water)
• Over-the-counter pain relievers (ibuprofen, acetaminophen)
• Cold or warm compress
• Gentle massage
• Relaxation techniques

**Prevention:**
• Regular sleep schedule
• Stay hydrated
• Manage stress
• Regular exercise
• Identify and avoid triggers
• Limit caffeine and alcohol''',

            'fever': '''**Understanding Fever**

Fever is your body's natural response to fighting infection.

**Temperature Guide:**
• Normal: 98.6°F (37°C)
• Low-grade: 99-100.4°F (37.2-38°C)
• Fever: Above 100.4°F (38°C)
• High fever: Above 103°F (39.4°C)

**Common Causes:**
• Viral infections (flu, COVID-19, colds)
• Bacterial infections
• Urinary tract infections
• Respiratory infections
• Heat exhaustion
• Inflammatory conditions
• Vaccinations (normal reaction)
• Some medications

**🚨 See a Doctor If:**
• Fever above 103°F (39.4°C)
• Lasts more than 3 days
• Severe headache or stiff neck
• Difficulty breathing
• Chest pain
• Severe abdominal pain
• Persistent vomiting
• Rash that doesn't fade
• Confusion or extreme drowsiness
• Infants under 3 months with ANY fever

**Home Care:**
• Rest and stay in bed
• Drink plenty of fluids (water, broth, juice)
• Take acetaminophen (Tylenol) or ibuprofen (Advil)
• Lukewarm bath (not cold!)
• Light clothing
• Monitor temperature every 2-4 hours

**Don't:** Use aspirin in children, use alcohol rubs, or bundle up in heavy blankets.''',

            'nausea': '''**Nausea and Upset Stomach**

Nausea is an uncomfortable feeling in the stomach, often before vomiting.

**Common Causes:**
• Food poisoning
• Stomach flu (gastroenteritis)
• Motion sickness
• Pregnancy (morning sickness)
• Migraines
• Medications
• Anxiety or stress
• Overeating
• Inner ear problems
• GERD (acid reflux)

**Home Remedies:**
• Sip clear fluids slowly (water, ginger ale, clear broth)
• Eat bland foods (crackers, toast, rice, bananas)
• Ginger (tea, candies, fresh ginger)
• Peppermint tea or candies
• Rest with head elevated (30-45 degrees)
• Fresh air and deep breathing
• Avoid strong odors, spicy/fatty foods
• Cold compress on forehead

**🚨 Seek Medical Care If:**
• Severe abdominal pain
• Blood in vomit (red or coffee-ground appearance)
• Signs of dehydration (dry mouth, little/no urination, dizziness)
• Nausea lasting more than 48 hours
• Severe headache with stiff neck
• Chest pain
• Confusion or high fever

**Prevention:**
• Eat slowly and smaller meals
• Avoid trigger foods
• Stay hydrated
• Manage stress
• Avoid lying down after eating''',

            'vomiting': '''**Vomiting**

Vomiting is your body's way of getting rid of harmful substances.

**Common Causes:**
• Viral gastroenteritis (stomach flu)
• Food poisoning
• Motion sickness
• Pregnancy
• Medications
• Migraines
• Appendicitis
• Concussion

**What to Do:**
1. **First Hour:** Rest stomach, no food/drink
2. **After 1 hour:** Small sips of clear fluids
3. **After 4-8 hours:** Try bland foods if no vomiting
4. **Gradually** return to normal diet

**Rehydration (Important!):**
• Sip water, clear broth, or oral rehydration solution
• Avoid sugary drinks or dairy initially
• Take small, frequent sips

**🚨 Emergency - Call 911 If:**
• Blood in vomit (bright red or coffee-ground)
• Severe abdominal pain
• Severe headache with stiff neck
• Signs of severe dehydration (no urination 8+ hours, extreme thirst, sunken eyes)
• Confusion or extreme weakness
• Can't keep down ANY fluids for 24+ hours
• Vomiting after head injury

**See Doctor If:**
• Vomiting lasts more than 24 hours (adults) or 12 hours (children)
• Unable to keep fluids down
• Dehydration symptoms
• High fever (>101°F)''',

            'fatigue': '''**Chronic Fatigue & Tiredness**

Fatigue is persistent tiredness that doesn't improve with rest.

**Common Causes:**
• Lack of sleep or poor sleep quality
• Stress, anxiety, depression
• Poor diet or dehydration
• Anemia (low iron)
• Thyroid problems
• Diabetes
• Sleep apnea
• Chronic fatigue syndrome
• Medications
• Vitamin deficiencies (B12, D)

**When to Worry:**
• Sudden, severe fatigue
• Doesn't improve with rest
• Lasts more than 2 weeks
• Interferes with daily activities
• Accompanied by: fever, weight loss, pain, depression

**Boosting Energy Naturally:**
• **Sleep:** 7-9 hours per night, consistent schedule
• **Exercise:** Even 10-minute walks help (seems counterintuitive but works!)
• **Nutrition:** Balanced diet, avoid sugar crashes
• **Hydration:** Drink 8 glasses of water daily
• **Stress Management:** Meditation, yoga, deep breathing
• **Limit:** Caffeine after 2pm, alcohol
• **Sunlight:** Get outside daily for vitamin D
• **Social Connection:** Spend time with loved ones

**Medical Tests to Consider:**
• Complete blood count (anemia check)
• Thyroid function test
• Vitamin B12 and D levels
• Blood sugar (diabetes screening)
• Sleep study (if suspected sleep apnea)

**See a Doctor:** If fatigue persists despite lifestyle changes or you have concerning symptoms.''',

            'cough': '''**Cough Types and Treatment**

A cough is a reflex to clear airways of mucus and irritants.

**Types:**
• **Acute** - Lasts less than 3 weeks (usually viral)
• **Subacute** - Lasts 3-8 weeks (often post-viral)
• **Chronic** - Lasts more than 8 weeks (needs evaluation)

**Common Causes:**
• Common cold or flu
• Allergies
• Asthma
• Acid reflux (GERD)
• Postnasal drip
• Smoking
• COVID-19
• Bronchitis
• Pneumonia

**🚨 See Doctor Immediately If:**
• Coughing up blood
• Difficulty breathing or chest pain
• Fever above 100.4°F (38°C)
• Wheezing or gasping
• Bluish lips or face
• Severe weakness or confusion

**See Doctor If:**
• Cough lasts more than 3 weeks
• Thick, green/yellow mucus
• Night sweats or unexplained weight loss
• Severe or worsening symptoms

**Home Care:**
• Stay hydrated (thins mucus)
• Use humidifier (adds moisture to air)
• Honey (1 tsp for adults - NOT for infants under 1 year)
• Elevate head while sleeping
• Avoid irritants (smoke, dust, strong odors)
• Throat lozenges or hard candies
• Gargle with salt water
• Steam inhalation

**Prevention:**
• Wash hands frequently
• Avoid sick people
• Don't smoke
• Get vaccinations (flu, COVID, pneumonia)''',

            'joint pain': '''**Joint Pain & Arthritis**

Joint pain can affect one or multiple joints.

**Common Causes:**
• Osteoarthritis (wear and tear)
• Rheumatoid arthritis (autoimmune)
• Injury or overuse
• Gout (uric acid crystals)
• Bursitis or tendinitis
• Infections
• Lupus

**Symptoms:**
• Pain, stiffness, swelling
• Reduced range of motion
• Redness and warmth
• Weakness

**Home Treatment:**
• **R.I.C.E. Method:**
  - Rest the joint
  - Ice (15-20 min several times daily)
  - Compression (wrap with elastic bandage)
  - Elevation (raise above heart level)
• Over-the-counter pain relievers (ibuprofen, acetaminophen)
• Gentle stretching and exercise
• Warm baths or heating pad
• Maintain healthy weight

**🚨 Seek Immediate Care If:**
• Sudden, intense pain
• Joint appears deformed
• Rapid swelling
• Fever with joint pain
• Can't use the joint at all

**Long-term Management:**
• Regular low-impact exercise (swimming, walking)
• Physical therapy
• Weight management
• Anti-inflammatory diet
• Supportive footwear
• Assistive devices if needed

**See a Doctor:** For persistent pain, diagnosis of arthritis type, and treatment plan.''',

            'rash': '''**Skin Rashes**

Rashes have many causes and appearances.

**Common Types:**
• Contact dermatitis (allergic reaction)
• Eczema (atopic dermatitis)
• Heat rash
• Hives (urticaria)
• Psoriasis
• Fungal infections (ringworm, athlete's foot)
• Viral infections (chickenpox, shingles)

**Home Care:**
• Keep area clean and dry
• Avoid scratching
• Cool compresses
• Over-the-counter hydrocortisone cream
• Antihistamines for itching
• Moisturizer for dry skin
• Avoid known irritants

**🚨 Emergency - Call 911 If:**
• Difficulty breathing or swallowing
• Facial swelling
• Rash with severe allergic reaction
• Purple or blood-colored rash with fever

**See Doctor If:**
• Rash covers large body area
• Rapidly spreading
• Severe pain or blisters
• Signs of infection (pus, warmth, red streaks)
• Fever with rash
• Rash lasts more than a few days
• Severe itching affecting sleep/daily life

**Prevention:**
• Identify and avoid triggers
• Use fragrance-free, hypoallergenic products
• Wear breathable fabrics
• Moisturize regularly
• Sun protection''',

            'weight loss': '''**Unintentional Weight Loss**

Losing weight without trying can signal health issues.

**Concerning If:**
• Lost 5% or more of body weight in 6 months
• No change in diet or exercise
• Accompanied by other symptoms

**Possible Causes:**
• Hyperthyroidism (overactive thyroid)
• Diabetes
• Depression or anxiety
• Cancer
• Digestive disorders (Crohn's, celiac, ulcers)
• Infections (tuberculosis, HIV)
• Medications
• Dental problems
• Dementia (in elderly)

**When to See Doctor:**
• Unintended weight loss of 10+ pounds
• Loss of appetite
• Fatigue or weakness
• Other symptoms (fever, pain, changes in bowel habits)
• Concerned about weight loss

**What Doctor May Check:**
• Complete physical exam
• Blood tests (thyroid, diabetes, infections)
• Stool tests
• Imaging (X-rays, CT scan)
• Endoscopy (if digestive issues)

**Healthy Weight Gain:**
• Eat nutrient-dense foods
• Frequent small meals
• Protein-rich foods
• Healthy fats (nuts, avocado, olive oil)
• Smoothies and shakes
• Strength training exercise

**Important:** Don't ignore unexplained weight loss. Early detection of serious conditions improves outcomes.''',

            'jaundice': '''**Jaundice (Yellow Skin/Eyes)**

Jaundice is yellowing of skin and eyes due to excess bilirubin.

**Causes:**
• Liver diseases (hepatitis, cirrhosis, liver cancer)
• Gallstones or bile duct blockage
• Pancreatic cancer
• Blood disorders (hemolytic anemia)
• Certain medications
• Gilbert's syndrome (benign)
• In newborns: immature liver (usually harmless)

**Symptoms:**
• Yellow tint to skin and whites of eyes
�� Dark urine
• Pale or clay-colored stools
• Itching
• Fatigue
• Abdominal pain

**🚨 Seek Immediate Care:**
Jaundice in adults always requires medical evaluation to determine the cause.

**What Doctor Will Do:**
• Physical examination
• Blood tests (liver function, bilirubin levels)
• Urine and stool tests
• Ultrasound or CT scan
• Sometimes liver biopsy

**Treatment:**
Depends on underlying cause:
• Hepatitis: Antivirals or supportive care
• Gallstones: Surgery to remove gallbladder
• Medications: Stop or change medications
• Cancer: Chemotherapy, radiation, surgery

**Prevention:**
• Limit alcohol
• Maintain healthy weight
• Get hepatitis vaccines
• Avoid sharing needles
• Safe sex practices
• Careful with medications and supplements''',

            # General Health Topics
            'emergency': '''**🚨 MEDICAL EMERGENCIES - CALL 911 IMMEDIATELY**

**Heart/Breathing:**
• Chest pain or pressure lasting more than a few minutes
• Severe difficulty breathing
• Coughing or vomiting blood
• Choking

**Neurological:**
• Stroke symptoms (F.A.S.T.)
• Sudden severe headache (thunderclap)
• Seizures
• Loss of consciousness
• Severe confusion

**Injuries:**
• Severe bleeding that won't stop
• Severe burns
• Suspected broken bones with deformity
• Head or spinal injury
• Deep wounds

**Other:**
• Severe allergic reaction (difficulty breathing, facial swelling)
• Sudden vision loss
• Severe, persistent vomiting
• Poisoning or overdose
• Suicidal thoughts or actions
• High fever with stiff neck

**Don't Drive Yourself!**
Call 911 or have someone drive you. Ambulances can start treatment immediately and alert hospitals.

**Not Sure If It's an Emergency?**
Call 911 anyway. Paramedics can assess and advise. Better safe than sorry!''',

            'when doctor': '''**When to See a Doctor**

**See Doctor Soon (Within 1-3 Days):**
• Persistent symptoms lasting more than a week
• Moderate pain or discomfort
• Low-grade fever (99-100.4°F) lasting 2+ days
• Mild breathing difficulties
• Persistent cough with colored mucus
• Rash that's spreading
• Digestive issues lasting several days

**See Doctor Today or Tomorrow:**
• High fever (above 102°F)
• Severe sore throat
• Ear pain
• Painful urination
• Vomiting or diarrhea with dehydration signs
• Injury with swelling/bruising
• Worsening symptoms

**When in Doubt:**
Call your doctor's office. They can help determine urgency and may offer telehealth options.

**Preventive Care:**
• Annual physical exam
• Age-appropriate screenings
• Vaccinations
• Dental checkups (twice yearly)
• Eye exams

**Build Relationship with Primary Care Doctor:**
Having a regular doctor who knows your health history is invaluable for ongoing care and quick consultations.''',

            'prevent': '''**Disease Prevention & Healthy Living**

**Top Prevention Strategies:**

**1. Nutrition:**
• Eat colorful fruits and vegetables
• Whole grains over refined
• Lean proteins (fish, chicken, beans)
• Healthy fats (nuts, olive oil, avocado)
• Limit sugar, salt, and processed foods
• Stay hydrated (8 glasses water/day)

**2. Exercise:**
• 150 minutes moderate activity per week
• Mix cardio and strength training
• Even small amounts help (walk 10 min)
• Find activities you enjoy

**3. Sleep:**
• 7-9 hours nightly
• Consistent sleep schedule
• Dark, cool, quiet room
• Limit screens before bed

**4. Don't Smoke:**
• Smoking causes heart disease, cancer, lung disease
• Quitting has immediate and long-term benefits
• Resources available to help you quit

**5. Limit Alcohol:**
• Moderate: up to 1 drink/day (women), 2/day (men)
• Or avoid completely

**6. Manage Stress:**
• Meditation, deep breathing
• Regular exercise
• Hobbies and social connections
• Professional help if needed

**7. Preventive Care:**
• Regular checkups
• Recommended screenings (blood pressure, cholesterol, cancer screenings)
• Vaccinations (flu, COVID, pneumonia, etc.)
• Dental and vision care

**8. Safety:**
• Wear seatbelts and helmets
• Sun protection (sunscreen, hats)
• Hand washing
• Safe sex practices

**9. Mental Health:**
• Social connections
• Purpose and meaning
• Seek help for depression/anxiety
• Work-life balance

**10. Know Your Numbers:**
• Blood pressure
• Cholesterol
• Blood sugar
• BMI
• Family health history

**Prevention is the best medicine!**''',

            'symptom checker': '''I see you're interested in checking your symptoms!

Good news - we have a comprehensive **Symptom Checker Tool** built right into this platform!

**How to Use It:**
1. Go back to your **Dashboard**
2. Click on **"Start Assessment"**
3. Select your symptoms from the list
4. Get instant disease predictions with match percentages
5. Find specialized doctors in your area based on results

**Our Symptom Checker Can Help With:**
• Identifying potential conditions
• Getting match percentages
• Finding relevant specialists
• Booking doctor appointments
• Tracking your health history

**Why Use Our Tool:**
✓ Based on medical symptom patterns
✓ Instant results
✓ Doctor recommendations
✓ Completely free
✓ Private and secure

Would you like me to explain any specific symptoms first, or would you prefer to go try the Symptom Checker now?''',

        }
        
        # Find best matching response
        bot_response = None
        matched_keyword = None
        
        # Check for exact or partial keyword matches
        for keyword, response in medical_responses.items():
            if keyword in user_message:
                bot_response = response
                matched_keyword = keyword
                break
        
        # If no match found, provide helpful default response
        if not bot_response:
            # Check for general health queries
            if any(word in user_message for word in ['help', 'what can you', 'how do you', 'what do you']):
                bot_response = '''**Hello! I'm Your Medical Information Assistant** 👋

I can provide general information about:

**🧠 Neurological Conditions:**
• Stroke, Brain Hemorrhage, Paralysis

**🤒 Common Symptoms:**
• Fever, Headaches, Nausea, Vomiting, Fatigue, Cough

**💊 Health Topics:**
• Joint Pain, Rashes, Weight Loss, Jaundice

**🚨 Emergency Information:**
• When to call 911
• When to see a doctor

**🔍 Prevention & Wellness:**
• Disease prevention tips
• Healthy living strategies

**Plus:**
• I can explain when symptoms are serious
• Guide you to appropriate care
• Explain medical terms simply

**You can also use our Symptom Checker tool** from the dashboard to identify potential conditions and find doctors!

What would you like to know about? Just ask me about any symptom or condition!'''
            
            elif any(word in user_message for word in ['thank', 'thanks']):
                bot_response = "You're very welcome! 😊 Remember, I'm here to provide general information. For personalized medical advice, please consult with a healthcare professional. Feel free to ask if you have more questions!"
            
            elif any(word in user_message for word in ['hello', 'hi', 'hey']):
                bot_response = "Hello! 👋 I'm your Medical Information Assistant. I can help you understand diseases, symptoms, and health conditions. What would you like to know about today?"
            
            else:
                bot_response = '''I'd be happy to help with that health question!

While I didn't find a specific match, here's what I can assist with:

**Try asking about:**
• Specific symptoms (headache, fever, cough, nausea, etc.)
• Conditions (stroke, paralysis, brain hemorrhage)
• General health topics (prevention, emergencies, when to see a doctor)

**Or better yet**, use our **Symptom Checker tool** from your dashboard! It can:
• Analyze your specific symptoms
• Predict potential conditions
• Recommend appropriate doctors
• Help you book appointments

**Important:** I provide general health information, not medical diagnosis. For personalized medical advice, please consult a healthcare professional.

What specific health topic would you like to know more about?'''
        
        # Save to chat history
        if 'chat_history' not in session:
            session['chat_history'] = []
        
        session['chat_history'].append({
            'user': user_message,
            'bot': bot_response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 20 messages
        if len(session['chat_history']) > 20:
            session['chat_history'] = session['chat_history'][-20:]
        
        session.modified = True
        
        return jsonify({
            'success': True,
            'response': bot_response
        })
        
    except Exception as e:
        print(f"Chatbot error: {e}")
        return jsonify({
            'success': False,
            'error': 'Sorry, I encountered an error. Please try again.'
        }), 500

@app.route('/chatbot/clear', methods=['POST'])
def chatbot_clear():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    session['chat_history'] = []
    session.modified = True
    
    return jsonify({'success': True})

@app.route('/chatbot/history')
def chatbot_history():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    history = session.get('chat_history', [])
    return jsonify({'history': history})



@app.route('/success')
def success():
    """Success page with animation"""
    message = session.pop('success_message', 'Operation completed successfully!')
    redirect_url = session.pop('success_redirect', url_for('dashboard'))
    return render_template('success.html', message=message, redirect_url=redirect_url)

# ============================================
# RUN APP
# ============================================

if __name__ == '__main__':
    app.run(debug=True)