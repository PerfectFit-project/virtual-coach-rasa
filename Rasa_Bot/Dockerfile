# Dockerfile for rasa server

FROM python:3.8

# Change to root user to install dependencies
USER root

RUN python -m pip install --upgrade pip==20.2

# Install requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Use subdirectory as working directory
WORKDIR /app

COPY . /app

RUN chmod -R 777 /app

# Don't use root user to run code
USER 1001

CMD ["rasa", "run", "--enable-api"]
