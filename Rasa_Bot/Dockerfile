# Dockerfile for rasa server

FROM python:3.8

# Change to root user to install dependencies
USER root

RUN python -m pip install --upgrade pip==20.2
RUN python -m pip install --upgrade sanic==21.9.3

# Install requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Spacy language model
RUN python -m spacy download nl_core_news_sm
RUN python -m spacy link nl_core_news_sm nl

# Don't use root user to run code
USER 1001

# Use subdirectory as working directory
WORKDIR /app

COPY . /app

ENTRYPOINT ["rasa", "run", "--enable-api"]
