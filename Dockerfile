FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Set BLIS architecture for ARM64
ENV BLIS_ARCH=generic

# Install system dependencies
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

# Install spaCy 3.8.3 and download model
RUN pip install --no-cache-dir spacy==3.8.3 \
    && python -m spacy download en_core_web_sm

# Clone GraphRAG repo and process dependencies
RUN git clone --depth 1 https://github.com/microsoft/graphrag.git /tmp/graphrag

# Copy dependency parser script
COPY parse_deps.py /tmp/parse_deps.py

# Install tomli first - required by parse_deps.py
RUN pip install --no-cache-dir tomli

# Parse dependencies and install them
RUN python /tmp/parse_deps.py \
    && pip install --no-cache-dir -r /tmp/graphrag-deps.txt \
    && pip install --no-cache-dir --no-deps graphrag==2.1.0 \
    && rm -rf /tmp/graphrag

# Copy requirements and install remaining packages
COPY requirements.txt .
RUN grep -v "graphrag" requirements.txt > requirements_no_graphrag.txt \
    && pip install --no-cache-dir -r requirements_no_graphrag.txt \
    && rm requirements_no_graphrag.txt

# Copy all application files
COPY . .

# Create necessary directories
RUN mkdir -p logs debug_logs input output

EXPOSE 20213

CMD ["uvicorn", "webserver.main:app", "--host", "0.0.0.0", "--port", "20213"]