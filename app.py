from flask import Flask, render_template, request, send_from_directory, jsonify, redirect, url_for
import os
import uuid
import time
import shutil
from pathlib import Path
from PIL import Image
import pillow_heif
import threading
import datetime
import json
import subprocess

# Setup Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_DIR', 'uploads')
app.config['OUTPUT_FOLDER'] = os.environ.get('OUTPUT_DIR', 'outputs')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload
app.config['EXPIRATION_TIME'] = int(os.environ.get('EXPIRATION_TIME', '3600'))  # 1 hour in seconds
app.config['SESSION_FILE'] = os.environ.get('SESSION_FILE', 'sessions.json')

# Get supported image formats from Pillow
def get_supported_formats():
    # Input formats - all formats that Pillow can open
    input_formats = Image.registered_extensions()
    readable_formats = {ext[1:].upper(): format_name 
                       for ext, format_name in input_formats.items() 
                       if format_name in Image.OPEN}
    
    # Output formats - all formats that Pillow can save
    writable_formats = {ext[1:].upper(): format_name 
                       for ext, format_name in input_formats.items() 
                       if format_name in Image.SAVE}
    
    # Add HEIC format since we have pillow_heif
    readable_formats['HEIC'] = 'HEIC'
    
    # Remove EPS from output formats (problematic format)
    if 'EPS' in writable_formats:
        del writable_formats['EPS']
    
    # Sort formats alphabetically
    sorted_input = sorted(readable_formats.keys())
    sorted_output = sorted(writable_formats.keys())
    
    return {
        'input_formats': sorted_input,
        'output_formats': sorted_output,
        'input_details': readable_formats,
        'output_details': writable_formats
    }

# Store supported formats for use in routes
SUPPORTED_FORMATS = get_supported_formats()

# Session tracking for expiration - use a more durable structure
sessions = {}

# Make sure data directory exists
data_dir = os.path.dirname(app.config['SESSION_FILE'])
if data_dir and data_dir != '.':
    os.makedirs(data_dir, exist_ok=True)

# Save sessions to disk to ensure they persist
def save_sessions():
    try:
        sessions_file = app.config['SESSION_FILE']
        with open(sessions_file, 'w') as f:
            # Create a serializable version of the sessions dictionary
            serializable_sessions = {}
            for session_id, session_data in sessions.items():
                if isinstance(session_data, (int, float)):
                    # Old format - just expiry time
                    serializable_sessions[session_id] = {
                        'created_at': session_data,
                        'files': []
                    }
                else:
                    # New format - full session data
                    serializable_sessions[session_id] = session_data
            
            json.dump(serializable_sessions, f, indent=2)
        
        print(f"[DEBUG] Saved {len(sessions)} sessions to {sessions_file}")
        print(f"[DEBUG] Session IDs: {list(sessions.keys())}")
    except Exception as e:
        print(f"[DEBUG] Error saving sessions: {str(e)}")

# Load sessions from disk on startup
def load_sessions():
    global sessions
    try:
        sessions_file = app.config['SESSION_FILE']
        if os.path.exists(sessions_file):
            with open(sessions_file, 'r') as f:
                loaded_data = json.load(f)
                
            # Clear existing sessions
            sessions.clear()
            
            # Process loaded data
            for session_id, session_data in loaded_data.items():
                if isinstance(session_data, str):
                    # Handle old string format (pre-update)
                    try:
                        sessions[session_id] = float(session_data)
                        print(f"[DEBUG] Loaded legacy session {session_id}")
                    except ValueError:
                        print(f"[DEBUG] Skipping invalid session data for {session_id}")
                elif isinstance(session_data, dict):
                    # Handle new dictionary format
                    sessions[session_id] = session_data
                    expiry_time = session_data.get('created_at', 0)
                    if isinstance(expiry_time, str):
                        try:
                            sessions[session_id]['created_at'] = float(expiry_time)
                        except ValueError:
                            sessions[session_id]['created_at'] = time.time()
                    print(f"[DEBUG] Loaded session {session_id} with {len(session_data.get('files', []))} files")
                else:
                    # Unknown format
                    print(f"[DEBUG] Unknown session data format for {session_id}")
            
            print(f"[DEBUG] Loaded {len(sessions)} sessions from {sessions_file}")
            for session_id in sessions:
                if isinstance(sessions[session_id], dict):
                    expiry_time = sessions[session_id].get('created_at', 0)
                else:
                    expiry_time = sessions[session_id]
                expiry_datetime = datetime.datetime.fromtimestamp(expiry_time)
                print(f"[DEBUG] Session {session_id} expires at {expiry_datetime}")
        else:
            print(f"[DEBUG] No sessions file found at {sessions_file}, starting with empty sessions")
            sessions = {}
            
            # Discover session directories and create entries for them
            output_dir = app.config['OUTPUT_FOLDER']
            if os.path.exists(output_dir):
                for item in os.listdir(output_dir):
                    item_path = os.path.join(output_dir, item)
                    if os.path.isdir(item_path) and len(item) >= 32:  # Likely a UUID
                        # Create a new session entry with long expiration
                        sessions[item] = {
                            'created_at': time.time() + (24 * 3600),  # 24 hour expiration
                            'files': []
                        }
                        print(f"[DEBUG] Auto-discovered session directory: {item}")
                
                # Save discovered sessions
                if sessions:
                    save_sessions()
    except Exception as e:
        print(f"[DEBUG] Error loading sessions: {str(e)}")
        sessions = {}

