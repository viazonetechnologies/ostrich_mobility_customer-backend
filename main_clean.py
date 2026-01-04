from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restx import Api, Resource, fields
import os
import jwt
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
CORS(app)

# Swagger API setup
api = Api(app, 
    version='1.0', 
    title='Ostrich Customer API',
    description='Customer mobile app API for Ostrich Product & Service Management System',
    doc='/docs/'
)

# Namespaces
auth_ns = api.namespace('api/v1/auth', description='Authentication operations')
dashboard_ns = api.namespace('api/v1/dashboard', description='Dashboard operations')
products_ns = api.namespace('api/v1/products', description='Products operations')

# Configuration
SECRET_KEY = 'customer-secret-key'
app.config['SECRET_KEY'] = SECRET_KEY

# JWT utilities
def create_access_token(data):
    payload = data.copy()
    payload['exp'] = datetime.utcnow() + timedelta(hours=24)
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except:
        return None

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if token and token.startswith('Bearer '):
            token = token[7:]
            payload = verify_token(token)
            if payload:
                return f(current_user=payload, *args, **kwargs)
        return jsonify({'error': 'Token required'}), 401
    return decorated

# Models
otp_model = api.model('OTP', {
    'phone_number': fields.String(required=True, description='Phone number')
})

verify_otp_model = api.model('VerifyOTP', {
    'phone_number': fields.String(required=True, description='Phone number'),
    'otp': fields.String(required=True, description='OTP code')
})

# Basic routes
@app.route('/')
def read_root():
    return jsonify({
        "message": "Ostrich Customer Mobile API",
        "version": "1.0.0",
        "docs": "/docs/",
        "status": "running"
    })

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "ostrich-customer-api",
        "timestamp": datetime.now().isoformat()
    })

# Authentication endpoints
@auth_ns.route('/send-otp')
class SendOTP(Resource):
    @auth_ns.expect(otp_model)
    def post(self):
        """Send OTP to phone number"""
        data = request.get_json()
        phone_number = data.get('phone_number')
        return {
            "message": "OTP sent successfully",
            "phone_number": phone_number,
            "expires_in_minutes": 5,
            "otp": "123456"
        }

@auth_ns.route('/verify-otp')
class VerifyOTP(Resource):
    @auth_ns.expect(verify_otp_model)
    def post(self):
        """Verify OTP and authenticate"""
        data = request.get_json()
        phone_number = data.get('phone_number')
        otp = data.get('otp')
        
        if otp == "123456":
            access_token = create_access_token({"sub": "1", "phone": phone_number})
            return {
                "access_token": access_token,
                "customer_id": 1,
                "is_new_customer": False,
                "phone_number": phone_number,
                "profile_complete": True
            }
        return {"detail": "Invalid OTP"}, 400

@dashboard_ns.route('/')
class Dashboard(Resource):
    @dashboard_ns.doc('get_dashboard')
    @token_required
    def get(self, current_user):
        """Get customer dashboard"""
        return {
            "customer_info": {
                "name": "John Customer",
                "phone": current_user.get('phone', '9876543210'),
                "customer_id": current_user.get('sub', '1')
            },
            "stats": {
                "total_products": 2,
                "active_services": 1,
                "completed_services": 1,
                "warranty_products": 2
            },
            "recent_services": [
                {"id": 1, "ticket_number": "TKT000001", "status": "IN_PROGRESS", "priority": "HIGH"}
            ],
            "notifications": {
                "unread_count": 2,
                "latest": [
                    {"id": 1, "title": "Service Scheduled", "message": "Your motor service is scheduled"}
                ]
            }
        }

@products_ns.route('/')
class Products(Resource):
    @products_ns.doc('get_products')
    @token_required
    def get(self, current_user):
        """Get customer products"""
        return {
            "products": [
                {"id": 1, "name": "3HP Motor", "model": "OST-3HP-SP", "status": "active"},
                {"id": 2, "name": "5HP Pump", "model": "OST-5HP-MP", "status": "active"}
            ],
            "total_count": 2
        }

# Additional Flask routes
@app.route('/api/v1/catalog/products')
def get_product_catalog():
    return jsonify({
        "products": [
            {"id": 1, "name": "3HP Motor", "price": 15000, "category": "Motors"},
            {"id": 2, "name": "5HP Pump", "price": 25000, "category": "Pumps"}
        ]
    })

@app.route('/api/v1/services/', methods=['GET'])
@token_required
def get_services(current_user):
    return jsonify({
        "services": [
            {"id": 1, "ticket_number": "TKT000001", "status": "IN_PROGRESS", "priority": "HIGH"}
        ],
        "total_count": 1
    })

@app.route('/api/v1/orders/', methods=['GET'])
@token_required
def get_orders(current_user):
    return jsonify({
        "orders": [
            {"id": 1, "order_number": "ORD000001", "status": "delivered", "total_amount": 25000}
        ],
        "total_count": 1
    })

@app.route('/api/v1/notifications/', methods=['GET'])
@token_required
def get_notifications(current_user):
    return jsonify([
        {"id": 1, "title": "Service Scheduled", "message": "Your service is scheduled", "is_read": False}
    ])

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    app.run(host="0.0.0.0", port=port, debug=True)