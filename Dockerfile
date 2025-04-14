FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for OpenCV and MediaPipe
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    python3-dev \
    build-essential \
    libcairo2-dev \
    pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements_cloud.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create audio directory
RUN mkdir -p audio

# Expose the port the app runs on
EXPOSE 8080

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Use Gunicorn as production web server
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app