# Configure server name from environment if available
server_name = os.environ.get('FLASK_SERVER_NAME')
if server_name:
    app.config['SERVER_NAME'] = server_name
    print(f"Using SERVER_NAME: {server_name}")

# Ensure upload and output directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Load sessions on startup
load_sessions()

def cleanup_expired_sessions():
    """Cleanup thread that runs in the background to remove expired sessions"""
    while True:
        current_time = time.time()
        expired_sessions = []
        
        # Find expired sessions
        for session_id, session_data in list(sessions.items()):
            # Handle both old and new format
            if isinstance(session_data, dict):
                expiry_time = session_data.get('created_at', 0)
            else:
                expiry_time = session_data
                
            if current_time > expiry_time:
                expired_sessions.append(session_id)
        
        if expired_sessions:
            print(f"[DEBUG] Found {len(expired_sessions)} expired sessions to clean up")
            
            # Clean up expired sessions
            for session_id in expired_sessions:
                try:
                    cleanup_session(session_id)
                    print(f"Auto-cleaned expired session: {session_id}")
                except Exception as e:
                    print(f"Error cleaning up session {session_id}: {str(e)}")
            
            # Save sessions after cleanup
            save_sessions()
        
        # Sleep for 5 minutes before checking again
        time.sleep(300)

def cleanup_session(session_id):
    """Clean up a session's files"""
    # Remove from tracking dict
    if session_id in sessions:
        del sessions[session_id]
        save_sessions()  # Save sessions after removal
    
    # Don't remove files for troubleshooting purposes
    # session_dir = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
    # if os.path.exists(session_dir):
    #     shutil.rmtree(session_dir, ignore_errors=True)
    
    # Remove zip file if it exists
    zip_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{session_id}_converted.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    
    print(f"[DEBUG] Cleaned up session: {session_id}")

