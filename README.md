# Ostrich Customer Mobile API

Complete Flask backend for Ostrich Customer Mobile App with 35+ endpoints.

## Features
- JWT + OTP Authentication
- Customer Dashboard
- Product Management
- Service Requests
- Order History
- Notifications
- Support System
- Swagger Documentation

## Quick Start
```bash
pip install -r requirements.txt
python main.py
```

## API Documentation
- Swagger: http://localhost:8001/docs/
- Health: http://localhost:8001/health

## Test Credentials
- OTP: 123456
- Demo Login: demo/password

## Endpoints
- Authentication: /api/v1/auth/*
- Dashboard: /api/v1/dashboard/
- Products: /api/v1/products/
- Services: /api/v1/services/
- Orders: /api/v1/orders/
- Notifications: /api/v1/notifications/
- Profile: /api/v1/profile/
- Catalog: /api/v1/catalog/products
- Support: /api/v1/support/*