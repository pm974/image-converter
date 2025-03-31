#!/bin/bash

# Set terminal colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting Image Converter...${NC}"

# Check if docker-compose exists
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if the container is already running
if docker ps | grep -q "image-convert"; then
    echo -e "${GREEN}Image Converter is already running!${NC}"
    echo -e "Access the application at: ${GREEN}http://localhost:12346${NC}"
    exit 0
fi

# Start the container with docker-compose
echo -e "${YELLOW}Starting container with docker-compose...${NC}"
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