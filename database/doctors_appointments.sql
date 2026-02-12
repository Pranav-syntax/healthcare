USE project;

-- Specializations Table
CREATE TABLE specializations (
    specialization_id INT AUTO_INCREMENT PRIMARY KEY,
    specialization_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Doctors Table
CREATE TABLE doctors (
    doctor_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    specialization_id INT NOT NULL,
    qualification VARCHAR(200) NOT NULL,
    experience_years INT NOT NULL,
    hospital_name VARCHAR(200) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    address TEXT,
    phone VARCHAR(15) NOT NULL,
    email VARCHAR(100),
    consultation_fee DECIMAL(10, 2),
    rating DECIMAL(3, 2) CHECK (rating >= 0 AND rating <= 5),
    total_reviews INT DEFAULT 0,
    availability ENUM('Available', 'Busy', 'Unavailable') DEFAULT 'Available',
    profile_image VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (specialization_id) REFERENCES specializations(specialization_id),
    INDEX idx_city (city),
    INDEX idx_state (state),
    INDEX idx_rating (rating),
    INDEX idx_specialization (specialization_id)
) ENGINE=InnoDB;

-- Disease to Specialization Mapping
CREATE TABLE disease_specialization (
    id INT AUTO_INCREMENT PRIMARY KEY,
    disease_name VARCHAR(100) NOT NULL,
    specialization_id INT NOT NULL,
    FOREIGN KEY (specialization_id) REFERENCES specializations(specialization_id),
    UNIQUE KEY unique_disease_spec (disease_name, specialization_id)
) ENGINE=InnoDB;

-- Appointments Table
CREATE TABLE appointments (
    appointment_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    doctor_id INT NOT NULL,
    assessment_id INT,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status ENUM('Pending', 'Confirmed', 'Completed', 'Cancelled') DEFAULT 'Pending',
    disease_name VARCHAR(100),
    symptoms TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id) ON DELETE CASCADE,
    FOREIGN KEY (assessment_id) REFERENCES assessments(assessment_id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_doctor_id (doctor_id),
    INDEX idx_appointment_date (appointment_date),
    INDEX idx_status (status)
) ENGINE=InnoDB;

-- Doctor Reviews Table (optional for future)
CREATE TABLE doctor_reviews (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    doctor_id INT NOT NULL,
    user_id INT NOT NULL,
    appointment_id INT,
    rating INT CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id) ON DELETE SET NULL
) ENGINE=InnoDB;