def convert_eps_with_ghostscript(input_path, output_path, output_format):
    """
    Convert EPS file to other formats using Ghostscript
    """
    try:
        # Verify input file exists and is readable
        if not os.path.exists(input_path):
            raise Exception(f"Input file not found: {input_path}")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # For other formats, use a simplified approach
        dpi = 300  # Use high DPI for quality
        device = 'png16m' if output_format.lower() == 'png' else 'jpeg'
        temp_path = f"{output_path}.temp.png"
        
        # Try to determine the Ghostscript version to use appropriate device
        ps_device = 'pswrite'  # Default for older versions
        try:
            gs_version_result = subprocess.run(['gs', '--version'], capture_output=True, text=True)
            if gs_version_result.returncode == 0:
                version_str = gs_version_result.stdout.strip()
                print(f"[DEBUG] Ghostscript version: {version_str}")
                # Parse version
                try:
                    version_parts = [int(part) for part in version_str.split('.')]
                    if len(version_parts) >= 2:
                        # eps2write introduced in GS 9.21, pswrite deprecated before that
                        if version_parts[0] > 9 or (version_parts[0] == 9 and version_parts[1] >= 21):
                            ps_device = 'eps2write'
                        elif version_parts[0] >= 9:
                            ps_device = 'epswrite'
                except ValueError:
                    print(f"[DEBUG] Could not parse GS version, using {ps_device}")
        except Exception as e:
            print(f"[DEBUG] Error checking GS version: {str(e)}, using {ps_device}")
        
        # Use simplified settings for broader compatibility
        cmd = [
            'gs', '-q', '-dNOPAUSE', '-dBATCH', '-dSAFER',
            f'-sDEVICE={device}',
            f'-r{dpi}',
            f'-sOutputFile={temp_path}',
            input_path
        ]
        
        # Add JPEG-specific settings if converting to JPEG
        if device == 'jpeg':
            cmd.extend([
                '-dJPEGQ=95',  # High JPEG quality
            ])
        
        # Run Ghostscript with error capture
        print(f"[DEBUG] Running GS command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[DEBUG] Ghostscript stderr: {result.stderr}")
            print(f"[DEBUG] Ghostscript stdout: {result.stdout}")
            raise Exception(f"Ghostscript failed: {result.stderr}")
        
        if not os.path.exists(temp_path):
            raise Exception(f"Ghostscript did not create output file: {temp_path}")
        
        # Convert the high-quality temp file to final format using Pillow
        try:
            with Image.open(temp_path) as img:
                if output_format.lower() in ['jpeg', 'jpg']:
                    img = img.convert('RGB')
                    # Use high-quality JPEG settings
                    img.save(output_path, output_format.upper(), quality=95, optimize=True)
                else:
                    img.save(output_path, output_format.upper())
        except Exception as e:
            raise Exception(f"Failed to convert temporary file to final format: {str(e)}")
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        # Verify the final output file exists
        if not os.path.exists(output_path):
            raise Exception("Failed to create final output file")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"[DEBUG] Ghostscript conversion failed: {str(e)}")
        if hasattr(e, 'stderr'):
            print(f"[DEBUG] Ghostscript stderr: {e.stderr}")
        if hasattr(e, 'stdout'):
            print(f"[DEBUG] Ghostscript stdout: {e.stdout}")
        return False
    except Exception as e:
        print(f"[DEBUG] Error in EPS conversion: {str(e)}")
        return False

@app.route('/')
def index():
    print("Root route accessed!")
    return render_template('index.html', 
                          input_formats=SUPPORTED_FORMATS['input_formats'],
                          output_formats=SUPPORTED_FORMATS['output_formats'])

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'files[]' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files[]')
        if not files or files[0].filename == '':
            return jsonify({'error': 'No files selected'}), 400
            
        output_format = request.form.get('format', 'JPEG')
        if not output_format:
            return jsonify({'error': 'No output format specified'}), 400
        
        # Extra validation to explicitly block EPS output format
        if output_format.lower() == 'eps':
            return jsonify({'error': 'EPS output format is not supported'}), 400
            
        # Validate output format
        if output_format.upper() not in SUPPORTED_FORMATS['output_formats']:
            return jsonify({'error': f'Unsupported output format: {output_format}'}), 400
        
        # Create session
        session_id = str(uuid.uuid4())
        session_output_dir = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
        os.makedirs(session_output_dir, exist_ok=True)
        
        # Print detailed debug info
        print(f"[DEBUG] Created session directory: {session_output_dir}")
        print(f"[DEBUG] Converting to format: {output_format}")
        print(f"[DEBUG] Number of files: {len(files)}")
        
        # Set expiration time
        expiry_time = time.time() + app.config['EXPIRATION_TIME']
        sessions[session_id] = {
            'created_at': expiry_time,
            'files': []
        }
        
        results = []
        conversion_errors = []
        
        for file in files:
            if file and file.filename:
                # Save uploaded file temporarily
                filename = file.filename
                print(f"[DEBUG] Processing file: {filename}")
                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                try:
                    file.save(temp_path)
                    print(f"[DEBUG] Saved temp file: {temp_path}")
                    
                    # Generate output path with format extension
                    file_stem = Path(filename).stem
                    output_filename = f"{file_stem}.{output_format.lower()}"
                    output_path = os.path.join(session_output_dir, output_filename)
                    print(f"[DEBUG] Output path: {output_path}")
                    
                    conversion_success = False
                    
                    # Special handling for EPS files as input (only support converting from EPS to other formats)
                    if filename.lower().endswith('.eps'):
                        print(f"[DEBUG] Processing EPS file: {filename}")
                        success = convert_eps_with_ghostscript(temp_path, output_path, output_format)
                        print(f"[DEBUG] EPS conversion result: {success}")
                        
                        # If conversion failed, try direct PIL conversion as fallback
                        if not success:
                            print("[DEBUG] EPS conversion failed, attempting PIL fallback")
                            try:
                                # Try direct PIL conversion which is more limited but more compatible
                                image = Image.open(temp_path)
                                print(f"[DEBUG] PIL opened EPS file, mode={image.mode}, size={image.size}")
                                
                                # Convert to RGB if needed for certain output formats
                                if output_format.lower() in ['jpeg', 'jpg'] and image.mode != 'RGB':
                                    image = image.convert('RGB')
                                    print(f"[DEBUG] Converted to RGB mode")
                                
                                # Handle transparency for PNG
                                if output_format.lower() == 'png' and image.mode not in ['RGBA', 'RGB']:
                                    image = image.convert('RGBA')
                                    print(f"[DEBUG] Converted to RGBA mode for PNG")
                                
                                # Save with high quality
                                if output_format.lower() in ['jpeg', 'jpg']:
                                    image.save(output_path, output_format.upper(), quality=95)
                                else:
                                    image.save(output_path, output_format.upper())
                                
                                print(f"[DEBUG] PIL saved output to {output_path}")    
                                success = True
                                print("[DEBUG] PIL fallback succeeded")
                            except Exception as e:
                                print(f"[DEBUG] PIL fallback failed: {str(e)}")
                                success = False
                                    
                        if not success:
                            raise Exception("Failed to convert EPS file - all conversion methods failed")
                            
                        conversion_success = success
                    else:
                        # Handle HEIC files
                        if filename.lower().endswith('.heic'):
                            try:
                                heif_file = pillow_heif.read_heif(temp_path)
                                image = Image.frombytes(
                                    heif_file.mode,
                                    heif_file.size,
                                    heif_file.data,
                                    "raw",
                                )
                            except Exception as e:
                                raise Exception(f"Failed to read HEIC file: {str(e)}")
                        else:
                            # Use regular PIL for other formats
                            try:
                                image = Image.open(temp_path)
                            except Exception as e:
                                raise Exception(f"Failed to open image file: {str(e)}")
                        
                        # Convert to RGB if needed for certain output formats
                        if output_format.lower() in ['jpeg', 'jpg'] and image.mode != 'RGB':
                            image = image.convert('RGB')
                        
                        # Handle transparency for PNG
                        if output_format.lower() == 'png' and image.mode not in ['RGBA', 'RGB']:
                            image = image.convert('RGBA')
                        
                        # Save the image with specified format
                        try:
                            image.save(output_path, output_format.upper())
                            conversion_success = True
                        except Exception as e:
                            raise Exception(f"Failed to save converted image: {str(e)}")
                    
                    if not os.path.exists(output_path):
                        raise Exception("Conversion completed but output file not found")
                    
                    print(f"[DEBUG] Converted and saved: {output_path}")
                    
                    # Generate URLs
                    share_url = url_for('share_file', session_id=session_id, filename=output_filename, _external=True)
                    download_url = url_for('download_file', session_id=session_id, filename=output_filename)
                    print(f"[DEBUG] Share URL: {share_url}")
                    
                    # Track file in session
                    file_info = {
                        'original_filename': filename,
                        'converted_filename': output_filename,
                        'conversion_time': time.time()
                    }
                    sessions[session_id]['files'].append(file_info)
                    
                    results.append({
                        'original': filename,
                        'converted': output_filename,
                        'status': 'success',
                        'download_url': download_url,
                        'share_url': share_url
                    })
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"[DEBUG] Error converting {filename}: {error_msg}")
                    conversion_errors.append(error_msg)
                    results.append({
                        'original': filename,
                        'status': 'error',
                        'error': error_msg
                    })
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
        
        # Save session data after all files processed
        save_sessions()
        
        # If all conversions failed, remove empty session directory
        if all(result['status'] == 'error' for result in results):
            shutil.rmtree(session_output_dir, ignore_errors=True)
            if session_id in sessions:
                del sessions[session_id]
                save_sessions()
            error_details = '; '.join(conversion_errors) if conversion_errors else 'Unknown error'
            return jsonify({
                'error': 'All conversions failed',
                'details': results,
                'message': error_details
            }), 500
        
        # Generate session URL
        session_url = url_for('view_session', session_id=session_id, _external=True)
        print(f"[DEBUG] Session URL: {session_url}")
        
        # Calculate expiration time for display
        expiry_datetime = datetime.datetime.fromtimestamp(expiry_time)
        expiry_formatted = expiry_datetime.strftime('%Y-%m-%d %H:%M:%S')
        
        response_data = {
            'session_id': session_id,
            'results': results,
            'download_all_url': url_for('download_all', session_id=session_id),
            'session_url': session_url,
            'expires_at': expiry_formatted,
            'expiration_seconds': app.config['EXPIRATION_TIME']
        }
        
        # If there were any errors but not all failed, include them in the response
        if conversion_errors:
            response_data['warnings'] = conversion_errors
        
        print(f"[DEBUG] Upload successful for session {session_id}")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"[DEBUG] Unexpected error in upload: {str(e)}")
        return jsonify({
            'error': 'Server error',
            'message': str(e)
        }), 500

@app.route('/check-session/<session_id>')
def check_session(session_id):
    """API endpoint to check if a session is still valid and when it expires"""
    if session_id in sessions:
        # Handle both old and new format
        if isinstance(sessions[session_id], dict):
            expiry_time = sessions[session_id].get('created_at', 0)
        else:
            expiry_time = sessions[session_id]
            
        current_time = time.time()
        
        if current_time <= expiry_time:
            time_left = int(expiry_time - current_time)
            expiry_datetime = datetime.datetime.fromtimestamp(expiry_time)
            expiry_formatted = expiry_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            return jsonify({
                'valid': True,
                'expires_at': expiry_formatted,
                'seconds_left': time_left
            })
    
    # Session not found or expired
    return jsonify({
        'valid': False
    })

@app.route('/share/<session_id>/<filename>')
def share_file(session_id, filename):
    """Render a simple page to view and download shared file"""
    print(f"[DEBUG] Share request for session_id: {session_id}, filename: {filename}")
    print(f"[DEBUG] Active sessions: {list(sessions.keys())}")
    
    # Check if session exists and is not expired
    if session_id not in sessions:
        print(f"[DEBUG] Session {session_id} not found in sessions dict")
        # Check if file exists anyway (for recovery purposes)
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], session_id, filename)
        if os.path.exists(file_path):
            print(f"[DEBUG] File exists but session is not registered: {file_path}")
            # Auto-register the session
            expiry_time = time.time() + app.config['EXPIRATION_TIME']
            sessions[session_id] = {
                'created_at': expiry_time,
                'files': [{
                    'original_filename': filename,
                    'converted_filename': filename,
                    'conversion_time': time.time()
                }]
            }
            save_sessions()
            print(f"[DEBUG] Auto-registered session {session_id}")
        else:
            return render_template('error.html', message="File link has expired or is invalid"), 404
    
    # Get expiry time, handling both formats
    if isinstance(sessions[session_id], dict):
        expiry_time = sessions[session_id].get('created_at', 0)
    else:
        expiry_time = sessions[session_id]
        
    if time.time() > expiry_time:
        # Expired but don't clean up, just report
        print(f"[DEBUG] Session {session_id} expired at {datetime.datetime.fromtimestamp(expiry_time)}")
        return render_template('error.html', message="File link has expired"), 404
    
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], session_id, filename)
    if not os.path.exists(file_path):
        print(f"[DEBUG] File not found: {file_path}")
        return render_template('error.html', message="File not found or has expired"), 404
    
    print(f"[DEBUG] File exists: {file_path}")
    file_url = url_for('static_file', session_id=session_id, filename=filename)
    download_url = url_for('download_file', session_id=session_id, filename=filename)
    
    # Calculate time left
    time_left = int(expiry_time - time.time())
    expiry_datetime = datetime.datetime.fromtimestamp(expiry_time)
    expiry_formatted = expiry_datetime.strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('share.html', 
                           filename=filename, 
                           file_url=file_url, 
                           download_url=download_url,
                           expires_at=expiry_formatted,
                           seconds_left=time_left,
                           session_id=session_id)

@app.route('/static-file/<session_id>/<filename>')
def static_file(session_id, filename):
    """Serve the file for viewing in the browser (not as attachment)"""
    # Auto-register session if it exists on disk but not in memory
    if session_id not in sessions:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], session_id, filename)
        if os.path.exists(file_path):
            # Auto-register the session
            expiry_time = time.time() + app.config['EXPIRATION_TIME']
            sessions[session_id] = {
                'created_at': expiry_time,
                'files': [{
                    'original_filename': filename,
                    'converted_filename': filename,
                    'conversion_time': time.time()
                }]
            }
            save_sessions()
            print(f"[DEBUG] Auto-registered session {session_id} for static file")
    
    # Check if session exists and is not expired
    if session_id not in sessions:
        return render_template('error.html', message="File link has expired or is invalid"), 404
    
    # Get expiry time, handling both formats
    if isinstance(sessions[session_id], dict):
        expiry_time = sessions[session_id].get('created_at', 0)
    else:
        expiry_time = sessions[session_id]
        
    if time.time() > expiry_time:
        # Don't clean up, just report expiry
        print(f"[DEBUG] Session {session_id} expired for static file")
        return render_template('error.html', message="File link has expired"), 404
    
    directory = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
    return send_from_directory(directory, filename)

@app.route('/session/<session_id>')
def view_session(session_id):
    """View all files in a session"""
    # Auto-register session if it exists on disk but not in memory
    if session_id not in sessions:
        session_dir = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
        if os.path.exists(session_dir) and os.path.isdir(session_dir):
            # Auto-register the session
            expiry_time = time.time() + app.config['EXPIRATION_TIME']
            sessions[session_id] = {
                'created_at': expiry_time,
                'files': []
            }
            
            # Scan for files
            for filename in os.listdir(session_dir):
                if os.path.isfile(os.path.join(session_dir, filename)) and not filename.endswith('.zip'):
                    sessions[session_id]['files'].append({
                        'original_filename': filename,
                        'converted_filename': filename,
                        'conversion_time': time.time()
                    })
            
            save_sessions()
            print(f"[DEBUG] Auto-registered session {session_id} with {len(sessions[session_id]['files'])} files")
    
    # Check if session exists and is not expired
    if session_id not in sessions:
        return render_template('error.html', message="Session link has expired or is invalid"), 404
    
    # Get expiry time, handling both formats
    if isinstance(sessions[session_id], dict):
        expiry_time = sessions[session_id].get('created_at', 0)
    else:
        expiry_time = sessions[session_id]
        
    if time.time() > expiry_time:
        # Don't clean up, just report expiry
        return render_template('error.html', message="Session link has expired"), 404
    
    session_dir = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
    if not os.path.exists(session_dir):
        return render_template('error.html', message="Session not found or has expired"), 404
    
    files = []
    for filename in os.listdir(session_dir):
        if os.path.isfile(os.path.join(session_dir, filename)) and not filename.endswith('.zip'):
            file_url = url_for('static_file', session_id=session_id, filename=filename)
            download_url = url_for('download_file', session_id=session_id, filename=filename)
            share_url = url_for('share_file', session_id=session_id, filename=filename, _external=True)
            files.append({
                'filename': filename,
                'file_url': file_url,
                'download_url': download_url,
                'share_url': share_url
            })
    
    download_all_url = url_for('download_all', session_id=session_id)
    
    # Calculate time left
    time_left = int(expiry_time - time.time())
    expiry_datetime = datetime.datetime.fromtimestamp(expiry_time)
    expiry_formatted = expiry_datetime.strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('session.html', 
                          session_id=session_id, 
                          files=files, 
                          download_all_url=download_all_url,
                          expires_at=expiry_formatted,
                          seconds_left=time_left)

