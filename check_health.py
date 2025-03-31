#!/usr/bin/env python3
import os
import json
import time
import argparse
from datetime import datetime

def print_status(message, success=True):
    """Print a status message with color."""
    if success:
        print(f"\033[92m✓ {message}\033[0m")  # Green
    else:
        print(f"\033[91m✗ {message}\033[0m")  # Red

def format_time(timestamp):
    """Format a timestamp into a readable datetime."""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def check_expiration(timestamp, expiration_time):
    """Check if a timestamp is expired based on expiration time."""
    current_time = time.time()
    remaining = timestamp + expiration_time - current_time
    if remaining <= 0:
        return f"EXPIRED ({abs(int(remaining/60))} minutes ago)"
    else:
        return f"VALID ({int(remaining/60)} minutes remaining)"

def main():
    parser = argparse.ArgumentParser(description='Check health of Image Converter sessions and files')
    parser.add_argument('--data-path', default='/mnt/fastlane/docker/image-convert', 
                        help='Base path for Image Converter data')
    parser.add_argument('--expiration', type=int, default=3600,
                        help='Session expiration time in seconds (default: 3600)')
    args = parser.parse_args()

    # Set paths
    SESSION_FILE = os.path.join(args.data_path, 'image_data', 'sessions.json')
    UPLOAD_DIR = os.path.join(args.data_path, 'image_uploads')
    OUTPUT_DIR = os.path.join(args.data_path, 'image_outputs')
    
    print("\n===== IMAGE CONVERTER HEALTH CHECK =====\n")
    
    # Check directories
    print("Checking directories...")
    for directory in [os.path.join(args.data_path, 'image_data'), UPLOAD_DIR, OUTPUT_DIR]:
        if os.path.exists(directory):
            print_status(f"Directory exists: {directory}")
            if os.access(directory, os.W_OK):
                print_status(f"Directory is writable: {directory}")
            else:
                print_status(f"Directory is NOT writable: {directory}", False)
        else:
            print_status(f"Directory does NOT exist: {directory}", False)
    
    # Check sessions file
    print("\nChecking sessions...")
    if os.path.exists(SESSION_FILE):
        print_status(f"Sessions file exists: {SESSION_FILE}")
        try:
            with open(SESSION_FILE, 'r') as f:
                sessions = json.load(f)
            
            print_status(f"Sessions file loaded successfully. Found {len(sessions)} sessions.")
            
            # Check each session
            print("\nSession details:")
            for session_id, session_data in sessions.items():
                created_time = session_data.get('created_at', 0)
                status = check_expiration(created_time, args.expiration)
                
                print(f"\nSession ID: {session_id}")
                print(f"  Created: {format_time(created_time)}")
                print(f"  Status: {status}")
                
                # Check files
                files = session_data.get('files', [])
                if files:
                    print(f"  Files ({len(files)}):")
                    for file_info in files:
                        orig_filename = file_info.get('original_filename', 'N/A')
                        conv_filename = file_info.get('converted_filename', 'N/A')
                        
                        orig_path = os.path.join(UPLOAD_DIR, orig_filename)
                        conv_path = os.path.join(OUTPUT_DIR, conv_filename)
                        
                        print(f"    - Original: {orig_filename} ", end="")
                        if os.path.exists(orig_path):
                            print("(✓ exists)")
                        else:
                            print("(✗ missing)")
                        
                        print(f"      Converted: {conv_filename} ", end="")
                        if os.path.exists(conv_path):
                            print("(✓ exists)")
                        else:
                            print("(✗ missing)")
                else:
                    print("  No files in this session")
        except json.JSONDecodeError:
            print_status(f"Sessions file is corrupted or empty", False)
        except Exception as e:
            print_status(f"Error processing sessions file: {str(e)}", False)
    else:
        print_status(f"Sessions file does NOT exist: {SESSION_FILE}", False)
    
    print("\n===== HEALTH CHECK COMPLETE =====\n")

if __name__ == "__main__":
    main() 