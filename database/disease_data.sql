-- Use existing database
USE project;

-- Create disease_symptoms table (matches your CSV structure)
CREATE TABLE disease_symptoms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fever TINYINT(1) DEFAULT 0,
    headache TINYINT(1) DEFAULT 0,
    nausea TINYINT(1) DEFAULT 0,
    vomiting TINYINT(1) DEFAULT 0,
    fatigue TINYINT(1) DEFAULT 0,
    joint_pain TINYINT(1) DEFAULT 0,
    skin_rash TINYINT(1) DEFAULT 0,
    cough TINYINT(1) DEFAULT 0,
    weight_loss TINYINT(1) DEFAULT 0,
    yellow_eyes TINYINT(1) DEFAULT 0,
    disease VARCHAR(100) NOT NULL,
    INDEX idx_disease (disease)
) ENGINE=InnoDB;

-- Create assessments table to store user symptom checks
CREATE TABLE assessments (
    assessment_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    assessment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    selected_symptoms JSON,
    predicted_disease VARCHAR(100),
    match_percentage DECIMAL(5,2),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB;