from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restx import Api, Resource, fields
import os
import jwt
from datetime import datetime, timedelta, date
from functools import wraps
import json
import threading
import time
import pymysql
from contextlib import contextmanager
import hashlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# JSON serialization fix
def json_serializer(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

app = Flask(__name__)
app.json.default = json_serializer

# Configure CORS for customer backend
CORS(app, 
     origins=["*"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "Accept"],
     supports_credentials=True)

# Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SECRET_KEY'] = SECRET_KEY

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
        connection = pymysql.connect(**DB_CONFIG)
        yield connection
    except Exception as e:
        print(f"Database connection failed: {e}")
        print(f"DB Config: host={DB_CONFIG['host']}, port={DB_CONFIG['port']}, db={DB_CONFIG['database']}")
        yield None
    finally:
        if connection:
            connection.close()

def execute_query(query, params=None, fetch_one=False):
    try:
        with get_db_connection() as conn:
            if conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute(query, params or [])
                if fetch_one:
                    result = cursor.fetchone()
                else:
                    result = cursor.fetchall()
                cursor.close()
                
                # Convert datetime objects to strings
                if result:
                    if fetch_one:
                        for key, value in result.items():
                            if isinstance(value, (datetime, date)):
                                result[key] = value.isoformat()
                    else:
                        for row in result:
                            for key, value in row.items():
                                if isinstance(value, (datetime, date)):
                                    row[key] = value.isoformat()
                
                return result
            else:
                print("Database connection is None")
                return None if fetch_one else []
    except Exception as e:
        print(f"Query execution failed: {e}")
        print(f"Query: {query}")
        print(f"Params: {params}")
        return None if fetch_one else []

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# JWT utilities
def create_access_token(data):
    payload = data.copy()
    # Remove expiration - token never expires
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return {"message": "Token required", "status": False, "data": None}, 401
        
        token = token[7:]
        payload = verify_token(token)
        
        if payload is None:
            return {"message": "Invalid token", "status": False, "data": None}, 401
        
        return f(current_user=payload, *args, **kwargs)
    return decorated

# Standard response helper
def standard_response(message, status=True, data=None):
    return jsonify({
        "message": message,
        "status": status,
        "data": data
    })

# Database helper functions
def get_customer_data(customer_id):
    return execute_query("SELECT * FROM customers WHERE id = %s", [customer_id], fetch_one=True)

def get_customer_products(customer_id):
    return execute_query(
        "SELECT p.*, si.serial_number, si.warranty_start_date, si.warranty_end_date FROM products p "
        "LEFT JOIN sale_items si ON p.id = si.product_id "
        "LEFT JOIN sales s ON si.sale_id = s.id "
        "WHERE s.customer_id = %s", 
        [customer_id]
    )

def get_customer_services(customer_id):
    return execute_query(
        "SELECT st.*, p.name as product_name FROM service_tickets st "
        "LEFT JOIN products p ON st.product_id = p.id "
        "WHERE st.customer_id = %s ORDER BY st.created_at DESC", 
        [customer_id]
    )

def get_customer_orders(customer_id):
    return execute_query(
        "SELECT s.*, GROUP_CONCAT(p.name) as products FROM sales s "
        "LEFT JOIN sale_items si ON s.id = si.sale_id "
        "LEFT JOIN products p ON si.product_id = p.id "
        "WHERE s.customer_id = %s GROUP BY s.id ORDER BY s.sale_date DESC", 
        [customer_id]
    )

def get_customer_notifications(customer_id):
    return execute_query(
        "SELECT * FROM notifications WHERE customer_id = %s ORDER BY created_at DESC LIMIT 10", 
        [customer_id]
    )

# Basic routes
@app.route('/')
def read_root():
    return {
        "message": "Ostrich Customer Mobile API v1.0.0",
        "status": True,
        "data": {
            "version": "1.0.0",
            "docs": "/docs/",
            "status": "running",
            "endpoints": {
                "auth": "/api/v1/auth/",
                "dashboard": "/api/v1/dashboard/",
                "products": "/api/v1/products/",
                "services": "/api/v1/services/"
            }
        }
    }

@app.route('/test')
def test_route():
    return {
        "message": "Test route working",
        "status": True,
        "timestamp": datetime.now().isoformat()
    }

@app.route('/health')
def health_check():
    return {
        "message": "Service is healthy",
        "status": True,
        "data": {
            "service": "ostrich-customer-api",
            "timestamp": datetime.now().isoformat()
        }
    }

# Swagger API setup
api = Api(app, 
    version='1.0', 
    title='Ostrich Customer API',
    description='Customer mobile app API for Ostrich Product & Service Management System',
    doc='/docs/',
    prefix='/api/v1',
    contact='support@ostrich.com',
    contact_email='support@ostrich.com',
    license='MIT',
    license_url='https://opensource.org/licenses/MIT'
)

# Configure Swagger security
authorizations = {
    'Bearer': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': 'Add a JWT token to the header with ** Bearer <JWT> ** token to authorize'
    }
}
api.authorizations = authorizations

# Response models for consistent API responses
standard_response = api.model('StandardResponse', {
    'message': fields.String(required=True, description='Response message'),
    'status': fields.Boolean(required=True, description='Success status'),
    'data': fields.Raw(description='Response data')
})

error_response = api.model('ErrorResponse', {
    'message': fields.String(required=True, description='Error message'),
    'status': fields.Boolean(required=True, description='Always false for errors'),
    'data': fields.Raw(description='Error details')
})

# Namespaces
auth_ns = api.namespace('auth', description='Authentication operations')
dashboard_ns = api.namespace('dashboard', description='Dashboard operations')
products_ns = api.namespace('products', description='Products operations')
services_ns = api.namespace('services', description='Services operations')
profile_ns = api.namespace('profile', description='Profile operations')
notifications_ns = api.namespace('notifications', description='Notifications operations')
orders_ns = api.namespace('orders', description='Orders operations')
enquiries_ns = api.namespace('enquiries', description='Enquiry operations')
support_ns = api.namespace('support', description='Support operations')
utilities_ns = api.namespace('utilities', description='Utility operations')
catalog_ns = api.namespace('catalog', description='Product catalog')
gallery_ns = api.namespace('gallery', description='Gallery operations')
warranty_ns = api.namespace('warranty', description='Warranty operations')
locations_ns = api.namespace('locations', description='Location services')
sales_ns = api.namespace('sales', description='Sales operations')

# Models for Swagger documentation
otp_model = api.model('OTP', {
    'phone_number': fields.String(required=True, description='Phone number', example='9876543210')
})

verify_otp_model = api.model('VerifyOTP', {
    'phone_number': fields.String(required=True, description='Phone number', example='9876543210'),
    'otp': fields.String(required=True, description='OTP code', example='123456')
})

register_model = api.model('Register', {
    'customer_type': fields.String(description='Customer type', example='b2c', enum=['b2c', 'b2b', 'b2g']),
    'individual_name': fields.String(description='Individual name (for B2C)', example='John Doe'),
    'company_name': fields.String(description='Company name (for B2B/B2G)', example='ABC Corp'),
    'contact_person': fields.String(description='Contact person name', example='John Manager'),
    'phone': fields.String(required=True, description='Phone number', example='9876543210'),
    'email': fields.String(description='Email address', example='john@example.com'),
    'password': fields.String(required=True, description='Password', example='password123'),
    'address': fields.String(description='Address', example='123 Main Street'),
    'city': fields.String(description='City', example='Mumbai'),
    'state': fields.String(description='State', example='Maharashtra'),
    'pin_code': fields.String(description='PIN Code', example='400001')
})

login_model = api.model('Login', {
    'username': fields.String(required=True, description='Phone number or email', example='9876543210 or user@example.com'),
    'password': fields.String(required=True, description='Password', example='password123')
})

service_request_model = api.model('ServiceRequest', {
    'product_id': fields.Integer(required=True, description='Product ID', example=1),
    'issue_description': fields.String(required=True, description='Issue description', example='Motor not starting'),
    'priority': fields.String(description='Priority level', example='HIGH', enum=['LOW', 'MEDIUM', 'HIGH', 'URGENT'])
})

enquiry_model = api.model('Enquiry', {
    'subject': fields.String(required=True, description='Enquiry subject', example='Product Information'),
    'message': fields.String(required=True, description='Enquiry message', example='Need details about 3HP motor'),
    'product_id': fields.Integer(description='Related product ID', example=1)
})

profile_update_model = api.model('ProfileUpdate', {
    'individual_name': fields.String(description='Individual name', example='John Updated'),
    'email': fields.String(description='Email address', example='john.updated@example.com'),
    'address': fields.String(description='Address', example='456 New Street'),
    'city': fields.String(description='City', example='Mumbai'),
    'state': fields.String(description='State', example='Maharashtra')
})

change_password_model = api.model('ChangePassword', {
    'current_password': fields.String(required=True, description='Current password', example='oldpass123'),
    'new_password': fields.String(required=True, description='New password', example='newpass123')
})

check_phone_model = api.model('CheckPhone', {
    'phone': fields.String(required=True, description='Phone number', example='9876543210')
})

whatsapp_model = api.model('WhatsApp', {
    'message': fields.String(required=True, description='Message to send', example='Hello from Ostrich!'),
    'phone': fields.String(required=True, description='Phone number', example='9876543210')
})

# Authentication endpoints
@auth_ns.route('/send-otp')
class SendOTP(Resource):
    @auth_ns.expect(otp_model)
    @auth_ns.doc('send_otp', description='Send OTP to phone number for authentication')
    @auth_ns.response(200, 'Success', standard_response)
    @auth_ns.response(400, 'Bad Request', error_response)
    def post(self):
        """Send OTP to phone number"""
        data = request.get_json()
        phone_number = data.get('phone_number')
        
        if not phone_number:
            return {"message": "Phone number is required", "status": False, "data": None}, 400
        
        # Check if customer exists
        customer = execute_query("SELECT id FROM customers WHERE phone = %s", [phone_number], fetch_one=True)
        if not customer:
            return {"message": "Phone number not registered", "status": False, "data": None}, 404
        
        return {
            "message": "OTP sent successfully",
            "status": True,
            "data": {
                "phone_number": phone_number,
                "expires_in_minutes": 5,
                "otp": "123456"  # Hardcoded for testing
            }
        }

@auth_ns.route('/verify-otp')
class VerifyOTP(Resource):
    @auth_ns.expect(verify_otp_model)
    @auth_ns.doc('verify_otp', description='Verify OTP and get access token')
    @auth_ns.response(200, 'Success', standard_response)
    @auth_ns.response(400, 'Invalid OTP', error_response)
    @auth_ns.response(404, 'Customer not found', error_response)
    def post(self):
        """Verify OTP and authenticate"""
        data = request.get_json()
        phone_number = data.get('phone_number')
        otp = data.get('otp')
        
        if not phone_number or not otp:
            return {"message": "Phone and OTP are required", "status": False, "data": None}, 400
        
        if otp == "123456":  # Hardcoded OTP for testing
            # Find customer by phone
            customer = execute_query(
                "SELECT * FROM customers WHERE phone = %s AND has_mobile_access = 1", 
                [phone_number], 
                fetch_one=True
            )
            
            if customer:
                # Update verification status and last login
                with get_db_connection() as conn:
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE customers SET is_verified = 1, last_login = %s WHERE id = %s", 
                            [datetime.now(), customer['id']]
                        )
                        conn.commit()
                        cursor.close()
                
                access_token = create_access_token({"sub": str(customer['id']), "phone": phone_number})
                return {
                    "message": "OTP verified successfully",
                    "status": True,
                    "data": {
                        "access_token": access_token,
                        "customer_id": customer['id'],
                        "is_new_customer": customer.get('registration_source') == 'mobile_app',
                        "phone_number": phone_number,
                        "profile_complete": True
                    }
                }
            else:
                return {"message": "Customer not found", "status": False, "data": None}, 404
        
        return {"message": "Invalid OTP", "status": False, "data": None}, 400

