#!/usr/bin/env python3
import os
import json
import time
import shutil
import argparse
from datetime import datetime
import glob

def print_colored(message, color_code):
    """Print message with color."""
    print(f"\033[{color_code}m{message}\033[0m")

def print_success(message):
    print_colored(message, "92")  # Green

def print_error(message):
    print_colored(message, "91")  # Red

def print_warning(message):
    print_colored(message, "93")  # Yellow

def print_info(message):
    print_colored(message, "96")  # Cyan

def format_time(timestamp):
    """Format a timestamp into a readable datetime."""
    return datetime.fromtimestamp(float(timestamp)).strftime('%Y-%m-%d %H:%M:%S')

def main():
    parser = argparse.ArgumentParser(description='Recover files from Image Converter outputs')
    parser.add_argument('--data-path', default='/mnt/fastlane/docker/image-convert', 
                        help='Base path for Image Converter data')
    parser.add_argument('--filename', 
                        help='Filename to search for and recover')
    parser.add_argument('--session-id',
                        help='Session ID to recover files from')
    parser.add_argument('--recover-all', action='store_true',
                        help='Recover all files from all sessions')
    parser.add_argument('--output-dir', default='./recovered_files',
                        help='Directory to save recovered files to')
    parser.add_argument('--force', action='store_true',
                        help='Overwrite existing files in output directory')
    args = parser.parse_args()

    # Set paths
    SESSION_FILE = os.path.join(args.data_path, 'image_data', 'sessions.json')
    OUTPUT_DIR = os.path.join(args.data_path, 'image_outputs')
    
    # Create recovery directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    print_info("\n===== IMAGE CONVERTER FILE RECOVERY TOOL =====\n")
    
    # Check if output directory exists
    print_info("Checking output directory...")
    if os.path.exists(OUTPUT_DIR):
        print_success(f"Output directory exists: {OUTPUT_DIR}")
    else:
        print_error(f"Output directory does NOT exist: {OUTPUT_DIR}")
        return 1
    
    # If no session file exists yet but there are directories
    session_dirs = []
    for dir_path in glob.glob(os.path.join(OUTPUT_DIR, '*')):
        if os.path.isdir(dir_path) and not os.path.basename(dir_path).startswith('.'):
            session_id = os.path.basename(dir_path)
            if len(session_id) >= 32:  # Likely a UUID session directory
                session_dirs.append(session_id)
    
    if session_dirs:
        print_info(f"Found {len(session_dirs)} session directories on disk")
    
    # Check for session file
    sessions = {}
    if os.path.exists(SESSION_FILE):
        print_success(f"Sessions file exists: {SESSION_FILE}")
        try:
            with open(SESSION_FILE, 'r') as f:
                sessions = json.load(f)
            print_success(f"Loaded {len(sessions)} sessions from file")
        except json.JSONDecodeError:
            print_error(f"Sessions file is corrupted or empty")
        except Exception as e:
            print_error(f"Error loading sessions: {str(e)}")
    else:
        print_warning(f"Sessions file does NOT exist: {SESSION_FILE}")
    
    # Recover files based on arguments
    recovered_files = []
    
    # Case 1: Recover by filename
    if args.filename:
        print_info(f"\nSearching for filename: {args.filename}")
        found = False
        
        # First look in session file (if it exists)
        for session_id, session_data in sessions.items():
            if isinstance(session_data, dict) and 'files' in session_data:
                for file_info in session_data.get('files', []):
                    if file_info.get('converted_filename') == args.filename or file_info.get('original_filename') == args.filename:
                        found = True
                        source_path = os.path.join(OUTPUT_DIR, session_id, args.filename)
                        if os.path.exists(source_path):
                            dest_path = os.path.join(args.output_dir, args.filename)
                            if os.path.exists(dest_path) and not args.force:
                                print_warning(f"File already exists in output directory: {dest_path}")
                                print_warning("Use --force to overwrite")
                            else:
                                shutil.copy2(source_path, dest_path)
                                print_success(f"Recovered file: {args.filename} from session {session_id}")
                                recovered_files.append(dest_path)
                        else:
                            print_error(f"File found in session {session_id} but not on disk: {source_path}")
        
        # If not found in session file, search all directories
        if not found:
            print_info("File not found in session data, searching directories...")
            for session_id in session_dirs:
                source_path = os.path.join(OUTPUT_DIR, session_id, args.filename)
                if os.path.exists(source_path):
                    dest_path = os.path.join(args.output_dir, args.filename)
                    if os.path.exists(dest_path) and not args.force:
                        print_warning(f"File already exists in output directory: {dest_path}")
                        print_warning("Use --force to overwrite")
                    else:
                        shutil.copy2(source_path, dest_path)
                        print_success(f"Recovered file: {args.filename} from session {session_id}")
                        recovered_files.append(dest_path)
                        found = True
            
            # If still not found, do a recursive search
            if not found:
                print_info("Performing deep search for file...")
                for root, dirs, files in os.walk(OUTPUT_DIR):
                    if args.filename in files:
                        source_path = os.path.join(root, args.filename)
                        dest_path = os.path.join(args.output_dir, args.filename)
                        if os.path.exists(dest_path) and not args.force:
                            print_warning(f"File already exists in output directory: {dest_path}")
                            print_warning("Use --force to overwrite")
                        else:
                            shutil.copy2(source_path, dest_path)
                            print_success(f"Recovered file: {args.filename} from {source_path}")
                            recovered_files.append(dest_path)
                            found = True
            
            if not found:
                print_error(f"File not found: {args.filename}")
    
    # Case 2: Recover by session ID
    elif args.session_id:
        print_info(f"\nRecovering files from session: {args.session_id}")
        session_dir = os.path.join(OUTPUT_DIR, args.session_id)
        if os.path.exists(session_dir):
            file_count = 0
            for filename in os.listdir(session_dir):
                if os.path.isfile(os.path.join(session_dir, filename)):
                    source_path = os.path.join(session_dir, filename)
                    dest_path = os.path.join(args.output_dir, filename)
                    if os.path.exists(dest_path) and not args.force:
                        print_warning(f"File already exists in output directory: {dest_path}")
                        print_warning("Use --force to overwrite")
                    else:
                        shutil.copy2(source_path, dest_path)
                        print_success(f"Recovered file: {filename}")
                        recovered_files.append(dest_path)
                        file_count += 1
            
            if file_count == 0:
                print_warning(f"No files found in session directory: {session_dir}")
            else:
                print_success(f"Recovered {file_count} files from session {args.session_id}")
        else:
            print_error(f"Session directory not found: {session_dir}")
    
    # Case 3: Recover all files
    elif args.recover_all:
        print_info("\nRecovering all files from all sessions")
        total_files = 0
        
        # Recover from session directories
        for session_id in session_dirs:
            session_dir = os.path.join(OUTPUT_DIR, session_id)
            if os.path.exists(session_dir):
                file_count = 0
                for filename in os.listdir(session_dir):
                    if os.path.isfile(os.path.join(session_dir, filename)):
                        source_path = os.path.join(session_dir, filename)
                        # Use session ID as subdirectory to avoid filename conflicts
                        session_recovery_dir = os.path.join(args.output_dir, session_id)
                        os.makedirs(session_recovery_dir, exist_ok=True)
                        dest_path = os.path.join(session_recovery_dir, filename)
                        if os.path.exists(dest_path) and not args.force:
                            print_warning(f"File already exists: {dest_path}")
                        else:
                            shutil.copy2(source_path, dest_path)
                            recovered_files.append(dest_path)
                            file_count += 1
                
                if file_count > 0:
                    print_success(f"Recovered {file_count} files from session {session_id}")
                    total_files += file_count
        
        print_success(f"\nTotal files recovered: {total_files}")
    
    # No action specified
    else:
        print_warning("No recovery action specified. Use --filename, --session-id, or --recover-all")
        parser.print_help()
        return 1
    
    # Print summary
    if recovered_files:
        print_success(f"\nSuccessfully recovered {len(recovered_files)} files to {args.output_dir}")
    else:
        print_warning("\nNo files were recovered")
    
    print_info("\n===== RECOVERY COMPLETE =====\n")
    return 0

if __name__ == "__main__":
    exit(main()) 