@app.route('/download/<session_id>/<filename>')
def download_file(session_id, filename):
    # Auto-register session if it exists on disk but not in memory
    if session_id not in sessions:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], session_id, filename)
        if os.path.exists(file_path):
            # Auto-register the session
            expiry_time = time.time() + app.config['EXPIRATION_TIME']
            sessions[session_id] = {
                'created_at': expiry_time,
                'files': [{
                    'original_filename': filename,
                    'converted_filename': filename,
                    'conversion_time': time.time()
                }]
            }
            save_sessions()
            print(f"[DEBUG] Auto-registered session {session_id} for download")
    
    # Check if session exists and is not expired
    if session_id not in sessions:
        return render_template('error.html', message="File link has expired or is invalid"), 404
    
    # Get expiry time, handling both formats
    if isinstance(sessions[session_id], dict):
        expiry_time = sessions[session_id].get('created_at', 0)
    else:
        expiry_time = sessions[session_id]
        
    if time.time() > expiry_time:
        # Don't clean up, just report expiry
        print(f"[DEBUG] Session {session_id} expired for download")
        return render_template('error.html', message="File link has expired"), 404
    
    directory = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
    return send_from_directory(directory, filename, as_attachment=True)

@app.route('/download-all/<session_id>')
def download_all(session_id):
    # Auto-register session if it exists on disk but not in memory
    if session_id not in sessions:
        session_dir = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
        if os.path.exists(session_dir) and os.path.isdir(session_dir):
            # Auto-register the session
            expiry_time = time.time() + app.config['EXPIRATION_TIME']
            sessions[session_id] = {
                'created_at': expiry_time,
                'files': []
            }
            
            # Scan for files
            for filename in os.listdir(session_dir):
                if os.path.isfile(os.path.join(session_dir, filename)) and not filename.endswith('.zip'):
                    sessions[session_id]['files'].append({
                        'original_filename': filename,
                        'converted_filename': filename,
                        'conversion_time': time.time()
                    })
            
            save_sessions()
            print(f"[DEBUG] Auto-registered session {session_id} for download-all")
    
    # Check if session exists and is not expired
    if session_id not in sessions:
        return render_template('error.html', message="Session link has expired or is invalid"), 404
    
    # Get expiry time, handling both formats
    if isinstance(sessions[session_id], dict):
        expiry_time = sessions[session_id].get('created_at', 0)
    else:
        expiry_time = sessions[session_id]
        
    if time.time() > expiry_time:
        # Don't clean up, just report expiry
        print(f"[DEBUG] Session {session_id} expired for download-all")
        return render_template('error.html', message="Session link has expired"), 404
    
    # Create a zip of all files in the session
    session_dir = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
    zip_filename = f"{session_id}_converted.zip"
    zip_path = os.path.join(app.config['OUTPUT_FOLDER'], zip_filename)
    
    # Create zip file
    shutil.make_archive(zip_path.replace('.zip', ''), 'zip', session_dir)
    
    return send_from_directory(app.config['OUTPUT_FOLDER'], zip_filename, as_attachment=True)

@app.route('/cleanup/<session_id>', methods=['POST'])
def cleanup(session_id):
    """Clean up files after download"""
    cleanup_session(session_id)
    return jsonify({'status': 'success'})

@app.route('/extend/<session_id>', methods=['POST'])
def extend_session(session_id):
    """Extend the session expiration time by another hour"""
    print(f"[DEBUG] Extend request for session_id: {session_id}")
    print(f"[DEBUG] Active sessions: {list(sessions.keys())}")
    
    # Check if the directory exists even if not in sessions dict
    session_dir = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
    if session_id not in sessions and os.path.exists(session_dir) and os.path.isdir(session_dir):
        print(f"[DEBUG] Session directory exists but not in sessions dict: {session_id}")
        # Auto-register the session
        expiry_time = time.time() + app.config['EXPIRATION_TIME']
        sessions[session_id] = {
            'created_at': expiry_time,
            'files': []
        }
        
        # Scan for files
        for filename in os.listdir(session_dir):
            if os.path.isfile(os.path.join(session_dir, filename)) and not filename.endswith('.zip'):
                sessions[session_id]['files'].append({
                    'original_filename': filename,
                    'converted_filename': filename,
                    'conversion_time': time.time()
                })
        
        save_sessions()
        print(f"[DEBUG] Auto-registered session {session_id}")
    
    if session_id in sessions:
        # Add another hour
        new_expiry = time.time() + app.config['EXPIRATION_TIME']
        
        # Update expiry time, handling both formats
        if isinstance(sessions[session_id], dict):
            sessions[session_id]['created_at'] = new_expiry
        else:
            sessions[session_id] = new_expiry
            
        save_sessions()  # Save sessions after extension
        
        expiry_datetime = datetime.datetime.fromtimestamp(new_expiry)
        expiry_formatted = expiry_datetime.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[DEBUG] Extended session {session_id} to {expiry_formatted}")
        
        return jsonify({
            'status': 'success',
            'expires_at': expiry_formatted,
            'seconds_left': app.config['EXPIRATION_TIME']
        })
    
    print(f"[DEBUG] Session not found for extension: {session_id}")
    return jsonify({'status': 'error', 'message': 'Session not found'}), 404

@app.route('/api/formats')
def get_formats():
    """Return supported formats as JSON"""
    return jsonify(SUPPORTED_FORMATS)

@app.route('/api/check-gs')
def check_ghostscript():
    """Check if Ghostscript is available"""
    try:
        result = subprocess.run(['gs', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            return jsonify({
                'status': 'success',
                'version': result.stdout.strip(),
                'message': 'Ghostscript is available'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Ghostscript command returned error',
                'stderr': result.stderr
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to check Ghostscript: {str(e)}'
        }), 500

# Error handlers
@app.errorhandler(413)
def too_large(error):
    return jsonify({'error': 'File too large (max 50MB)'}), 413

@app.errorhandler(404)
def page_not_found(error):
    print(f"404 error: {request.path} - Referrer: {request.referrer}")
    if request.path == '/':
        print("Root path was not found! Make sure index.html is in templates directory.")
        try:
            print(f"Templates directory contents: {os.listdir('templates')}")
        except Exception as e:
            print(f"Error listing templates: {str(e)}")
    
    return render_template('error.html', message=f"Page not found: {request.path}"), 404

# Add static file route for SVG and other static assets
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/debug/session/<session_id>')
def debug_session(session_id):
    """Debug endpoint to check session information"""
    if not app.debug:
        return jsonify({'error': 'Debug endpoints only available in debug mode'}), 403
        
    result = {
        'session_id': session_id,
        'in_memory': session_id in sessions,
        'directory_exists': False
    }
    
    # Check if session directory exists
    session_dir = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
    if os.path.exists(session_dir) and os.path.isdir(session_dir):
        result['directory_exists'] = True
        
        # List files in the directory
        files = []
        for filename in os.listdir(session_dir):
            file_path = os.path.join(session_dir, filename)
            if os.path.isfile(file_path):
                files.append({
                    'name': filename,
                    'size': os.path.getsize(file_path),
                    'modified': datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                })
        result['files'] = files
    
    # Include session data if it exists
    if session_id in sessions:
        session_data = sessions[session_id]
        if isinstance(session_data, dict):
            expiry_time = session_data.get('created_at', 0)
            result['session_data'] = {
                'expires_at': datetime.datetime.fromtimestamp(expiry_time).strftime('%Y-%m-%d %H:%M:%S'),
                'seconds_left': int(expiry_time - time.time()),
                'files_count': len(session_data.get('files', []))
            }
        else:
            # Handle legacy format
            result['session_data'] = {
                'expires_at': datetime.datetime.fromtimestamp(session_data).strftime('%Y-%m-%d %H:%M:%S'),
                'seconds_left': int(session_data - time.time()),
                'legacy_format': True
            }
    
    # Include all active sessions
    result['active_sessions'] = list(sessions.keys())
    
    return jsonify(result)

# Enable debug mode for testing
app.debug = True

if __name__ == '__main__':
    # Start background cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_expired_sessions, daemon=True)
    cleanup_thread.start()
    
    # FORCE port 5000 with no randomization whatsoever
    port = 5000
    print(f"FORCING PORT 5000 - IGNORING ALL OTHER PORT SETTINGS")
    print(f"Running on http://0.0.0.0:{port}")
    import socket
    import sys
    
    try:
        # Force the port to always be 5000, ignoring Flask's dynamic port allocation
        app.run(host='0.0.0.0', port=5000, debug=False)
    except socket.error as e:
        print(f"ERROR: Could not bind to port 5000: {e}")
        sys.exit(1) 