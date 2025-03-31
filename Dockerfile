FROM continuumio/miniconda3:latest

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Set BLIS architecture for ARM64
ENV BLIS_ARCH=generic

# Combine RUN commands and clean up in the same layer to reduce size
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libpython3-dev \
    pkg-config \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create conda environment and install all conda packages in one layer
RUN conda create -n graphrag python=3.10 -y \
    && echo "source activate graphrag" >> ~/.bashrc \
    && conda install -n graphrag -c conda-forge -y \
       "numpy=1.26.4" \
       cython \
       tomli \
    && conda clean -afy --all

    # Install spaCy 3.8.3 (available version)
# Note: We're using spaCy 3.8.3 instead of 3.8.4 because:
# 1. GraphRAG depends on spaCy >=3.8.4, but this version may not be available for ARM64
# 2. We'll install GraphRAG with --no-deps to bypass the version check
# 3. spaCy 3.8.3 is functionally compatible and available for our architecture
# Install spaCy and download model
RUN conda run -n graphrag pip install --no-cache-dir spacy==3.8.3 \
    && conda run -n graphrag python -m spacy download en_core_web_sm

# Clone GraphRAG repo, process dependencies, and clean up in the same layer
RUN git clone --depth 1 https://github.com/microsoft/graphrag.git /tmp/graphrag

# Copy dependency parser script - keep in the same location as original
COPY parse_deps.py /tmp/parse_deps.py

# Parse dependencies and install them
RUN conda run -n graphrag python /tmp/parse_deps.py \
    && conda run -n graphrag pip install --no-cache-dir -r /tmp/graphrag-deps.txt \
    && conda run -n graphrag pip install --no-cache-dir --no-deps graphrag==2.1.0 \
    && rm -rf /tmp/graphrag \
    && conda clean -afy --all \
    && conda run -n graphrag pip cache purge

# Copy requirements and install remaining packages
COPY requirements.txt .
RUN grep -v "graphrag" requirements.txt > requirements_no_graphrag.txt \
    && conda run -n graphrag pip install --no-cache-dir -r requirements_no_graphrag.txt \
    && rm requirements_no_graphrag.txt \
    && conda run -n graphrag pip cache purge

# Copy all application files to ensure nothing is missing
COPY . .

# Create necessary directories that might be expected by the application
RUN mkdir -p logs debug_logs input output

EXPOSE 20213

# Use conda environment for running the application
CMD ["conda", "run", "-n", "graphrag", "uvicorn", "webserver.main:app", "--host", "0.0.0.0", "--port", "20213"]
