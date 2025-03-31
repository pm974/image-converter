FROM python:3.10-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    libheif-dev \
    netcat-openbsd \
    ghostscript \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create directories with proper permissions
RUN mkdir -p uploads outputs data
RUN chmod 777 uploads outputs data

# Copy application files
COPY app.py /app/app.py
COPY templates ./templates/
COPY static ./static/

# Create entrypoint script
RUN echo '#!/bin/bash\nset -e\n\nmkdir -p /app/uploads /app/outputs /app/data\nchmod 777 /app/uploads /app/outputs /app/data\n\n# Export environment variables\nexport UPLOAD_DIR=${UPLOAD_DIR:-/app/uploads}\nexport OUTPUT_DIR=${OUTPUT_DIR:-/app/outputs}\nexport SESSION_FILE=${SESSION_FILE:-/app/data/sessions.json}\n\n# Set server name if EXTERNAL_URL is provided\nif [ -n "$EXTERNAL_URL" ]; then\n  export FLASK_SERVER_NAME=$(echo $EXTERNAL_URL | sed "s/https\\?:\\/\\///g")\n  echo "Setting FLASK_SERVER_NAME to $FLASK_SERVER_NAME"\nfi\n\n# Start the WSGI server\nexec gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app\n' > /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Install gunicorn
RUN pip install gunicorn

# Expose port
EXPOSE 5000

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"] 