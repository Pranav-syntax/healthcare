USE project;

-- Trigger 1: Auto-update doctor availability when appointment is booked
DELIMITER //

CREATE TRIGGER after_appointment_insert
AFTER INSERT ON appointments
FOR EACH ROW
BEGIN
    -- Count pending/confirmed appointments for the doctor
    DECLARE appointment_count INT;
    
    SELECT COUNT(*) INTO appointment_count
    FROM appointments
    WHERE doctor_id = NEW.doctor_id
    AND status IN ('Pending', 'Confirmed');
    
    -- Update doctor availability based on workload
    IF appointment_count >= 10 THEN
        UPDATE doctors SET availability = 'Busy' WHERE doctor_id = NEW.doctor_id;
    ELSE
        UPDATE doctors SET availability = 'Available' WHERE doctor_id = NEW.doctor_id;
    END IF;
END//

DELIMITER ;

-- Trigger 2: Update doctor availability when appointment status changes
DELIMITER //

CREATE TRIGGER after_appointment_update
AFTER UPDATE ON appointments
FOR EACH ROW
BEGIN
    DECLARE appointment_count INT;
    
    SELECT COUNT(*) INTO appointment_count
    FROM appointments
    WHERE doctor_id = NEW.doctor_id
    AND status IN ('Pending', 'Confirmed');
    
    IF appointment_count >= 10 THEN
        UPDATE doctors SET availability = 'Busy' WHERE doctor_id = NEW.doctor_id;
    ELSE
        UPDATE doctors SET availability = 'Available' WHERE doctor_id = NEW.doctor_id;
    END IF;
END//

DELIMITER ;

-- Trigger 3: Log deleted appointments (create audit table first)
CREATE TABLE IF NOT EXISTS appointment_audit_log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    appointment_id INT,
    user_id INT,
    doctor_id INT,
    appointment_date DATE,
    disease_name VARCHAR(100),
    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_reason VARCHAR(255)
) ENGINE=InnoDB;

DELIMITER //

CREATE TRIGGER before_appointment_delete
BEFORE DELETE ON appointments
FOR EACH ROW
BEGIN
    INSERT INTO appointment_audit_log 
    (appointment_id, user_id, doctor_id, appointment_date, disease_name, deleted_reason)
    VALUES 
    (OLD.appointment_id, OLD.user_id, OLD.doctor_id, OLD.appointment_date, OLD.disease_name, 'User cancelled');
END//

DELIMITER ;

-- Trigger 4: Log deleted assessments
CREATE TABLE IF NOT EXISTS assessment_audit_log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    assessment_id INT,
    user_id INT,
    predicted_disease VARCHAR(100),
    match_percentage DECIMAL(5,2),
    deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

DELIMITER //

CREATE TRIGGER before_assessment_delete
BEFORE DELETE ON assessments
FOR EACH ROW
BEGIN
    INSERT INTO assessment_audit_log 
    (assessment_id, user_id, predicted_disease, match_percentage)
    VALUES 
    (OLD.assessment_id, OLD.user_id, OLD.predicted_disease, OLD.match_percentage);
END//

DELIMITER ;

-- Trigger 5: Prevent booking appointments in the past
DELIMITER //

CREATE TRIGGER before_appointment_insert_validate
BEFORE INSERT ON appointments
FOR EACH ROW
BEGIN
    IF NEW.appointment_date < CURDATE() THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Cannot book appointments in the past';
    END IF;
END//

DELIMITER ;