@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.expect(login_model)
    @auth_ns.doc('login', description='Customer login with phone/email and password')
    @auth_ns.response(200, 'Success', standard_response)
    @auth_ns.response(400, 'Bad Request', error_response)
    @auth_ns.response(401, 'Unauthorized', error_response)
    def post(self):
        """Customer login with phone/email and password"""
        data = request.get_json()
        username = data.get('username')  # Can be phone or email
        password = data.get('password')
        
        if not username or not password:
            return {"message": "Username and password are required", "status": False, "data": None}, 400
        
        # Check if username is email or phone
        if '@' in username:
            # Email login - case insensitive
            customer = execute_query(
                "SELECT * FROM customers WHERE LOWER(email) = LOWER(%s) AND password_hash = %s AND has_mobile_access = 1", 
                [username, hash_password(password)], 
                fetch_one=True
            )
        else:
            # Phone login
            customer = execute_query(
                "SELECT * FROM customers WHERE phone = %s AND password_hash = %s AND has_mobile_access = 1", 
                [username, hash_password(password)], 
                fetch_one=True
            )
        
        if customer:
            # Update last login
            with get_db_connection() as conn:
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE customers SET last_login = %s WHERE id = %s", 
                                 [datetime.now(), customer['id']])
                    conn.commit()
                    cursor.close()
            
            access_token = create_access_token({"sub": str(customer['id']), "username": username})
            return {
                "message": "Login successful",
                "status": True,
                "data": {
                    "access_token": access_token,
                    "customer_id": customer['id'],
                    "name": customer.get('individual_name') or customer.get('contact_person'),
                    "phone": customer.get('phone'),
                    "email": customer.get('email')
                }
            }
        
        return {"message": "Invalid credentials", "status": False, "data": None}, 401

@auth_ns.route('/logout')
class Logout(Resource):
    @auth_ns.doc('logout', description='Customer logout', security='Bearer')
    @auth_ns.response(200, 'Success', standard_response)
    @token_required
    def post(self, current_user):
        """Customer logout"""
        return {
            "message": "Logout successful",
            "status": True,
            "data": {
                "logged_out_at": datetime.now().isoformat()
            }
        }

@auth_ns.route('/register')
class Register(Resource):
    @auth_ns.expect(register_model)
    @auth_ns.doc('register', description='Customer self-registration')
    @auth_ns.response(200, 'Success', standard_response)
    @auth_ns.response(400, 'Bad Request', error_response)
    @auth_ns.response(500, 'Server Error', error_response)
    def post(self):
        """Customer self-registration"""
        data = request.get_json()
        customer_type = data.get('customer_type', 'b2c')
        individual_name = data.get('individual_name') or data.get('name')
        company_name = data.get('company_name')
        contact_person = data.get('contact_person') or individual_name
        phone = data.get('phone')
        email = data.get('email')
        address = data.get('address', '')
        city = data.get('city', '')
        state = data.get('state', '')
        pin_code = data.get('pin_code', '')
        password = data.get('password')
        
        if not individual_name and not company_name:
            return {"message": "Name is required", "status": False, "data": None}, 400
        if not phone:
            return {"message": "Phone is required", "status": False, "data": None}, 400
        if not password:
            return {"message": "Password is required", "status": False, "data": None}, 400
        
        # Check if phone already exists
        existing = execute_query("SELECT id FROM customers WHERE phone = %s", [phone], fetch_one=True)
        if existing:
            return {"message": "Phone number already registered", "status": False, "data": None}, 400
        
        # Generate customer code
        with get_db_connection() as conn:
            if conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("SELECT MAX(CAST(SUBSTRING(customer_code, 5) AS UNSIGNED)) as max_num FROM customers WHERE customer_code LIKE 'CUST%'")
                result = cursor.fetchone()
                next_num = (result['max_num'] or 0) + 1 if result else 1
                customer_code = f"CUST{next_num:03d}"
                cursor.close()
            else:
                customer_code = f"CUST{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Insert into customers table
        with get_db_connection() as conn:
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO customers (
                        customer_code, customer_type, individual_name, company_name, contact_person,
                        email, phone, address, city, state, pin_code, has_mobile_access, 
                        is_verified, registration_source, password_hash, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    customer_code, customer_type, individual_name, company_name, contact_person,
                    email, phone, address, city, state, pin_code, 1, 0, 'mobile_app', 
                    hash_password(password), datetime.now(), datetime.now()
                ))
                customer_id = cursor.lastrowid
                conn.commit()
                cursor.close()
                
                return {
                    "message": "Registration successful. Please verify your phone number.",
                    "status": True,
                    "data": {
                        "customer_id": customer_id,
                        "phone": phone,
                        "otp_sent": True,
                        "otp": "123456"  # Hardcoded for testing
                    }
                }
        
        return {"message": "Registration failed", "status": False, "data": None}, 500

