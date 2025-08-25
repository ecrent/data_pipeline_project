FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code (current structure has files in root)
COPY kafka_producer.py .

# Create data directory for mounting
RUN mkdir -p /app/data

# Set Python path
ENV PYTHONPATH=/app

# Default command
CMD ["python", "kafka_producer.py"]
