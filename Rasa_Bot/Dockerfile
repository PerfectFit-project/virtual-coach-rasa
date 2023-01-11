# Dockerfile for rasa server

FROM python:3.8

ENV MAX_NUMBER_OF_PREDICTIONS=30

RUN python -m pip install --upgrade pip==20.2

# Install requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Use subdirectory as working directory
WORKDIR /app

COPY . /app

RUN chmod -R 777 /app

CMD ["rasa", "run", "--enable-api",]
