# Dockerfile for rasa actions server

# Pull SDK image as base image
FROM rasa/rasa-sdk:2.0.0

# Use subdirectory as working directory
WORKDIR /app

# Copy actions requirements
COPY ./requirements.txt ./

# Change to root user to install dependencies
USER root

RUN apt-get update && \
    apt-get install -y git

# Install extra requirements for actions code
RUN pip install -r requirements.txt

# Copy actions code to working directory
COPY . /app/actions

# Don't use root user to run code
USER 1001