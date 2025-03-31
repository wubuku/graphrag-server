FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Set BLIS architecture for ARM64
ENV BLIS_ARCH=generic

# Install system dependencies and clean up in the same layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Note: We're using spaCy 3.8.3 instead of 3.8.4 because:
# 1. GraphRAG depends on spaCy >=3.8.4, but this version may not be available for ARM64
# 2. We'll install GraphRAG with --no-deps to bypass the version check
# 3. spaCy 3.8.3 is functionally compatible and available for our architecture

# Install tomli and spaCy, download model in a single layer
RUN pip install --no-cache-dir tomli spacy==3.8.3 \
    && python -m spacy download en_core_web_sm

# Process GraphRAG dependencies in a single layer
COPY parse_deps.py /tmp/parse_deps.py
RUN git clone --depth 1 https://github.com/microsoft/graphrag.git /tmp/graphrag \
    && python /tmp/parse_deps.py \
    && pip install --no-cache-dir -r /tmp/graphrag-deps.txt \
    && pip install --no-cache-dir --no-deps graphrag==2.1.0 \
    && rm -rf /tmp/graphrag /tmp/parse_deps.py

# Copy requirements and install remaining packages
COPY requirements.txt .
RUN grep -v "graphrag" requirements.txt > requirements_no_graphrag.txt \
    && pip install --no-cache-dir -r requirements_no_graphrag.txt \
    && rm requirements_no_graphrag.txt

# Copy only necessary application files
COPY webserver/ ./webserver/
COPY prompts/ ./prompts/
COPY debug_server.py debug_env.py ./

# Create necessary directories
RUN mkdir -p logs debug_logs input output

# Clean up cache and temporary files to reduce image size
RUN pip cache purge \
    && find /usr/local -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local -name "*.pyc" -delete

EXPOSE 20213

CMD ["uvicorn", "webserver.main:app", "--host", "0.0.0.0", "--port", "20213"]