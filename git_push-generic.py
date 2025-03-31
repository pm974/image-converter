#!/usr/bin/env python3
# @uv
"""
Generic script to automate git add, commit, and push operations.
Uses the @uv runner for Python script execution.

To use this file:
1. Copy this file to git_push.py
2. Make sure it's executable: chmod +x git_push.py
3. Run with: ./git_push.py or uv run git_push.py

This script is intended as a template. You may want to customize:
- The branch name ('main' is used by default)
- The remote name ('origin' is used by default)
- Add other git operations like pulling before pushing
"""

import subprocess
import sys
import os

def run_command(command):
    """Run a shell command and print output"""
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(f"Error message: {e.stderr}")
        return False

def main():
    # Configuration - customize these values if needed
    GIT_BRANCH = "main"
    GIT_REMOTE = "origin"
    
    # Check if we're in a git repository
    if not os.path.exists('.git'):
        print("Error: Not in a git repository. Please run this script from the root of your git repository.")
        sys.exit(1)
    
    # Ask for commit message
    print("\n=== GitHub Push Helper ===")
    print("This script will add, commit, and push all changes to GitHub.")
    commit_description = input("Enter a description of your changes: ")
    
    if not commit_description:
        print("Error: Commit description cannot be empty.")
        sys.exit(1)
    
    # Show what will be committed
    print("\nFiles to be committed:")
    run_command("git status --short")
    
    # Confirm changes
    confirm = input("\nProceed with these changes? (y/n): ")
    if confirm.lower() not in ['y', 'yes']:
        print("Operation canceled.")
        sys.exit(0)
    
    # Run git add
    print("\nAdding all changes...")
    if not run_command("git add ."):
        sys.exit(1)
    
    # Run git commit
    print("\nCommitting changes...")
    if not run_command(f'git commit -m "{commit_description}"'):
        sys.exit(1)
    
    # Run git push
    print(f"\nPushing to GitHub ({GIT_REMOTE}/{GIT_BRANCH})...")
    if not run_command(f"git push {GIT_REMOTE} {GIT_BRANCH}"):
        sys.exit(1)
    
    print("\n✅ Success! Your changes have been pushed to GitHub.")

if __name__ == "__main__":
    main() 