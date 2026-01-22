# Customer Preferences API

## Overview
Fully functional preferences system for customer app with database persistence in Aiven MySQL.

## Database Table
**Table**: `customer_preferences`

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| id | INT | AUTO_INCREMENT | Primary key |
| customer_id | INT | NOT NULL | Foreign key to customers table |
| email_notifications | BOOLEAN | TRUE | Enable/disable email notifications |
| sms_notifications | BOOLEAN | TRUE | Enable/disable SMS notifications |
| push_notifications | BOOLEAN | TRUE | Enable/disable push notifications |
| location_sharing | BOOLEAN | FALSE | Enable/disable location sharing |
| created_at | TIMESTAMP | CURRENT_TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | CURRENT_TIMESTAMP | Last update time |

## API Endpoints

### 1. Get Preferences
**Endpoint**: `GET /api/v1/utilities/settings`  
**Authentication**: Required (Bearer token)

**Response**:
```json
{
  "message": "Preferences retrieved successfully",
  "status": true,
  "data": {
    "email_notifications": true,
    "sms_notifications": true,
    "push_notifications": true,
    "location_sharing": false
  }
}
```

### 2. Update Preferences
**Endpoint**: `PUT /api/v1/utilities/settings`  
**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "email_notifications": false,
  "sms_notifications": true,
  "push_notifications": true,
  "location_sharing": true
}
```

**Response**:
```json
{
  "message": "Preferences updated successfully",
  "status": true,
  "data": {
    "email_notifications": false,
    "sms_notifications": true,
    "push_notifications": true,
    "location_sharing": true,
    "updated_at": "2024-01-15T10:30:00"
  }
}
```

## Features
✅ Database persistence in Aiven MySQL
✅ Auto-initialization for new customers
✅ Individual preference toggles
✅ Swagger documentation at `/docs/`
✅ JWT authentication required
✅ Timestamps for audit trail

## Testing
Run the test script:
```bash
python test_preferences.py
```

## Migration
To create the table:
```bash
python create_preferences_table.py
```

## Preference Types

### Email Notifications
- Order confirmations
- Service updates
- Promotional emails
- Account notifications

### SMS Notifications
- Service appointment reminders
- Order status updates
- Critical alerts
- OTP messages

### Location Sharing
- Enable GPS tracking for service requests
- Find nearby service centers
- Delivery tracking
- Location-based offers


### Push Notifications
- Order status updates
- Service appointment reminders
- New product launches
- Special offers and promotions
- Real-time alerts
