import mysql.connector
from mysql.connector import Error
import random

def import_sample_doctors():
    """Import sample doctors data for Indian cities"""
    
    connection = None
    
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root',  # Change to your MySQL password
            database='project'
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            print("✅ Connected to MySQL database\n")
            
            # 1. Insert Specializations
            specializations = [
                ('Neurologist', 'Specializes in disorders of the nervous system including brain hemorrhage'),
                ('General Physician', 'Treats general health conditions and provides primary care'),
                ('Internal Medicine', 'Focuses on adult diseases and complex diagnostic problems'),
                ('Emergency Medicine', 'Handles acute and urgent medical conditions'),
                ('Cardiologist', 'Specializes in heart and cardiovascular conditions'),
                ('Pulmonologist', 'Treats respiratory system and lung diseases'),
                ('Gastroenterologist', 'Specializes in digestive system disorders'),
                ('Infectious Disease Specialist', 'Treats infectious diseases and fever-related conditions')
            ]
            
            print("📋 Inserting specializations...")
            for spec_name, desc in specializations:
                cursor.execute('''
                    INSERT IGNORE INTO specializations (specialization_name, description)
                    VALUES (%s, %s)
                ''', (spec_name, desc))
            connection.commit()
            print(f"✅ Inserted {len(specializations)} specializations\n")
            
            # 2. Map Disease to Specialization
            print("🔗 Mapping diseases to specializations...")
            cursor.execute('''
                INSERT IGNORE INTO disease_specialization (disease_name, specialization_id)
                SELECT 'Paralysis (brain hemorrhage)', specialization_id 
                FROM specializations WHERE specialization_name = 'Neurologist'
            ''')
            
            cursor.execute('''
                INSERT IGNORE INTO disease_specialization (disease_name, specialization_id)
                SELECT 'Paralysis (brain hemorrhage)', specialization_id 
                FROM specializations WHERE specialization_name = 'Emergency Medicine'
            ''')
            connection.commit()
            print("✅ Disease-Specialization mapping complete\n")
            
            # 3. Insert Sample Doctors
            indian_cities = [
                ('Mumbai', 'Maharashtra'),
                ('Delhi', 'Delhi'),
                ('Bangalore', 'Karnataka'),
                ('Hyderabad', 'Telangana'),
                ('Chennai', 'Tamil Nadu'),
                ('Kolkata', 'West Bengal'),
                ('Pune', 'Maharashtra'),
                ('Ahmedabad', 'Gujarat'),
                ('Jaipur', 'Rajasthan'),
                ('Lucknow', 'Uttar Pradesh'),
                ('Kochi', 'Kerala'),
                ('Chandigarh', 'Chandigarh'),
                ('Indore', 'Madhya Pradesh'),
                ('Coimbatore', 'Tamil Nadu'),
                ('Bhopal', 'Madhya Pradesh')
            ]
            
            doctor_names = [
                'Dr. Rajesh Kumar', 'Dr. Priya Sharma', 'Dr. Amit Patel', 
                'Dr. Sneha Reddy', 'Dr. Vikram Singh', 'Dr. Anjali Gupta',
                'Dr. Suresh Menon', 'Dr. Kavita Desai', 'Dr. Arun Verma',
                'Dr. Deepa Iyer', 'Dr. Ravi Nair', 'Dr. Pooja Joshi',
                'Dr. Manoj Chopra', 'Dr. Sunita Rao', 'Dr. Karthik Krishnan',
                'Dr. Meera Agarwal', 'Dr. Sanjay Mehta', 'Dr. Divya Pillai',
                'Dr. Rahul Bansal', 'Dr. Nidhi Malhotra', 'Dr. Arjun Bose',
                'Dr. Swati Kulkarni', 'Dr. Nitin Jain', 'Dr. Priyanka Das',
                'Dr. Varun Saxena', 'Dr. Shruti Kapoor', 'Dr. Ashok Shetty',
                'Dr. Rekha Pandey', 'Dr. Sachin Naidu', 'Dr. Vidya Bhatt'
            ]
            
            hospitals = [
                'Apollo Hospital', 'Fortis Healthcare', 'Max Hospital',
                'Medanta', 'AIIMS', 'Manipal Hospital', 'Narayana Health',
                'Columbia Asia', 'Global Hospital', 'Lilavati Hospital',
                'Kokilaben Hospital', 'BLK Hospital', 'Indraprastha Apollo',
                'Continental Hospital', 'Yashoda Hospital'
            ]
            
            qualifications = [
                'MBBS, MD (Medicine)', 'MBBS, MD (Neurology)', 
                'MBBS, DNB (Medicine)', 'MBBS, MD, DM (Neurology)',
                'MBBS, MD (Internal Medicine)', 'MBBS, MS, MCh (Neurosurgery)'
            ]
            
            print("👨‍⚕️ Inserting sample doctors...")
            
            doctors_inserted = 0
            for city, state in indian_cities:
                # Insert 3-5 doctors per city
                num_doctors = random.randint(3, 5)
                
                for _ in range(num_doctors):
                    # Get Neurologist specialization_id
                    cursor.execute("SELECT specialization_id FROM specializations WHERE specialization_name = 'Neurologist'")
                    neuro_spec_id = cursor.fetchone()[0]
                    
                    # Get other specialization randomly
                    cursor.execute("SELECT specialization_id FROM specializations ORDER BY RAND() LIMIT 1")
                    random_spec_id = cursor.fetchone()[0]
                    
                    # 70% Neurologists, 30% others
                    spec_id = neuro_spec_id if random.random() < 0.7 else random_spec_id
                    
                    doctor_data = (
                        random.choice(doctor_names),
                        spec_id,
                        random.choice(qualifications),
                        random.randint(5, 25),  # experience
                        random.choice(hospitals),
                        city,
                        state,
                        f'{random.randint(1, 999)}, MG Road, {city}',
                        f'+91-{random.randint(7000000000, 9999999999)}',
                        None,  # email
                        random.randint(500, 2000),  # consultation fee
                        round(random.uniform(3.5, 5.0), 2),  # rating
                        random.randint(50, 500),  # total reviews
                        random.choice(['Available', 'Available', 'Available', 'Busy'])  # 75% available
                    )
                    
                    cursor.execute('''
                        INSERT INTO doctors 
                        (full_name, specialization_id, qualification, experience_years, 
                         hospital_name, city, state, address, phone, email, 
                         consultation_fee, rating, total_reviews, availability)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', doctor_data)
                    doctors_inserted += 1
            
            connection.commit()
            print(f"✅ Inserted {doctors_inserted} doctors\n")
            
            # Summary
            cursor.execute("SELECT COUNT(*) FROM doctors")
            total_doctors = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT city, COUNT(*) as count 
                FROM doctors 
                GROUP BY city 
                ORDER BY count DESC 
                LIMIT 10
            ''')
            city_stats = cursor.fetchall()
            
            print("📊 Database Summary:")
            print(f"Total Doctors: {total_doctors}")
            print("\nDoctors by City (Top 10):")
            for city, count in city_stats:
                print(f"  - {city}: {count} doctors")
            
            cursor.execute('''
                SELECT s.specialization_name, COUNT(*) as count
                FROM doctors d
                JOIN specializations s ON d.specialization_id = s.specialization_id
                GROUP BY s.specialization_name
                ORDER BY count DESC
            ''')
            spec_stats = cursor.fetchall()
            
            print("\nDoctors by Specialization:")
            for spec, count in spec_stats:
                print(f"  - {spec}: {count} doctors")
            
    except Error as e:
        print(f"❌ MySQL Error: {e}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("\n🔌 Database connection closed")

if __name__ == "__main__":
    print("🚀 Starting doctors data import...\n")
    import_sample_doctors()