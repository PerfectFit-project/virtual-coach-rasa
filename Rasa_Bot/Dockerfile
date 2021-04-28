# Pull SDK image as base image
FROM rasa/rasa-sdk:2.0.0

# Use subdirectory as working directory
WORKDIR /app

# Copy actions requirements
# COPY actions/requirements-actions.txt ./

# Change to root user to install dependencies
USER root

# Install extra requirements for actions code
# RUN pip install -r requirements-actions.txt

# Copy actions code to working directory
COPY ./actions /app/actions

# Don't use root user to run code
USER 1001