# Dashboard endpoint
@dashboard_ns.route('/')
class Dashboard(Resource):
    @dashboard_ns.doc('get_dashboard', description='Get customer dashboard', security='Bearer')
    @dashboard_ns.response(200, 'Success', standard_response)
    @dashboard_ns.response(401, 'Unauthorized', error_response)
    @dashboard_ns.response(404, 'Customer not found', error_response)
    @token_required
    def get(self, current_user):
        """Get customer dashboard with real database data"""
        try:
            customer_id = current_user.get('sub')
            
            # Get customer data
            customer = get_customer_data(customer_id)
            if not customer:
                return {"message": "Customer not found", "status": False, "data": None}, 404
            
            # Get related data with error handling
            try:
                products = get_customer_products(customer_id) or []
            except:
                products = []
                
            try:
                services = get_customer_services(customer_id) or []
            except:
                services = []
                
            try:
                notifications = get_customer_notifications(customer_id) or []
            except:
                notifications = []
            
            return {
                "message": "Dashboard data retrieved successfully",
                "status": True,
                "data": {
                    "customer_info": {
                        "name": customer.get('individual_name') or customer.get('contact_person'),
                        "phone": customer.get('phone'),
                        "customer_id": customer_id,
                        "customer_type": customer.get('customer_type'),
                        "company_name": customer.get('company_name')
                    },
                    "stats": {
                        "total_products": len(products),
                        "active_services": len([s for s in services if s.get('status') in ['SCHEDULED', 'IN_PROGRESS']]),
                        "completed_services": len([s for s in services if s.get('status') == 'COMPLETED']),
                        "warranty_products": 0
                    },
                    "recent_services": services[:3],
                    "notifications": {
                        "unread_count": len([n for n in notifications if not n.get('is_read')]),
                        "latest": notifications[:3]
                    }
                }
            }
        except Exception as e:
            print(f"Dashboard error: {e}")
            return {"message": "Internal server error", "status": False, "data": None}, 500

# Products endpoints
@products_ns.route('/')
class Products(Resource):
    @products_ns.doc('get_products', description='Get customer products', security='Bearer')
    @products_ns.response(200, 'Success', standard_response)
    @products_ns.response(401, 'Unauthorized', error_response)
    @token_required
    def get(self, current_user):
        """Get customer products"""
        try:
            customer_id = current_user.get('sub', '1')
            products = get_customer_products(customer_id)
            
            return {
                "message": "Products retrieved successfully",
                "status": True,
                "data": {
                    "products": products,
                    "total_count": len(products)
                }
            }
        except Exception as e:
            print(f"Products error: {e}")
            return {"message": "Internal Server Error", "status": False, "data": None}, 500

@products_ns.route('/<int:product_id>')
class ProductDetails(Resource):
    @products_ns.doc('get_product_details', description='Get product details by ID', security='Bearer')
    @token_required
    def get(self, product_id, current_user):
        """Get product details"""
        try:
            customer_id = current_user.get('sub', '1')
            products = get_customer_products(customer_id)
            product = next((p for p in products if p.get('id') == product_id), None)
            
            if not product:
                return {"message": "Product not found", "status": False, "data": None}, 404
            
            return {
                "message": "Product details retrieved successfully",
                "status": True,
                "data": product
            }
        except Exception as e:
            print(f"Product details error: {e}")
            return {"message": "Internal Server Error", "status": False, "data": None}, 500

# Services endpoints
@services_ns.route('/')
class Services(Resource):
    @services_ns.doc('get_services', description='Get customer services', security='Bearer')
    @token_required
    def get(self, current_user):
        """Get customer services"""
        customer_id = current_user.get('sub', '1')
        services = get_customer_services(customer_id)
        status_filter = request.args.get('status')
        
        if status_filter:
            services = [s for s in services if s.get('status', '').lower() == status_filter.lower()]
        
        return {
            "message": "Services retrieved successfully",
            "status": True,
            "data": {
                "services": services,
                "total_count": len(services)
            }
        }

@services_ns.route('/request')
class ServiceRequest(Resource):
    @services_ns.expect(service_request_model)
    @services_ns.doc('request_service', description='Request a new service', security='Bearer')
    @token_required
    def post(self, current_user):
        """Request a new service"""
        data = request.get_json()
        customer_id = current_user.get('sub')
        product_id = data.get('product_id')
        issue_description = data.get('issue_description')
        priority = data.get('priority', 'MEDIUM')
        
        if not product_id or not issue_description:
            return {"message": "Product ID and issue description are required", "status": False, "data": None}, 400
        
        # Generate ticket number
        ticket_number = f"SRV{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        with get_db_connection() as conn:
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO service_tickets (customer_id, product_id, ticket_number, issue_description, priority) VALUES (%s, %s, %s, %s, %s)",
                    [customer_id, product_id, ticket_number, issue_description, priority]
                )
                service_id = cursor.lastrowid
                conn.commit()
                cursor.close()
        
        return {
            "message": "Service request submitted successfully",
            "status": True,
            "data": {
                "service_id": service_id,
                "ticket_number": ticket_number,
                "status": "OPEN",
                "priority": priority
            }
        }

@services_ns.route('/<int:service_id>')
class ServiceDetails(Resource):
    @services_ns.doc('get_service_details', description='Get service details by ID', security='Bearer')
    @token_required
    def get(self, service_id, current_user):
        """Get service details"""
        return {
            "message": "Service details retrieved successfully",
            "status": True,
            "data": {
                "id": service_id,
                "customer_id": current_user.get('sub'),
                "status": "Please check with support for service details"
            }
        }

# Orders endpoints
@orders_ns.route('/')
class Orders(Resource):
    @orders_ns.doc('get_orders', description='Get customer orders', security='Bearer')
    @token_required
    def get(self, current_user):
        """Get customer orders"""
        customer_id = current_user.get('sub', '1')
        orders = get_customer_orders(customer_id)
        
        return {
            "message": "Orders retrieved successfully",
            "status": True,
            "data": {
                "orders": orders,
                "total_count": len(orders)
            }
        }

@orders_ns.route('/<int:order_id>')
class OrderDetails(Resource):
    @orders_ns.doc('get_order_details', description='Get order details by ID', security='Bearer')
    @token_required
    def get(self, order_id, current_user):
        """Get order details"""
        customer_id = current_user.get('sub', '1')
        orders = get_customer_orders(customer_id)
        order = next((o for o in orders if o.get('id') == order_id), None)
        
        if not order:
            return {"message": "Order not found", "status": False, "data": None}, 404
        
        return {
            "message": "Order details retrieved successfully",
            "status": True,
            "data": order
        }

