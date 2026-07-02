FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    gdal-bin libgdal-dev libgeos-dev libproj-dev \
    && rm -rf /var/lib/apt/lists/*

ARG REQUIREMENTS_FILE=production.txt
COPY requirements/ /tmp/requirements/
RUN pip install --upgrade pip && pip install -r /tmp/requirements/${REQUIREMENTS_FILE}

COPY . .

RUN mkdir -p /app/media/reports /app/staticfiles

EXPOSE 8000
