#!/bin/bash

# Generic server setup script for Image Converter
# Copy this file to setup_server.sh and customize for your environment

# Set terminal colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# CUSTOMIZE THESE VARIABLES
DATA_ROOT="/path/to/your/data"  # Root directory for all data
APP_PORT="12346"                # Port to expose the application
EXTERNAL_URL="https://your-domain.com"  # Public URL for the application
DOCKER_IMAGE="image-convert:latest"  # Docker image to use

# Check if script is run as root or with sudo
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root or with sudo${NC}"
  exit 1
fi

echo -e "${YELLOW}==== IMAGE CONVERTER SERVER SETUP AND RESET ====${NC}"

# Create data directories with proper permissions
echo -e "${YELLOW}Creating data directories...${NC}"
mkdir -p ${DATA_ROOT}/image_uploads
mkdir -p ${DATA_ROOT}/image_outputs
mkdir -p ${DATA_ROOT}/image_data

# Set permissions
echo -e "${YELLOW}Setting permissions...${NC}"
chmod -R 777 ${DATA_ROOT}/image_uploads
chmod -R 777 ${DATA_ROOT}/image_outputs
chmod -R 777 ${DATA_ROOT}/image_data

# Pull latest image
echo -e "${YELLOW}Pulling latest Docker image...${NC}"
docker pull ${DOCKER_IMAGE}

# Stop and remove existing container
echo -e "${YELLOW}Stopping existing container...${NC}"
docker stop image-convert || true
echo -e "${YELLOW}Removing container...${NC}"
docker rm image-convert || true

# Check if docker-compose.yml exists
COMPOSE_FILE="${DATA_ROOT}/docker-compose.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
  echo -e "${YELLOW}Creating docker-compose.yml file...${NC}"
  cat > "$COMPOSE_FILE" << EOF
services:
  image-convert:
    image: ${DOCKER_IMAGE}
    container_name: image-convert
    pull_policy: always
    ports:
      - "${APP_PORT}:5000"
    volumes:
      - ${DATA_ROOT}/image_uploads:/app/uploads
      - ${DATA_ROOT}/image_outputs:/app/outputs
      - ${DATA_ROOT}/image_data:/app/data
    restart: unless-stopped
    environment:
      - EXTERNAL_URL=${EXTERNAL_URL}
      - OUTPUT_DIR=/app/outputs
      - SESSION_FILE=/app/data/sessions.json
EOF
  echo -e "${GREEN}Created docker-compose.yml${NC}"
fi

# Start the container with docker-compose
echo -e "${YELLOW}Starting container with docker-compose...${NC}"
cd ${DATA_ROOT} && docker-compose up -d

# Wait for container to start
echo -e "${YELLOW}Waiting for container to start (10 seconds)...${NC}"
sleep 10

# Check logs
echo -e "${YELLOW}Container logs:${NC}"
docker logs image-convert

echo -e "${GREEN}==== SETUP COMPLETE ====${NC}"
echo -e "The application should be accessible at: ${EXTERNAL_URL}"
echo -e "If you encounter issues, check the logs with: docker logs image-convert" 