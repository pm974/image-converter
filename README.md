# Image Converter - Docker Web App

A web-based application that converts image files between various formats supported by the Pillow library. This application is containerized using Docker for easy deployment.

## Features

- Drag and drop interface for uploading image files
- Convert between numerous image formats (including JPEG, PNG, TIFF, BMP, GIF, WebP, HEIC, and more)
- Support for all image formats that the Pillow (PIL) library can handle
- Download converted files individually or as a ZIP archive
- **Share converted files with shareable links**
- **Session gallery with all converted files in one place**
- **Temporary links that expire after one hour for security**
- **File expiration system with countdown timers**
- **Option to extend expiration time when needed**
- Clean, modern interface with responsive design
- Automatic cleanup of temporary files
- **Uses random port for security (avoids common port conflicts)**

## Deployment Instructions

### Prerequisites

- Docker installed on your system
- Docker Compose installed
- Internet connection to pull the base image

### Quick Start (Recommended)

Use the included start script which automatically selects an available port and launches the application:

```bash
# Make the script executable
chmod +x build-and-run.sh

# Run the script
./build-and-run.sh
```

The script will:
1. Find an available port
2. Configure the container to use that port
3. Start the Docker container
4. Open your web browser to the application

### Server Setup and Maintenance

Several utility scripts are included to help with server setup and maintenance:

#### Setup Server Script

The `setup_server.sh` script ensures proper directory setup and container deployment:

```bash
# Make the script executable
chmod +x setup_server.sh

# Run the script
./setup_server.sh
```

This script:
1. Creates necessary data directories with proper permissions
2. Pulls the latest Docker image
3. Stops and removes any existing container
4. Starts the container with docker-compose
5. Displays container logs to verify proper startup

#### Health Check Script

The `check_health.py` script helps diagnose potential issues:

```bash
# Make the script executable
chmod +x check_health.py

# Run the script
./check_health.py

# Optional parameters
./check_health.py --data-path /custom/path --expiration 7200
```

This script:
1. Checks all data directories for existence and permissions
2. Verifies the sessions file integrity
3. Inspects all active sessions and their expiration status
4. Confirms existence of all original and converted files

#### Session Extension Script

The `extend_session.py` script allows manual extension of session lifetimes:

```bash
# Extend all active sessions by 24 hours (default)
./extend_session.py

# Extend a specific session by 48 hours
./extend_session.py --session-id YOUR_SESSION_ID --hours 48

# Force extension of expired sessions
./extend_session.py --force
```

#### File Recovery Tool

The `recover_file.py` script helps recover files even after sessions have expired:

```bash
# Make the script executable
chmod +x recover_file.py

# Recover a specific file by name
./recover_file.py --filename example.jpeg

# Recover all files from a specific session
./recover_file.py --session-id b35be978-972a-4eea-8c99-e3ac5fb2a0f9

# Recover all files from all sessions
./recover_file.py --recover-all

# Specify an output directory
./recover_file.py --filename test.jpeg --output-dir /path/to/recovery

# Force overwrite of existing files
./recover_file.py --session-id b35be978-972a-4eea-8c99-e3ac5fb2a0f9 --force
```

This script:
1. Searches for files in all session directories
2. Can recover individual files by name
3. Can recover all files from a specific session
4. Can recover all files from all sessions
5. Works even when session data is lost or corrupted

### Manual Building and Running

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/image-convert.git
   cd image-convert
   ```

2. Build the Docker image:
   ```
   docker build -t image-convert .
   ```

3. Run the container with Docker Compose:
   ```
   docker-compose up -d
   ```

   Docker Compose will assign a random available port from the range specified in the docker-compose.yml file.

4. Find the assigned port:
   ```
   docker-compose ps
   ```

The web application will be available at http://localhost:[assigned-port]

## Usage

1. Open your web browser and navigate to http://localhost:[assigned-port]
2. Drag and drop image files onto the dropzone, or click "Select Files" to browse
3. Select your desired output format from the dropdown list of supported formats
4. Click "Convert Files" to start the conversion process
5. Once conversion is complete:
   - **Download individual files** with the Download buttons
   - **Download all files** as a ZIP with the "Download All as ZIP" button
   - **Get a shareable link** for the entire session to share with others
   - **Share individual files** with unique links for each converted file
   - **Note the expiration time** displayed for all files and links

## Sharing Features

This application provides several ways to share your converted files:

1. **Session Links**: After conversion, you'll get a session URL that contains all your converted files. You can bookmark this link or share it with others.

2. **Individual File Links**: Each converted file has its own shareable link. Click the "Share" button next to any file to get a link that you can share.

3. **Gallery View**: The session link opens a gallery view showing all converted files with options to download or share each one.

4. **Time-Limited Access**: All links and files expire after one hour for security. A countdown timer is displayed on each page.

5. **Expiration Extension**: You can extend the expiration time by clicking the "Extend Time" button if you need more time to access the files.

## Automatic Cleanup

For security and to manage disk space efficiently:

1. All files and links automatically expire after one hour
2. A background process periodically cleans up expired files
3. Expired links will show an error message when accessed
4. Downloaded ZIP files are also cleaned up after expiration

## Troubleshooting

If you encounter issues with expired links or missing files:

1. Run the health check script to identify problems:
   ```
   ./check_health.py
   ```

2. Extend session lifetimes if needed:
   ```
   ./extend_session.py --session-id YOUR_SESSION_ID --hours 24
   ```

3. Recover files from expired or lost sessions:
   ```
   ./recover_file.py --recover-all
   ```

4. Ensure proper directory permissions:
   ```
   ./setup_server.sh
   ```

5. Check container logs for errors:
   ```
   docker logs image-convert
   ```

## Development

To build and run the container in development mode with live reloading:

```
docker run -d -p 5000:5000 -v $(pwd):/app --name image-convert-dev image-convert
```

## License

MIT License 