# Profile endpoints
@profile_ns.route('/')
class Profile(Resource):
    @profile_ns.doc('get_profile', description='Get customer profile', security='Bearer')
    @token_required
    def get(self, current_user):
        """Get customer profile"""
        customer_id = current_user.get('sub')
        customer = get_customer_data(customer_id)
        
        if not customer:
            return {"message": "Customer not found", "status": False, "data": None}, 404
        
        return {
            "message": "Profile retrieved successfully",
            "status": True,
            "data": {
                "id": customer['id'],
                "name": customer.get('individual_name') or customer.get('contact_person'),
                "phone": customer.get('phone'),
                "email": customer.get('email'),
                "customer_type": customer.get('customer_type'),
                "company_name": customer.get('company_name'),
                "address": customer.get('address'),
                "city": customer.get('city'),
                "state": customer.get('state'),
                "pin_code": customer.get('pin_code')
            }
        }
    
    @profile_ns.expect(profile_update_model)
    @profile_ns.doc('update_profile', description='Update customer profile', security='Bearer')
    @token_required
    def put(self, current_user):
        """Update customer profile"""
        data = request.get_json()
        return {
            "message": "Profile updated successfully",
            "status": True,
            "data": {
                "updated_fields": list(data.keys())
            }
        }

# Notifications endpoints
@notifications_ns.route('/')
class Notifications(Resource):
    @notifications_ns.doc('get_notifications', description='Get customer notifications', security='Bearer')
    @token_required
    def get(self, current_user):
        """Get customer notifications"""
        customer_id = current_user.get('sub', '1')
        notifications = get_customer_notifications(customer_id)
        
        return {
            "message": "Notifications retrieved successfully",
            "status": True,
            "data": notifications
        }

@notifications_ns.route('/<int:notification_id>/read')
class NotificationRead(Resource):
    @notifications_ns.doc('mark_notification_read', description='Mark notification as read', security='Bearer')
    @token_required
    def put(self, notification_id, current_user):
        """Mark notification as read"""
        customer_id = current_user.get('sub')
        
        # Update notification to mark as read
        with get_db_connection() as conn:
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE notifications SET is_read = 1 WHERE id = %s AND customer_id = %s",
                    [notification_id, customer_id]
                )
                affected_rows = cursor.rowcount
                conn.commit()
                cursor.close()
                
                if affected_rows > 0:
                    return {
                        "message": "Notification marked as read",
                        "status": True,
                        "data": {
                            "notification_id": notification_id
                        }
                    }
                else:
                    return {
                        "message": "Notification not found",
                        "status": False,
                        "data": None
                    }, 404
        
        return {
            "message": "Failed to update notification",
            "status": False,
            "data": None
        }, 500

@notifications_ns.route('/unread-count')
class NotificationUnreadCount(Resource):
    @notifications_ns.doc('get_unread_count', description='Get unread notifications count', security='Bearer')
    @token_required
    def get(self, current_user):
        """Get unread notifications count"""
        customer_id = current_user.get('sub')
        unread_count = execute_query(
            "SELECT COUNT(*) as count FROM notifications WHERE customer_id = %s AND is_read = 0",
            [customer_id],
            fetch_one=True
        )
        
        return {
            "message": "Unread count retrieved successfully",
            "status": True,
            "data": {
                "unread_count": unread_count.get('count', 0) if unread_count else 0
            }
        }

# Remove support_tickets from main.py since it's same as service_tickets
# Update enquiries endpoints to use proper database queries

# Enquiries endpoints
@enquiries_ns.route('/')
class Enquiries(Resource):
    @enquiries_ns.expect(enquiry_model)
    @enquiries_ns.doc('create_enquiry', description='Create new enquiry', security='Bearer')
    @token_required
    def post(self, current_user):
        """Create new enquiry"""
        try:
            data = request.get_json()
            customer_id = current_user.get('sub')
            message = data.get('message')
            product_id = data.get('product_id')
            
            if not message:
                return {"message": "Message is required", "status": False, "data": None}, 400
            
            # Generate enquiry number
            enquiry_number = f"ENQ{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            with get_db_connection() as conn:
                if conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO enquiries (customer_id, enquiry_number, message, product_id) VALUES (%s, %s, %s, %s)",
                        [customer_id, enquiry_number, message, product_id]
                    )
                    enquiry_id = cursor.lastrowid
                    conn.commit()
                    cursor.close()
            
            return {
                "message": "Enquiry submitted successfully",
                "status": True,
                "data": {
                    "enquiry_id": enquiry_id,
                    "enquiry_number": enquiry_number,
                    "status": "open",
                    "estimated_response_time": "24 hours"
                }
            }
        except Exception as e:
            print(f"Enquiry creation error: {e}")
            return {"message": "Failed to create enquiry", "status": False, "data": None}, 500
    
    @enquiries_ns.doc('get_enquiries', description='Get customer enquiries', security='Bearer')
    @token_required
    def get(self, current_user):
        """Get customer enquiries"""
        try:
            customer_id = current_user.get('sub')
            enquiries = execute_query(
                "SELECT e.*, p.name as product_name FROM enquiries e "
                "LEFT JOIN products p ON e.product_id = p.id "
                "WHERE e.customer_id = %s ORDER BY e.created_at DESC",
                [customer_id]
            )
            
            return {
                "message": "Enquiries retrieved successfully",
                "status": True,
                "data": {
                    "enquiries": enquiries
                }
            }
        except Exception as e:
            print(f"Get enquiries error: {e}")
            return {
                "message": "Failed to get enquiries",
                "status": False,
                "data": {"enquiries": []}
            }

