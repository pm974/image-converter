#!/bin/bash

# Script to build Image Converter for x86 and push to Docker Hub
# Usage: ./build-and-push.sh [repository_name]

# Default repository name
REPO_NAME="cobaltfilms/image-convert"

# Check if repository name was provided as an argument
if [ -n "$1" ]; then
    REPO_NAME="$1"
fi

echo "=========================================="
echo "Building and pushing Image Converter to Docker Hub"
echo "Repository: $REPO_NAME"
echo "=========================================="

# Step 1: Build the Docker image for x86_64 architecture
echo "🔨 Building Docker image for x86_64..."
docker build --platform linux/amd64 -t "$REPO_NAME:latest" .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed. Exiting."
    exit 1
fi

echo "✅ Docker build successful"

# Step 2: Tag the image with x86 tag
echo "🏷️ Tagging image with x86 tag..."
docker tag "$REPO_NAME:latest" "$REPO_NAME:x86"

echo "✅ Image tagged successfully"

# Step 3: Push to Docker Hub
echo "⬆️ Pushing latest tag to Docker Hub..."
docker push "$REPO_NAME:latest"

if [ $? -ne 0 ]; then
    echo "❌ Failed to push latest tag. If you're not logged in, run 'docker login' first."
    exit 1
fi

echo "⬆️ Pushing x86 tag to Docker Hub..."
docker push "$REPO_NAME:x86"

if [ $? -ne 0 ]; then
    echo "❌ Failed to push x86 tag."
    exit 1
fi

echo "✅ All images pushed successfully"

echo "=========================================="
echo "Image Converter is now available on Docker Hub:"
echo "docker pull $REPO_NAME:latest"
echo "docker pull $REPO_NAME:x86"
echo "==========================================" 