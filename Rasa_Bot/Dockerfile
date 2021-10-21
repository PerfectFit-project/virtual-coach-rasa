# Dockerfile for rasa server

FROM python:3.8

# Change to root user to install dependencies
USER root

# Install requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Don't use root user to run code
USER 1001

# Use subdirectory as working directory
WORKDIR /app

COPY . /app

ENTRYPOINT ["rasa", "run", "--enable-api"]