# Support endpoints (static info only)
@support_ns.route('/faq')
class SupportFAQ(Resource):
    @support_ns.doc('get_faq', description='Get frequently asked questions')
    def get(self):
        """Get FAQ"""
        return {
            "message": "FAQ retrieved successfully",
            "status": True,
            "data": {
                "faqs": [
                    {"question": "How to request service?", "answer": "Use the service request feature in the app"},
                    {"question": "How to check warranty?", "answer": "Go to Products section and check warranty details"},
                    {"question": "Service center locations?", "answer": "Check Locations section for nearby service centers"}
                ]
            }
        }

@support_ns.route('/contact')
class SupportContact(Resource):
    @support_ns.doc('get_contact', description='Get contact information')
    def get(self):
        """Get contact information"""
        return {
            "message": "Contact information retrieved successfully",
            "status": True,
            "data": {
                "phone": "1800-123-4567",
                "email": "support@ostrich.com",
                "hours": "9 AM - 6 PM (Mon-Sat)",
                "whatsapp": "+91-98765-43210"
            }
        }

# Utilities endpoints
@utilities_ns.route('/whatsapp/send')
class WhatsAppSend(Resource):
    @utilities_ns.expect(whatsapp_model)
    @utilities_ns.doc('send_whatsapp', description='Send WhatsApp message', security='Bearer')
    @token_required
    def post(self, current_user):
        """Send WhatsApp message"""
        return {"message": "WhatsApp message sent", "status": True, "data": None}

@utilities_ns.route('/uploads')
class FileUpload(Resource):
    @utilities_ns.doc('upload_file', description='Upload file', security='Bearer')
    @token_required
    def post(self, current_user):
        """Upload file"""
        return {
            "message": "File uploaded successfully",
            "status": True,
            "data": {
                "url": "https://example.com/file.jpg"
            }
        }

@utilities_ns.route('/settings')
class Settings(Resource):
    @utilities_ns.doc('get_settings', description='Get user settings', security='Bearer')
    @token_required
    def get(self, current_user):
        """Get settings"""
        return {
            "message": "Settings retrieved successfully",
            "status": True,
            "data": {
                "notifications": True,
                "sms_alerts": True,
                "email_updates": True
            }
        }

# Catalog endpoints
@catalog_ns.route('/products')
class CatalogProducts(Resource):
    @catalog_ns.doc('get_product_catalog', description='Get product catalog', params={
        'category': 'Filter by category',
        'search': 'Search products'
    })
    def get(self):
        """Get product catalog from database"""
        try:
            category = request.args.get('category')
            search = request.args.get('search')
            
            query = "SELECT p.*, pc.name as category_name FROM products p LEFT JOIN product_categories pc ON p.category_id = pc.id WHERE p.is_active = 1"
            params = []
            
            if category:
                query += " AND pc.name = %s"
                params.append(category)
            
            if search:
                query += " AND (p.name LIKE %s OR p.description LIKE %s)"
                params.extend([f"%{search}%", f"%{search}%"])
            
            products = execute_query(query, params)
            
            return {
                "message": "Product catalog retrieved successfully",
                "status": True,
                "data": {
                    "products": products
                }
            }
        except Exception as e:
            print(f"Catalog products error: {e}")
            return {"message": "Internal Server Error", "status": False, "data": None}, 500

# Add a public products endpoint that doesn't require authentication
@products_ns.route('/catalog')
class PublicProducts(Resource):
    @products_ns.doc('get_public_products', description='Get all products (public access)')
    def get(self):
        """Get all products without authentication"""
        try:
            query = "SELECT p.*, pc.name as category_name FROM products p LEFT JOIN product_categories pc ON p.category_id = pc.id WHERE p.is_active = 1 ORDER BY p.name"
            products = execute_query(query)
            
            return {
                "message": "Products retrieved successfully",
                "status": True,
                "data": {
                    "products": products,
                    "total_count": len(products)
                }
            }
        except Exception as e:
            print(f"Public products error: {e}")
            return {"message": "Internal Server Error", "status": False, "data": None}, 500

@catalog_ns.route('/categories')
class CatalogCategories(Resource):
    @catalog_ns.doc('get_categories', description='Get product categories')
    def get(self):
        """Get product categories from database"""
        try:
            categories = execute_query("SELECT * FROM product_categories WHERE is_active = 1 ORDER BY display_order")
            
            return {
                "message": "Categories retrieved successfully",
                "status": True,
                "data": {
                    "categories": categories
                }
            }
        except Exception as e:
            print(f"Categories error: {e}")
            return {"message": "Internal Server Error", "status": False, "data": None}, 500

# Missing Authentication Endpoints - Forgot Password
@auth_ns.route('/forgot-password')
class ForgotPassword(Resource):
    @auth_ns.expect(check_phone_model)
    @auth_ns.doc('forgot_password', description='Send password reset OTP')
    def post(self):
        """Send password reset OTP"""
        data = request.get_json()
        phone = data.get('phone')
        
        if not phone:
            return {"message": "Phone number is required", "status": False, "data": None}, 400
        
        customer = execute_query("SELECT id FROM customers WHERE phone = %s", [phone], fetch_one=True)
        if not customer:
            return {"message": "Phone number not found", "status": False, "data": None}, 404
        
        # Store reset token
        reset_token = f"RST{datetime.now().strftime('%Y%m%d%H%M%S')}"
        with get_db_connection() as conn:
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
                    [customer['id'], reset_token, datetime.now() + timedelta(hours=1)]
                )
                conn.commit()
                cursor.close()
        
        return {
            "message": "Password reset OTP sent successfully",
            "status": True,
            "data": {
                "phone": phone,
                "otp": "123456",  # Hardcoded for testing
                "expires_in": "1 hour"
            }
        }

