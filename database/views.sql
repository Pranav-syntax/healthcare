USE project;

-- View 1: High Risk Patients (Match > 70%)
CREATE OR REPLACE VIEW high_risk_patients AS
SELECT 
    u.user_id,
    u.full_name,
    u.email,
    u.age,
    u.gender,
    a.assessment_id,
    a.predicted_disease,
    a.match_percentage,
    a.assessment_date
FROM users u
JOIN assessments a ON u.user_id = a.user_id
WHERE a.match_percentage > 70
ORDER BY a.match_percentage DESC, a.assessment_date DESC;

-- View 2: Doctor Workload Statistics
CREATE OR REPLACE VIEW doctor_workload AS
SELECT 
    d.doctor_id,
    d.full_name,
    s.specialization_name,
    d.city,
    d.state,
    d.rating,
    COUNT(DISTINCT ap.appointment_id) as total_appointments,
    COUNT(DISTINCT CASE WHEN ap.status = 'Pending' THEN ap.appointment_id END) as pending_appointments,
    COUNT(DISTINCT CASE WHEN ap.status = 'Confirmed' THEN ap.appointment_id END) as confirmed_appointments,
    COUNT(DISTINCT CASE WHEN ap.status = 'Completed' THEN ap.appointment_id END) as completed_appointments
FROM doctors d
JOIN specializations s ON d.specialization_id = s.specialization_id
LEFT JOIN appointments ap ON d.doctor_id = ap.doctor_id
GROUP BY d.doctor_id, d.full_name, s.specialization_name, d.city, d.state, d.rating
ORDER BY total_appointments DESC;

-- View 3: Disease Statistics
CREATE OR REPLACE VIEW disease_statistics AS
SELECT 
    a.predicted_disease,
    COUNT(DISTINCT a.assessment_id) as total_assessments,
    COUNT(DISTINCT a.user_id) as unique_patients,
    AVG(a.match_percentage) as avg_match_percentage,
    COUNT(DISTINCT ap.appointment_id) as appointments_booked,
    MIN(a.assessment_date) as first_reported,
    MAX(a.assessment_date) as last_reported
FROM assessments a
LEFT JOIN appointments ap ON a.assessment_id = ap.assessment_id
GROUP BY a.predicted_disease
ORDER BY total_assessments DESC;

-- View 4: User Health Summary
CREATE OR REPLACE VIEW user_health_summary AS
SELECT 
    u.user_id,
    u.full_name,
    u.email,
    u.age,
    COUNT(DISTINCT asm.assessment_id) as total_assessments,
    COUNT(DISTINCT ap.appointment_id) as total_appointments,
    MAX(asm.assessment_date) as last_assessment_date,
    MAX(ap.appointment_date) as next_appointment_date
FROM users u
LEFT JOIN assessments asm ON u.user_id = asm.user_id
LEFT JOIN appointments ap ON u.user_id = ap.user_id AND ap.status IN ('Pending', 'Confirmed')
GROUP BY u.user_id, u.full_name, u.email, u.age;

-- View 5: Appointment Overview
CREATE OR REPLACE VIEW appointment_overview AS
SELECT 
    ap.appointment_id,
    u.full_name as patient_name,
    u.email as patient_email,
    d.full_name as doctor_name,
    s.specialization_name,
    d.hospital_name,
    d.city,
    ap.appointment_date,
    ap.appointment_time,
    ap.status,
    ap.disease_name,
    ap.created_at as booking_date
FROM appointments ap
JOIN users u ON ap.user_id = u.user_id
JOIN doctors d ON ap.doctor_id = d.doctor_id
JOIN specializations s ON d.specialization_id = s.specialization_id
ORDER BY ap.appointment_date DESC, ap.appointment_time DESC;