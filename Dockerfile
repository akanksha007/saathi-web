FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all code
COPY . .

# Set working directory to backend
WORKDIR /app/backend

# Expose port
EXPOSE 8000

# Start server
CMD python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
