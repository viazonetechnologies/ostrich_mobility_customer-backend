# Ostrich Customer Backend API

Customer mobile app API for Ostrich Product & Service Management System.

## Features

- 42 REST API endpoints
- JWT authentication
- Aiven MySQL database integration
- Swagger documentation
- CORS enabled for mobile apps
- Fallback data for resilience

## Deployment on Render

1. **Environment Variables** (set in Render dashboard):
   ```
   DB_HOST=mysql-ostrich-tviazone-5922.i.aivencloud.com
   DB_USER=avnadmin
   DB_PASSWORD=your_aiven_password
   DB_NAME=defaultdb
   DB_PORT=16599
   SECRET_KEY=your_secret_key
   ```

2. **Deploy**: Connect GitHub repo to Render and deploy

## API Documentation

- Swagger UI: `/docs/`
- Health check: `/health`
- API endpoints: `/api/v1/`

## Local Development

```bash
pip install -r requirements.txt
python main.py
```

Visit `http://localhost:8001/docs/` for API documentation.