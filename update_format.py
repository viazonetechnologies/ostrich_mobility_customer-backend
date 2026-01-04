import re

# Read the file
with open('main.py', 'r') as f:
    content = f.read()

# Update all remaining endpoints to use standard_response format
updates = [
    # Services endpoints
    (r'return \{\s*"services": services,\s*"total_count": len\(services\)\s*\}', 
     'return standard_response("Services retrieved successfully", True, {"services": services, "total_count": len(services)})'),
    
    # Service request
    (r'return \{\s*"message": "Service request submitted successfully",\s*"ticket_number": "TKT000003",\s*"service_id": 3,\s*"status": "SCHEDULED",\s*"priority": data\.get\(\'priority\', \'MEDIUM\'\)\s*\}',
     'return standard_response("Service request submitted successfully", True, {"ticket_number": "TKT000003", "service_id": 3, "status": "SCHEDULED", "priority": data.get(\'priority\', \'MEDIUM\')})'),
    
    # Orders
    (r'return \{\s*"orders": orders,\s*"total_count": len\(orders\)\s*\}',
     'return standard_response("Orders retrieved successfully", True, {"orders": orders, "total_count": len(orders)})'),
    
    # Profile
    (r'return \{\s*"id": 1,\s*"name": "John Customer",\s*"phone": current_user\.get\(\'phone\', \'9876543210\'\),\s*"email": "john@example\.com"\s*\}',
     'return standard_response("Profile retrieved successfully", True, {"id": 1, "name": "John Customer", "phone": current_user.get(\'phone\', \'9876543210\'), "email": "john@example.com"})'),
    
    # All other simple returns
    (r'return \{([^}]+)\}(?!\s*,\s*\d+)', r'return standard_response("Operation successful", True, {\1})'),
]

for pattern, replacement in updates:
    content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)

# Write back
with open('main.py', 'w') as f:
    f.write(content)

print("Updated all endpoints to standard format")