FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt /usr/src/Naet/
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /usr/src/Naet
WORKDIR /usr/src/Naet

# Copy the rest of the project
COPY . /usr/src/Naet

RUN python manage.py collectstatic --noinput

# Inform Docker that the container listens on port 8000
EXPOSE 8000

# Run Gunicorn to serve the Django WSGI application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "Naet.wsgi:application"]