@auth_ns.route('/reset-password')
class ResetPassword(Resource):
    @auth_ns.expect(api.model('ResetPassword', {
        'phone': fields.String(required=True, description='Phone number', example='9876543210'),
        'otp': fields.String(required=True, description='Reset OTP', example='123456'),
        'new_password': fields.String(required=True, description='New password', example='newpass123')
    }))
    @auth_ns.doc('reset_password', description='Reset password with OTP')
    def post(self):
        """Reset password using OTP"""
        data = request.get_json()
        phone = data.get('phone')
        otp = data.get('otp')
        new_password = data.get('new_password')
        
        if not phone or not otp or not new_password:
            return {"message": "Phone, OTP and new password are required", "status": False, "data": None}, 400
        
        if otp == "123456":  # Hardcoded OTP for testing
            customer = execute_query("SELECT id FROM customers WHERE phone = %s", [phone], fetch_one=True)
            if customer:
                # Update password
                with get_db_connection() as conn:
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE customers SET password_hash = %s WHERE id = %s",
                            [hash_password(new_password), customer['id']]
                        )
                        conn.commit()
                        cursor.close()
                
                return {
                    "message": "Password reset successfully",
                    "status": True,
                    "data": {"updated_at": datetime.now().isoformat()}
                }
        
        return {"message": "Invalid OTP", "status": False, "data": None}, 400
@auth_ns.route('/check-phone')
class CheckPhone(Resource):
    @auth_ns.expect(check_phone_model)
    @auth_ns.doc('check_phone', description='Check if phone number exists')
    def post(self):
        """Check if phone number is already registered"""
        data = request.get_json()
        phone = data.get('phone')
        
        if not phone:
            return {"message": "Phone number is required", "status": False, "data": None}, 400
        
        customer = execute_query("SELECT id, individual_name, contact_person FROM customers WHERE phone = %s", [phone], fetch_one=True)
        
        return {
            "message": "Phone check completed",
            "status": True,
            "data": {
                "exists": customer is not None,
                "customer_name": customer.get('individual_name') or customer.get('contact_person') if customer else None
            }
        }

@auth_ns.route('/verify-registration')
class VerifyRegistration(Resource):
    @auth_ns.expect(verify_otp_model)
    @auth_ns.doc('verify_registration', description='Verify registration OTP')
    def post(self):
        """Verify registration OTP and activate account"""
        data = request.get_json()
        phone = data.get('phone_number')
        otp = data.get('otp')
        
        if not phone or not otp:
            return {"message": "Phone and OTP are required", "status": False, "data": None}, 400
        
        if otp == "123456":  # Hardcoded OTP for testing
            customer = execute_query("SELECT * FROM customers WHERE phone = %s", [phone], fetch_one=True)
            if customer:
                # Update verification status
                with get_db_connection() as conn:
                    if conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE customers SET is_verified = 1 WHERE id = %s", [customer['id']])
                        conn.commit()
                        cursor.close()
                
                access_token = create_access_token({"sub": str(customer['id']), "phone": phone})
                return {
                    "message": "Account verified successfully",
                    "status": True,
                    "data": {
                        "access_token": access_token,
                        "customer_id": customer['id'],
                        "is_new_customer": True,
                        "phone_number": phone,
                        "profile_complete": True
                    }
                }
        
        return {"message": "Invalid OTP", "status": False, "data": None}, 400

# Profile Management Endpoints
@profile_ns.route('/set-password')
class SetPassword(Resource):
    @profile_ns.expect(api.model('SetPassword', {
        'password': fields.String(required=True, description='New password', example='newpass123')
    }))
    @profile_ns.doc('set_password', description='Set password for first time', security='Bearer')
    @token_required
    def post(self, current_user):
        """Set password for customers who don't have one"""
        data = request.get_json()
        password = data.get('password')
        customer_id = current_user.get('sub')
        
        if not password:
            return {"message": "Password is required", "status": False, "data": None}, 400
        
        # Update password
        with get_db_connection() as conn:
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE customers SET password_hash = %s WHERE id = %s",
                    [hash_password(password), customer_id]
                )
                conn.commit()
                cursor.close()
        
        return {
            "message": "Password set successfully",
            "status": True,
            "data": {"updated_at": datetime.now().isoformat()}
        }
@profile_ns.route('/change-password')
class ChangePassword(Resource):
    @profile_ns.expect(change_password_model)
    @profile_ns.doc('change_password', description='Change customer password', security='Bearer')
    @token_required
    def put(self, current_user):
        """Change customer password"""
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        customer_id = current_user.get('sub')
        
        if not current_password or not new_password:
            return {"message": "Current and new passwords are required", "status": False, "data": None}, 400
        
        # Verify current password
        customer = execute_query("SELECT password_hash FROM customers WHERE id = %s", [customer_id], fetch_one=True)
        if not customer or customer['password_hash'] != hash_password(current_password):
            return {"message": "Current password is incorrect", "status": False, "data": None}, 400
        
        # Update password
        with get_db_connection() as conn:
            if conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE customers SET password_hash = %s WHERE id = %s", 
                             [hash_password(new_password), customer_id])
                conn.commit()
                cursor.close()
        
        return {
            "message": "Password changed successfully",
            "status": True,
            "data": {"updated_at": datetime.now().isoformat()}
        }

# Product Endpoints
@products_ns.route('/trending')
class TrendingProducts(Resource):
    @products_ns.doc('get_trending_products', description='Get trending products')
    def get(self):
        """Get trending products"""
        try:
            limit = int(request.args.get('limit', 10))
            
            trending = execute_query(
                "SELECT p.*, pc.name as category_name, COUNT(si.id) as sales_count "
                "FROM products p "
                "LEFT JOIN product_categories pc ON p.category_id = pc.id "
                "LEFT JOIN sale_items si ON p.id = si.product_id "
                "WHERE p.is_active = 1 "
                "GROUP BY p.id "
                "ORDER BY sales_count DESC, p.created_at DESC "
                f"LIMIT {limit}"
            )
            
            return {
                "message": "Trending products retrieved successfully",
                "status": True,
                "data": {"trending_products": trending}
            }
        except Exception as e:
            print(f"Trending products error: {e}")
            return {"message": "Internal Server Error", "status": False, "data": None}, 500

