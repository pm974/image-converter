#!/bin/bash

# Generic setup script for Image Converter server
# This script helps set up and reset the Image Converter server environment
# Usage: ./setup_server-generic.sh

# Note: This is a template file. Copy to setup_server.sh and customize for your environment.
# The setup_server.sh file is gitignored to prevent committing your specific configuration.

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - Edit these variables in your setup_server.sh
# Data directories
DATA_DIR="./data"
UPLOAD_DIR="./uploads"
OUTPUT_DIR="./outputs"

# Docker settings
DOCKER_IMAGE="your-docker-image:latest"
CONTAINER_NAME="image-converter"
PORT="12346"

# Server URL - change to your actual server URL if needed
EXTERNAL_URL="http://localhost:${PORT}"

echo -e "${YELLOW}==== IMAGE CONVERTER SERVER SETUP AND RESET ====${NC}"
echo

# Create directories if they don't exist
echo -e "${BLUE}Creating directories...${NC}"
mkdir -p "$DATA_DIR"
mkdir -p "$UPLOAD_DIR"
mkdir -p "$OUTPUT_DIR"

# Set permissions
echo -e "${BLUE}Setting permissions...${NC}"
chmod -R 755 "$DATA_DIR"
chmod -R 755 "$UPLOAD_DIR"
chmod -R 755 "$OUTPUT_DIR"

# Stop and remove any existing container
echo -e "${BLUE}Stopping and removing existing container...${NC}"
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

# Pull the latest image
echo -e "${BLUE}Pulling latest Docker image...${NC}"
docker pull "$DOCKER_IMAGE"

# Start the container with the mounted volumes
echo -e "${BLUE}Starting container...${NC}"
docker run -d \
  --name "$CONTAINER_NAME" \
  -p "$PORT:5000" \
  -v "$(pwd)/$DATA_DIR:/app/data" \
  -v "$(pwd)/$UPLOAD_DIR:/app/uploads" \
  -v "$(pwd)/$OUTPUT_DIR:/app/outputs" \
  -e "UPLOAD_DIR=/app/uploads" \
  -e "OUTPUT_DIR=/app/outputs" \
  -e "SESSION_FILE=/app/data/sessions.json" \
  -e "EXTERNAL_URL=$EXTERNAL_URL" \
  "$DOCKER_IMAGE"

# Check if container is running
if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    echo -e "${GREEN}✅ Setup complete! The Image Converter server is now running.${NC}"
    echo -e "${GREEN}Access the application at: $EXTERNAL_URL${NC}"
else
    echo -e "${RED}❌ Container failed to start. Check Docker logs for more information.${NC}"
    echo -e "${YELLOW}Docker logs:${NC}"
    docker logs "$CONTAINER_NAME"
    exit 1
fi

echo
echo -e "${BLUE}Container details:${NC}"
docker ps -f name="$CONTAINER_NAME"
echo
echo -e "${YELLOW}To stop the server:${NC} docker stop $CONTAINER_NAME"
echo -e "${YELLOW}To view logs:${NC} docker logs $CONTAINER_NAME" 