# Dockerfile for rasa actions server

# Pull SDK image as base image, version must be compatble with Rasa version
FROM rasa/rasa-sdk:3.0.4

# Use subdirectory as working directory
WORKDIR /app

# Copy actions requirements
COPY requirements-actions.txt ./

# Change to root user to install dependencies
USER root

RUN apt-get update && \
    apt-get install -y git
RUN apt-get install -y python3
RUN apt-get install -y python3-pip
RUN apt-get install -y libpq-dev
RUN apt-get install -y build-essential

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install wheel

# Install extra requirements for actions code
RUN pip install -r requirements-actions.txt

# Copy actions code to working directory
COPY . /app/actions

# Don't use root user to run code
USER 1001