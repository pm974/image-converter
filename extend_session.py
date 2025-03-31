#!/usr/bin/env python3
import os
import json
import time
import argparse
from datetime import datetime

def format_time(timestamp):
    """Format a timestamp into a readable datetime."""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def main():
    parser = argparse.ArgumentParser(description='Extend Image Converter session lifetimes')
    parser.add_argument('--data-path', default='/mnt/fastlane/docker/image-convert', 
                        help='Base path for Image Converter data')
    parser.add_argument('--session-id', 
                        help='Specific session ID to extend (omit to extend all)')
    parser.add_argument('--hours', type=int, default=24,
                        help='Hours to extend session(s) from now (default: 24)')
    parser.add_argument('--force', action='store_true',
                        help='Force extension even for already expired sessions')
    args = parser.parse_args()

    # Set paths
    SESSION_FILE = os.path.join(args.data_path, 'image_data', 'sessions.json')
    
    # Check if sessions file exists
    if not os.path.exists(SESSION_FILE):
        print(f"Error: Sessions file does not exist at {SESSION_FILE}")
        return 1
    
    try:
        # Load sessions
        with open(SESSION_FILE, 'r') as f:
            sessions = json.load(f)
        
        if not sessions:
            print("No sessions found in the sessions file.")
            return 0
        
        # Current time and extension time (in seconds)
        current_time = time.time()
        extension_seconds = args.hours * 3600
        
        # Count for stats
        extended_count = 0
        skipped_count = 0
        
        # Process sessions
        if args.session_id:
            # Extend specific session
            if args.session_id in sessions:
                session = sessions[args.session_id]
                created_at = session.get('created_at', 0)
                
                # Check if session is expired and force is not enabled
                if created_at < current_time - 3600 and not args.force:
                    print(f"Session {args.session_id} is already expired. Use --force to extend anyway.")
                    skipped_count += 1
                else:
                    # Set new creation time (current time)
                    sessions[args.session_id]['created_at'] = current_time
                    
                    before_time = format_time(created_at)
                    after_time = format_time(current_time)
                    expiry_time = format_time(current_time + extension_seconds)
                    
                    print(f"Extended session: {args.session_id}")
                    print(f"  Before: {before_time}")
                    print(f"  After: {after_time}")
                    print(f"  New expiry: {expiry_time}")
                    extended_count += 1
            else:
                print(f"Error: Session {args.session_id} not found.")
                return 1
        else:
            # Extend all valid sessions (or all if force is enabled)
            for session_id, session_data in sessions.items():
                created_at = session_data.get('created_at', 0)
                
                # Check if session is expired and force is not enabled
                if created_at < current_time - 3600 and not args.force:
                    print(f"Skipping expired session: {session_id}")
                    skipped_count += 1
                    continue
                
                # Set new creation time (current time)
                sessions[session_id]['created_at'] = current_time
                
                before_time = format_time(created_at)
                after_time = format_time(current_time)
                expiry_time = format_time(current_time + extension_seconds)
                
                print(f"Extended session: {session_id}")
                print(f"  Before: {before_time}")
                print(f"  After: {after_time}")
                print(f"  New expiry: {expiry_time}")
                extended_count += 1
        
        # Save updated sessions
        with open(SESSION_FILE, 'w') as f:
            json.dump(sessions, f, indent=2)
        
        print(f"\nSummary: Extended {extended_count} sessions, skipped {skipped_count} expired sessions.")
        print(f"Sessions file updated at {SESSION_FILE}")
        
    except json.JSONDecodeError:
        print(f"Error: Sessions file is corrupted or not valid JSON.")
        return 1
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 