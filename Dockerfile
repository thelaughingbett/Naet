FROM python:3.12.4-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/Naet

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt /usr/src/Naet/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . /usr/src/Naet

