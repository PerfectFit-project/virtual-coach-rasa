# Dockerfile for celery scheduler

FROM python:3.8

# Use subdirectory as working directory
WORKDIR /app

# Change to root user to install dependencies
USER root

# Install requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Don't use root user to run code
USER nobody

COPY . .

CMD ["celery", "--app=celery_tasks", "worker", "-B", "-l", \
     "INFO", "-s", "/tmp/celerybeat-schedule"]
