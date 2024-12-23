FROM python:3.9-slim

# Declare environment variables
ARG DJANGO_SECRET_KEY
ARG DJANGO_DEBUG
ARG DJANGO_ALLOWED_HOSTS
ARG REDIS_URL_DEV
ARG REDIS_URL_PROD
ARG DB_ENGINE
ARG DB_NAME
ARG DB_USER
ARG DB_PASSWORD
ARG DB_HOST
ARG DB_PORT
ARG GRADER_WORKERS
ARG TIME_ZONE

# Set as environment variables
ENV DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY
ENV DJANGO_DEBUG=$DJANGO_DEBUG
ENV DJANGO_ALLOWED_HOSTS=$DJANGO_ALLOWED_HOSTS
ENV REDIS_URL_DEV=$REDIS_URL_DEV
ENV REDIS_URL_PROD=$REDIS_URL_PROD
ENV DB_ENGINE=$DB_ENGINE
ENV DB_NAME=$DB_NAME
ENV DB_USER=$DB_USER
ENV DB_PASSWORD=$DB_PASSWORD
ENV DB_HOST=$DB_HOST
ENV DB_PORT=$DB_PORT
ENV GRADER_WORKERS=$GRADER_WORKERS
ENV TIME_ZONE=$TIME_ZONE

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    openjdk-11-jdk \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy project files
COPY . .

# Script untuk menjalankan web dan worker
COPY start.sh .
RUN chmod +x start.sh

# Expose port yang digunakan Railway
EXPOSE $PORT

# Gunakan start.sh sebagai entrypoint
CMD ["./start.sh"]