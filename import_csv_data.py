import csv
import mysql.connector
from mysql.connector import Error

def import_csv_to_mysql(csv_file_path):
    """Import CSV data into MySQL database"""
    
    connection = None  # Initialize connection variable
    
    try:
        # Connect to MySQL - CHANGE PASSWORD HERE
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='root',  # ← PUT YOUR PASSWORD HERE
            database='project'
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            print("✅ Connected to MySQL database")
            
            # Clear existing data (optional)
            cursor.execute("TRUNCATE TABLE disease_symptoms")
            print("🗑️  Cleared existing data")
            
            # Read CSV file
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                
                insert_query = """
                INSERT INTO disease_symptoms 
                (fever, headache, nausea, vomiting, fatigue, joint_pain, 
                 skin_rash, cough, weight_loss, yellow_eyes, disease)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                count = 0
                for row in csv_reader:
                    values = (
                        int(row['fever']),
                        int(row['headache']),
                        int(row['nausea']),
                        int(row['vomiting']),
                        int(row['fatigue']),
                        int(row['joint_pain']),
                        int(row['skin_rash']),
                        int(row['cough']),
                        int(row['weight_loss']),
                        int(row['yellow_eyes']),
                        row['disease']
                    )
                    
                    cursor.execute(insert_query, values)
                    count += 1
                
                connection.commit()
                print(f"✅ Successfully imported {count} records!")
                
                # Display summary
                cursor.execute("SELECT COUNT(*) FROM disease_symptoms")
                total = cursor.fetchone()[0]
                
                cursor.execute("SELECT DISTINCT disease, COUNT(*) as count FROM disease_symptoms GROUP BY disease")
                diseases = cursor.fetchall()
                
                print(f"\n📊 Database Summary:")
                print(f"Total records: {total}")
                print(f"\nDiseases in database:")
                for disease, cnt in diseases:
                    print(f"  - {disease}: {cnt} symptom patterns")
                
    except Error as e:
        print(f"❌ MySQL Error: {e}")
        print("\n💡 Common fixes:")
        print("  1. Check if MySQL is running")
        print("  2. Verify your password in line 11")
        print("  3. Make sure database 'project' exists")
        print("  4. Check if table 'disease_symptoms' is created")
    
    except FileNotFoundError:
        print(f"❌ File not found: {csv_file_path}")
        print("💡 Make sure your CSV file is in the project folder")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("\n🔌 Database connection closed")

if __name__ == "__main__":
    # Change this to your CSV file path
    csv_file = "dataset.csv"  # Put your CSV file in the project root
    
    print("🚀 Starting CSV import...\n")
    import_csv_to_mysql(csv_file)