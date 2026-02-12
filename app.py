from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import json
from datetime import datetime, timedelta


app = Flask(__name__)
app.secret_key = 'change-this-secret-key-in-production'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'  # Enter your MySQL password
app.config['MYSQL_DB'] = 'project'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

# Available symptoms (from your dataset)
SYMPTOMS = [
    'fever', 'headache', 'nausea', 'vomiting', 'fatigue',
    'joint_pain', 'skin_rash', 'cough', 'weight_loss', 'yellow_eyes'
]

# Home route - redirect to login
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Login route
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
            flash(f'Welcome back, {user["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

# Signup route
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
            
            flash(f'Registration successful! Your User ID is: {new_user_id}', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            mysql.connection.rollback()
            cursor.close()
            flash('Registration failed. Please try again.', 'error')
            print(f"Error: {e}")
            return render_template('signup.html')
    
    return render_template('signup.html')

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login to access dashboard', 'error')
        return redirect(url_for('login'))
    
    # Get user's assessment history
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

# Symptom Checker Page
@app.route('/symptom-checker')
def symptom_checker():
    if 'user_id' not in session:
        flash('Please login to access symptom checker', 'error')
        return redirect(url_for('login'))
    
    return render_template('symptom_checker.html', symptoms=SYMPTOMS)

# Predict Disease (API endpoint)
@app.route('/predict', methods=['POST'])
def predict():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Get selected symptoms from form
    selected_symptoms = request.form.getlist('symptoms')
    
    if not selected_symptoms:
        flash('Please select at least one symptom', 'error')
        return redirect(url_for('symptom_checker'))
    
    # Create binary vector for user's symptoms
    user_symptoms = {}
    for symptom in SYMPTOMS:
        user_symptoms[symptom] = 1 if symptom in selected_symptoms else 0
    
    # Build SQL query to find matching diseases
    cursor = mysql.connection.cursor()
    
    # Get all disease patterns
    cursor.execute("SELECT * FROM disease_symptoms")
    all_patterns = cursor.fetchall()
    
    # Calculate match scores
    matches = []
    for pattern in all_patterns:
        score = 0
        total_symptoms = sum(user_symptoms.values())
        
        # Count matching symptoms
        for symptom in SYMPTOMS:
            if user_symptoms[symptom] == 1 and pattern[symptom] == 1:
                score += 1
        
        # Calculate percentage match
        if total_symptoms > 0:
            match_percentage = (score / total_symptoms) * 100
        else:
            match_percentage = 0
        
        if score > 0:  # Only include if there's at least one match
            matches.append({
                'disease': pattern['disease'],
                'match_percentage': round(match_percentage, 2),
                'matched_symptoms': score,
                'total_selected': total_symptoms
            })
    
    # Sort by match percentage
    matches.sort(key=lambda x: x['match_percentage'], reverse=True)
    
    # Get top match
    if matches:
        top_match = matches[0]
        
        # Save assessment to database
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
                             matches=matches[:5],  # Top 5 matches
                             selected_symptoms=selected_symptoms,
                             assessment_id=assessment_id)
    else:
        cursor.close()
        flash('No matching diseases found. Please consult a doctor.', 'error')
        return redirect(url_for('symptom_checker'))

# View Assessment History
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
    
    # Parse JSON symptoms
    for assessment in assessments:
        assessment['selected_symptoms'] = json.loads(assessment['selected_symptoms'])
    
    return render_template('history.html', assessments=assessments)

# Find Doctors with Smart Fallback
@app.route('/find-doctors/<int:assessment_id>')
def find_doctors(assessment_id):
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    cursor = mysql.connection.cursor()
    
    # Get assessment details
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
    
    # Get location from query params
    city = request.args.get('city', '').strip()
    state = request.args.get('state', '').strip()
    
    doctors = []
    search_performed = False
    search_result_message = None
    nearby_doctors = []
    other_city_doctors = []
    
    if city:
        search_performed = True
        
        # STEP 1: Try to find doctors in the EXACT city
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
            # STEP 2: No doctors in city - Try same STATE
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
            
            # STEP 3: Try to find doctors treating this disease in OTHER cities
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
            
            # Set appropriate message
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
    
    # Get doctor details
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
    
    # Get assessment details
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
            # Insert appointment
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
            
            flash(f'Appointment booked successfully! Appointment ID: #{appointment_id}', 'success')
            return redirect(url_for('my_appointments'))
            
        except Exception as e:
            mysql.connection.rollback()
            cursor.close()
            flash('Booking failed. Please try again.', 'error')
            print(f"Error: {e}")
            return redirect(url_for('book_appointment', doctor_id=doctor_id, assessment_id=assessment_id))
    
    # GET request - show booking form
    min_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    cursor.close()
    
    return render_template('book_appointment.html',
                         doctor=doctor,
                         assessment_id=assessment_id,
                         disease_name=assessment['predicted_disease'],
                         symptoms=json.loads(assessment['selected_symptoms']),
                         min_date=min_date)

# My Appointments - COMPLETE FIX
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
    
    # Parse symptoms JSON and format time
    for appointment in appointments:
        appointment['symptoms'] = json.loads(appointment['symptoms'])
        
        # Convert timedelta to formatted time string
        time_obj = appointment['appointment_time']
        if time_obj:
            total_seconds = int(time_obj.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            
            # Convert to 12-hour format
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

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)