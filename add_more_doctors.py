import mysql.connector
import random

connection = mysql.connector.connect(
    host='localhost',
    user='root',
    password='root',  # Your password
    database='project'
)

cursor = connection.cursor()

# Add more cities
more_cities = [
    ('Surat', 'Gujarat'),
    ('Kanpur', 'Uttar Pradesh'),
    ('Nagpur', 'Maharashtra'),
    ('Visakhapatnam', 'Andhra Pradesh'),
    ('Patna', 'Bihar'),
    ('Ludhiana', 'Punjab'),
    ('Agra', 'Uttar Pradesh'),
    ('Nashik', 'Maharashtra'),
    ('Vadodara', 'Gujarat'),
    ('Rajkot', 'Gujarat')
]

cursor.execute("SELECT specialization_id FROM specializations WHERE specialization_name = 'Neurologist'")
neuro_spec_id = cursor.fetchone()[0]

doctor_names = [
    'Dr. Ramesh Kumar', 'Dr. Lakshmi Devi', 'Dr. Prakash Rao',
    'Dr. Gayatri Iyer', 'Dr. Mohan Lal', 'Dr. Saritha Reddy',
    'Dr. Vinod Singh', 'Dr. Madhavi Sharma', 'Dr. Ajay Patel'
]

for city, state in more_cities:
    for _ in range(2):  # 2 doctors per city
        cursor.execute('''
            INSERT INTO doctors 
            (full_name, specialization_id, qualification, experience_years, 
             hospital_name, city, state, address, phone, 
             consultation_fee, rating, total_reviews, availability)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            random.choice(doctor_names),
            neuro_spec_id,
            'MBBS, MD (Neurology)',
            random.randint(8, 20),
            f'{random.choice(["Apollo", "Fortis", "Max"])} Hospital',
            city, state,
            f'MG Road, {city}',
            f'+91-{random.randint(7000000000, 9999999999)}',
            random.randint(600, 1500),
            round(random.uniform(3.8, 5.0), 2),
            random.randint(60, 300),
            'Available'
        ))

connection.commit()
print(f"✅ Added {len(more_cities) * 2} more doctors!")
cursor.close()
connection.close()