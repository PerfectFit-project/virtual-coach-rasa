# Dockerfile for rasa actions server

# Pull SDK image as base image, version must be compatble with Rasa version
FROM rasa/rasa-sdk:2.8.1

# Use subdirectory as working directory
WORKDIR /app

# Copy actions requirements
COPY actions/requirements-actions.txt ./

# Change to root user to install dependencies
USER root

RUN apt-get update && \
    apt-get install -y git

# Install extra requirements for actions code
RUN pip install -r requirements-actions.txt

# Copy actions code to working directory
COPY ./actions /app/actions

# Don't use root user to run code
USER 1001