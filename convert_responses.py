import re

# Read the file
with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all standard_response calls with direct format
# Pattern to match standard_response calls
pattern = r'return standard_response\(\s*"([^"]+)",\s*(True|False)(?:,\s*(\{[^}]*\}|\{[^}]*\{[^}]*\}[^}]*\}|None))?\s*\)'

def replace_standard_response(match):
    message = match.group(1)
    status = match.group(2)
    data = match.group(3) if match.group(3) else 'None'
    
    if data == 'None':
        data = 'null'
    
    return f'''return {{
        "message": "{message}",
        "status": {status.lower()},
        "data": {data}
    }}'''

# Apply the replacement
content = re.sub(pattern, replace_standard_response, content, flags=re.DOTALL)

# Handle multi-line standard_response calls
multiline_pattern = r'return standard_response\(\s*"([^"]+)",\s*(True|False),\s*(\{[^}]*(?:\{[^}]*\}[^}]*)*\})\s*\)'

content = re.sub(multiline_pattern, replace_standard_response, content, flags=re.DOTALL | re.MULTILINE)

# Write back
with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Converted all standard_response calls to direct format")