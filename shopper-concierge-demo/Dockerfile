FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements_api.txt .
RUN pip install --no-cache-dir -r requirements_api.txt

# Copy the API code
COPY middleware_api.py .

# Expose port 8080 (Cloud Run default)
EXPOSE 8080

# Run the application
CMD ["uvicorn", "middleware_api:app", "--host", "0.0.0.0", "--port", "8080"]
