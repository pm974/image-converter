#!/bin/bash

# Script to push changes to GitHub
# Usage: ./build-and-push-editme.sh [commit_message]
# Copy this file to build-and-push.sh and edit it to match your GitHub settings

# Default repository information
GIT_USERNAME="your-username"
GIT_REPO_NAME="your-repo-name"
GIT_BRANCH="main"  # or master, depending on your default branch

# If no commit message is provided, ask for one
if [ -z "$1" ]; then
    echo "Enter commit message:"
    read COMMIT_MESSAGE
else
    COMMIT_MESSAGE="$1"
fi

echo "=========================================="
echo "Pushing changes to GitHub"
echo "Repository: $GIT_USERNAME/$GIT_REPO_NAME"
echo "Branch: $GIT_BRANCH"
echo "Commit message: $COMMIT_MESSAGE"
echo "=========================================="

# Step 1: Add all files to Git
echo "🔍 Adding changes to Git..."
git add .

if [ $? -ne 0 ]; then
    echo "❌ Git add failed. Exiting."
    exit 1
fi

echo "✅ Git add successful"

# Step 2: Commit changes
echo "💾 Committing changes..."
git commit -m "$COMMIT_MESSAGE"

if [ $? -ne 0 ]; then
    echo "❌ Git commit failed. Exiting."
    exit 1
fi

echo "✅ Git commit successful"

# Step 3: Push to GitHub
echo "⬆️ Pushing changes to GitHub..."
git push origin $GIT_BRANCH

if [ $? -ne 0 ]; then
    echo "❌ Git push failed. If you haven't set up a remote yet, run: git remote add origin https://github.com/$GIT_USERNAME/$GIT_REPO_NAME.git"
    exit 1
fi

echo "✅ Git push successful"

echo "=========================================="
echo "Changes have been pushed to GitHub!"
echo "Visit https://github.com/$GIT_USERNAME/$GIT_REPO_NAME to view your repository"
echo "==========================================" 