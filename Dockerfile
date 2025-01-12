FROM python:3.11-slim

# Install Chrome and dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    xvfb \
    unzip \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Set Chrome binary path environment variable
ENV CHROME_BINARY_PATH=/usr/bin/chromium

# Set display for xvfb
ENV DISPLAY=:99

# Start script
CMD ["python", "run.py"]