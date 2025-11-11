FROM python:3.11-slim

WORKDIR /app

# Install system dependencies with retry mechanism and better error handling
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8002

# Run the application
CMD ["python", "src/main.py"]