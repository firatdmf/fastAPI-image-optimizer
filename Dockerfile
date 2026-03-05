# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install system dependencies for AVIF and image processing
RUN apt-get update && apt-get install -y \
    libavif-dev \
    libheif-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set permissions for the Hugging Face user (User ID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Command to run the app (Hugging Face expects port 7860)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]