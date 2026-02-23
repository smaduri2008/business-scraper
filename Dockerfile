FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Start command
CMD gunicorn run:app --bind 0.0.0.0:$PORT --timeout 600 --workers 1 --log-level info
CMD ["sh", "-c", "gunicorn run:app --bind 0.0.0.0:${PORT:-8080} --timeout 600 --workers 1 --log-level info"FROM mcr.microsoft.com/playwright/python:v1.48.0-noble

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Start command with proper shell expansion
CMD gunicorn run:app --bind 0.0.0.0:8080 --timeout 600 --workers 1 --log-level info
