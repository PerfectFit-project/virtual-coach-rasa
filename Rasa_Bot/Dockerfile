# Dockerfile for rasa server

FROM python:3.8

# Heroku wants to provide a PORT env variable.
# This default is here for runs outside heroku
ENV PORT=5005

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

# Using shell form to enable usage of port
CMD rasa run --enable-api -p $PORT
