#!/usr/bin/env python3
"""
Simple script to automate git add, commit, and push operations.
Uses the @uv runner for Python script execution.
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
    # Check if we're in a git repository
    if not os.path.exists('.git'):
        print("Error: Not in a git repository. Please run this script from the root of your git repository.")
        sys.exit(1)
    
    # Ask for commit message
    print("\n=== GitHub Push Helper ===")
    commit_description = input("Enter a description of your changes: ")
    
    if not commit_description:
        print("Error: Commit description cannot be empty.")
        sys.exit(1)
    
    # Run git add
    print("\nAdding all changes...")
    if not run_command("git add ."):
        sys.exit(1)
    
    # Run git commit
    print("\nCommitting changes...")
    if not run_command(f'git commit -m "{commit_description}"'):
        sys.exit(1)
    
    # Run git push
    print("\nPushing to GitHub...")
    if not run_command("git push origin main"):
        sys.exit(1)
    
    print("\n✅ Success! Your changes have been pushed to GitHub.")

if __name__ == "__main__":
    main() 