FROM bitnami/spark:3.4.1

# Switch to root to install dependencies
USER root

# Install Python packages
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy source code (current structure has files in root)
COPY data_processor.py /app/

# Create logs directory and set permissions
RUN mkdir -p /app/logs && chown -R 1001:1001 /app

# Create cache directory with proper permissions (Bitnami Spark runs as user 1001)
RUN mkdir -p /opt/bitnami/spark/.ivy2/cache /opt/bitnami/spark/.ivy2/jars && \
    chown -R 1001:1001 /opt/bitnami/spark/.ivy2 && \
    chmod -R 755 /opt/bitnami/spark/.ivy2

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app:/opt/bitnami/spark/python:/opt/bitnami/spark/python/lib/py4j-0.10.9.7-src.zip
ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3

# Switch back to spark user
USER 1001

# Default command
CMD ["python", "data_processor.py"]
