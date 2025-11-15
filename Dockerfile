# Lightweight image with Tesseract and Python runtime
FROM python:3.11-slim

# Install tesseract and dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      tesseract-ocr \
      libtesseract-dev \
      imagemagick \
      build-essential \
      && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . /app

# Expose nothing by default — CLI tool
ENTRYPOINT ["bash", "-c"]