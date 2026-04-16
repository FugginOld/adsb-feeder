# syntax=docker/dockerfile:1

# Multi-stage build for different Linux bases
ARG BASE_IMAGE=debian:stable-slim
FROM ${BASE_IMAGE} as base

LABEL maintainer="FugginOld <dockerhub@fugginold.com>"
LABEL org.opencontainers.image.source="https://github.com/FugginOld/adsb-feeder"

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies (example for Debian/Ubuntu)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        python3 \
        python3-pip \
        python3-venv \
        socat \
        rtl-sdr \
        gnupg \
        docker-compose \
        # Add other dependencies as needed \
    && rm -rf /var/lib/apt/lists/*

# Copy application code and configs
COPY src/modules/adsb-feeder/filesystem/root/opt/adsb /opt/adsb
WORKDIR /opt/adsb

# Install Python requirements if present
RUN if [ -f requirements.txt ]; then pip3 install -r requirements.txt; fi

# Expose common ports (adjust as needed)
EXPOSE 8080 30001 30002 30003 32006 30004 30104 30005 30006 30047 30152 31003 31004 31005 31006

# Entrypoint: run the full stack using docker-compose
CMD ["docker-compose", "-f", "docker-compose.yml", "up"]
