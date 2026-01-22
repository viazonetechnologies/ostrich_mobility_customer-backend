import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def add_push_notification_column():
    """Add push_notifications column to customer_preferences table"""
    try:
        connection = pymysql.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            port=int(os.getenv('DB_PORT', 3306)),
            ssl={'ssl': True}
        )
        
        cursor = connection.cursor()
        
        # Check if column exists first
        cursor.execute("""
            SELECT COUNT(*) as count FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'customer_preferences' 
            AND COLUMN_NAME = 'push_notifications'
        """, [os.getenv('DB_NAME')])
        
        result = cursor.fetchone()
        
        if result[0] == 0:
            # Add push_notifications column
            alter_query = """
            ALTER TABLE customer_preferences 
            ADD COLUMN push_notifications BOOLEAN DEFAULT TRUE 
            AFTER sms_notifications
            """
            
            cursor.execute(alter_query)
            connection.commit()
            print("Successfully added push_notifications column")
        else:
            print("push_notifications column already exists")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_push_notification_column()
