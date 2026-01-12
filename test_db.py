#!/usr/bin/env python3
"""
Database connection test for Ostrich Customer API
"""
import os
import pymysql
from contextlib import contextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'password'),
    'database': os.getenv('DB_NAME', 'ostrich_db'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'charset': 'utf8mb4',
    'ssl': {'ssl_mode': 'REQUIRED'}
}

@contextmanager
def get_db_connection():
    connection = None
    try:
        print(f"Attempting to connect to database...")
        print(f"Host: {DB_CONFIG['host']}")
        print(f"Port: {DB_CONFIG['port']}")
        print(f"Database: {DB_CONFIG['database']}")
        print(f"User: {DB_CONFIG['user']}")
        
        connection = pymysql.connect(**DB_CONFIG)
        print("Database connection successful!")
        yield connection
    except Exception as e:
        print("Database connection failed: {}".format(e))
        yield None
    finally:
        if connection:
            connection.close()
            print("Database connection closed.")

def test_products_query():
    """Test products query"""
    with get_db_connection() as conn:
        if conn:
            try:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("SELECT COUNT(*) as count FROM products WHERE is_active = 1")
                result = cursor.fetchone()
                print("Products table query successful: {} active products".format(result['count']))
                cursor.close()
                return True
            except Exception as e:
                print("Products query failed: {}".format(e))
                return False
        return False

def test_customers_query():
    """Test customers query"""
    with get_db_connection() as conn:
        if conn:
            try:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("SELECT COUNT(*) as count FROM customers WHERE has_mobile_access = 1")
                result = cursor.fetchone()
                print("Customers table query successful: {} mobile customers".format(result['count']))
                cursor.close()
                return True
            except Exception as e:
                print("Customers query failed: {}".format(e))
                return False
        return False

def test_tables_exist():
    """Test if required tables exist"""
    tables = ['products', 'customers', 'product_categories', 'sales', 'sale_items', 'service_tickets']
    
    with get_db_connection() as conn:
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SHOW TABLES")
                existing_tables = [row[0] for row in cursor.fetchall()]
                cursor.close()
                
                print("Existing tables: {}".format(existing_tables))
                
                missing_tables = [table for table in tables if table not in existing_tables]
                if missing_tables:
                    print("Missing tables: {}".format(missing_tables))
                    return False
                else:
                    print("All required tables exist")
                    return True
            except Exception as e:
                print("Failed to check tables: {}".format(e))
                return False
        return False

if __name__ == "__main__":
    print("Testing Ostrich Customer API Database Connection")
    print("=" * 50)
    
    # Test basic connection
    with get_db_connection() as conn:
        if not conn:
            print("Cannot proceed - database connection failed")
            exit(1)
    
    print("\nTesting table existence...")
    if not test_tables_exist():
        print("Cannot proceed - missing required tables")
        exit(1)
    
    print("\nTesting products query...")
    test_products_query()
    
    print("\nTesting customers query...")
    test_customers_query()
    
    print("\nDatabase tests completed!")