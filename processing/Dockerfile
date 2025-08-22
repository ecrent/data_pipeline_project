FROM bitnami/spark:3.4.1

# Switch to root to install dependencies
USER root

# Install Python packages
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy source code
COPY src/ /app/src/

# Create logs directory
RUN mkdir -p /app/logs

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3

# Switch back to spark user
USER 1001

# Default command
CMD ["python", "src/data_processor.py"]
