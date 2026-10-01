FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

WORKDIR /usr/src/Naet

# Install Python requirements first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Dummy values so collectstatic doesn't need real secrets at build time
RUN SECRET_KEY=build-only-dummy python manage.py collectstatic --noinput

EXPOSE 10000

# Shell form so $PORT is expanded; Render sets PORT at runtime
CMD gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 2 --timeout 120 Naet.wsgi:application