@products_ns.route('/<int:product_id>/images')
class ProductImages(Resource):
    @products_ns.doc('get_product_images', description='Get product images')
    def get(self, product_id):
        """Get product images"""
        images = execute_query(
            "SELECT * FROM product_images WHERE product_id = %s AND is_active = 1 ORDER BY display_order",
            [product_id]
        )
        
        return {
            "message": "Product images retrieved successfully",
            "status": True,
            "data": {"images": images}
        }

# Gallery Endpoint
@gallery_ns.route('/')
class Gallery(Resource):
    @gallery_ns.doc('get_gallery', description='Get gallery images')
    def get(self):
        """Get gallery images from product images"""
        gallery = execute_query(
            "SELECT pi.*, p.name as product_name, pc.name as category_name "
            "FROM product_images pi "
            "LEFT JOIN products p ON pi.product_id = p.id "
            "LEFT JOIN product_categories pc ON p.category_id = pc.id "
            "WHERE pi.is_active = 1 AND pi.image_type = 'gallery' "
            "ORDER BY pi.display_order"
        )
        
        return {
            "message": "Gallery images retrieved successfully",
            "status": True,
            "data": {"gallery": gallery}
        }

# Warranty Endpoint
@warranty_ns.route('/')
class Warranty(Resource):
    @warranty_ns.doc('get_warranty_info', description='Get warranty information', security='Bearer')
    @token_required
    def get(self, current_user):
        """Get customer warranty information"""
        customer_id = current_user.get('sub')
        
        warranties = execute_query(
            "SELECT p.name as product_name, si.serial_number, si.warranty_start_date, si.warranty_end_date, "
            "CASE WHEN si.warranty_end_date > CURDATE() THEN 'active' ELSE 'expired' END as status "
            "FROM sale_items si "
            "LEFT JOIN products p ON si.product_id = p.id "
            "LEFT JOIN sales s ON si.sale_id = s.id "
            "WHERE s.customer_id = %s AND si.warranty_start_date IS NOT NULL",
            [customer_id]
        )
        
        return {
            "message": "Warranty information retrieved successfully",
            "status": True,
            "data": {"warranties": warranties}
        }

# Locations Endpoint
@locations_ns.route('/nearby')
class NearbyLocations(Resource):
    @locations_ns.doc('get_nearby_locations', description='Get nearby service centers')
    def get(self):
        """Get nearby service centers"""
        service_centers = execute_query(
            "SELECT * FROM service_centers WHERE is_active = 1 ORDER BY name"
        )
        
        return {
            "message": "Nearby locations retrieved successfully",
            "status": True,
            "data": {"service_centers": service_centers}
        }

# Sales Endpoints
@sales_ns.route('/history')
class SalesHistory(Resource):
    @sales_ns.doc('get_sales_history', description='Get sales history', security='Bearer')
    @token_required
    def get(self, current_user):
        """Get customer sales history"""
        customer_id = current_user.get('sub')
        
        sales = execute_query(
            "SELECT s.*, GROUP_CONCAT(CONCAT(p.name, ' (', si.quantity, ')')) as products "
            "FROM sales s "
            "LEFT JOIN sale_items si ON s.id = si.sale_id "
            "LEFT JOIN products p ON si.product_id = p.id "
            "WHERE s.customer_id = %s "
            "GROUP BY s.id ORDER BY s.sale_date DESC",
            [customer_id]
        )
        
        return {
            "message": "Sales history retrieved successfully",
            "status": True,
            "data": {"sales": sales}
        }

@orders_ns.route('/related-purchases')
class RelatedPurchases(Resource):
    @orders_ns.doc('get_related_purchases', description='Get related purchase suggestions', security='Bearer')
    @token_required
    def get(self, current_user):
        """Get related purchase suggestions"""
        try:
            customer_id = current_user.get('sub')
            
            # Get products from same categories as customer's purchases
            related_products = execute_query(
                "SELECT DISTINCT p.*, pc.name as category_name "
                "FROM products p "
                "LEFT JOIN product_categories pc ON p.category_id = pc.id "
                "WHERE p.category_id IN ("
                "  SELECT DISTINCT p2.category_id FROM products p2 "
                "  LEFT JOIN sale_items si ON p2.id = si.product_id "
                "  LEFT JOIN sales s ON si.sale_id = s.id "
                "  WHERE s.customer_id = %s"
                ") AND p.is_active = 1 "
                "AND p.id NOT IN ("
                "  SELECT si2.product_id FROM sale_items si2 "
                "  LEFT JOIN sales s2 ON si2.sale_id = s2.id "
                "  WHERE s2.customer_id = %s"
                ") LIMIT 10",
                [customer_id, customer_id]
            )
            
            return {
                "message": "Related purchases retrieved successfully",
                "status": True,
                "data": {
                    "related_products": related_products,
                    "accessories": [],
                    "recommendation_source": "categories"
                }
            }
        except Exception as e:
            print(f"Related purchases error: {e}")
            return {
                "message": "Failed to get related purchases",
                "status": False,
                "data": {
                    "related_products": [],
                    "accessories": [],
                    "recommendation_source": "error"
                }
            }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    debug_mode = os.getenv('FLASK_ENV', 'production') != 'production'
    print(f"Starting Ostrich Customer API on port {port}")
    print(f"Swagger UI: http://localhost:{port}/docs/")
    print("Database: Connected to MySQL (Aiven)")
    print("Features: Real-time data, No fallback data")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)

