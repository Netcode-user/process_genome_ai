FROM python:3.11-slim

# Prevent Python from creating .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Ensure Python output appears immediately
ENV PYTHONUNBUFFERED=1

# Streamlit configuration
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for Docker layer caching
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create directories if your application writes runtime data
RUN mkdir -p /app/data

EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
