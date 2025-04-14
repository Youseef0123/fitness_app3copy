FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for OpenCV, MediaPipe, and audio
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    python3-dev \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file for Cloud Run environment
COPY requirements_cloud.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all app files into the container
COPY . /app

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Create directory for audio files (if needed by your application)
RUN mkdir -p /app/audio

# Expose the port for the application
EXPOSE 8080

# Use Gunicorn to run the app
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 rtc_video_server:app
