# Fix all remaining endpoints to use standard_response format

# Read current file
with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all remaining non-standard responses
replacements = [
    # Enquiries
    ('return {\n            "message": "Enquiry submitted successfully",\n            "enquiry_id": "ENQ000001",\n            "status": "pending",\n            "estimated_response_time": "24 hours"\n        }',
     'return standard_response(\n            "Enquiry submitted successfully",\n            True,\n            {\n                "enquiry_id": "ENQ000001",\n                "status": "pending",\n                "estimated_response_time": "24 hours"\n            }\n        )'),
    
    ('return {\n            "enquiries": [\n                {\n                    "id": 1,\n                    "enquiry_number": "ENQ000001",\n                    "subject": "Product Information",\n                    "status": "responded",\n                    "created_date": (datetime.now() - timedelta(days=2)).strftime(\'%Y-%m-%d\'),\n                    "response_date": (datetime.now() - timedelta(days=1)).strftime(\'%Y-%m-%d\')\n                }\n            ]\n        }',
     'return standard_response(\n            "Enquiries retrieved successfully",\n            True,\n            {\n                "enquiries": [\n                    {\n                        "id": 1,\n                        "enquiry_number": "ENQ000001",\n                        "subject": "Product Information",\n                        "status": "responded",\n                        "created_date": (datetime.now() - timedelta(days=2)).strftime(\'%Y-%m-%d\'),\n                        "response_date": (datetime.now() - timedelta(days=1)).strftime(\'%Y-%m-%d\')\n                    }\n                ]\n            }\n        )'),
    
    # Support
    ('return {\n            "ticket_id": "SUP000001",\n            "message": "Support ticket created successfully",\n            "status": "open"\n        }',
     'return standard_response(\n            "Support ticket created successfully",\n            True,\n            {\n                "ticket_id": "SUP000001",\n                "status": "open"\n            }\n        )'),
    
    ('return {\n            "faqs": [\n                {"question": "How to request service?", "answer": "Use the service request feature in the app"}\n            ]\n        }',
     'return standard_response(\n            "FAQ retrieved successfully",\n            True,\n            {\n                "faqs": [\n                    {"question": "How to request service?", "answer": "Use the service request feature in the app"}\n                ]\n            }\n        )'),
    
    ('return {\n            "phone": "1800-123-4567",\n            "email": "support@ostrich.com",\n            "hours": "9 AM - 6 PM"\n        }',
     'return standard_response(\n            "Contact information retrieved successfully",\n            True,\n            {\n                "phone": "1800-123-4567",\n                "email": "support@ostrich.com",\n                "hours": "9 AM - 6 PM"\n            }\n        )'),
    
    # Utilities
    ('return {"message": "WhatsApp message sent"}',
     'return standard_response("WhatsApp message sent", True)'),
    
    ('return {"message": "File uploaded successfully", "url": "https://example.com/file.jpg"}',
     'return standard_response(\n            "File uploaded successfully",\n            True,\n            {\n                "url": "https://example.com/file.jpg"\n            }\n        )'),
    
    ('return {\n            "notifications": True,\n            "sms_alerts": True,\n            "email_updates": True\n        }',
     'return standard_response(\n            "Settings retrieved successfully",\n            True,\n            {\n                "notifications": True,\n                "sms_alerts": True,\n                "email_updates": True\n            }\n        )'),
    
    # Catalog
    ('return {"products": catalog_products}',
     'return standard_response(\n            "Product catalog retrieved successfully",\n            True,\n            {\n                "products": catalog_products\n            }\n        )'),
    
    ('return {"categories": categories}',
     'return standard_response(\n            "Categories retrieved successfully",\n            True,\n            {\n                "categories": categories\n            }\n        )'),
]

# Apply all replacements
for old, new in replacements:
    content = content.replace(old, new)

# Write back
with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed all remaining endpoints to use standard_response format")