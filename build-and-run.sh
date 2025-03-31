#!/bin/bash

# Set terminal colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}===========================================${NC}"
echo -e "${YELLOW}Building and running Image Converter locally${NC}"
echo -e "${YELLOW}===========================================${NC}"

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check for Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

# Create necessary directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p uploads outputs data
chmod 777 uploads outputs data

# Build the Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t image-convert:latest .

if [ $? -ne 0 ]; then
    echo -e "${RED}Docker build failed. Please check the errors above.${NC}"
    exit 1
fi

echo -e "${GREEN}Docker image built successfully!${NC}"

# Run the container with Docker Compose
echo -e "${YELLOW}Starting container with Docker Compose...${NC}"
docker-compose up -d

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to start container. Please check the errors above.${NC}"
    exit 1
fi

echo -e "${GREEN}Image Converter is now running!${NC}"
echo -e "Access the application at: ${GREEN}http://localhost:12346${NC}"
echo -e ""
echo -e "To view logs: ${YELLOW}docker logs image-convert${NC}"
echo -e "To stop the container: ${YELLOW}docker-compose down${NC}" 