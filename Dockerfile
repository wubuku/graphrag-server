FROM continuumio/miniconda3:latest

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Set BLIS architecture for ARM64
ENV BLIS_ARCH=generic

RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libpython3-dev \
    pkg-config \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create conda environment with Python 3.10 (same as local)
RUN conda create -n graphrag python=3.10 -y && \
    echo "source activate graphrag" >> ~/.bashrc

# Install base dependencies using conda with numpy 1.26.4 for graspologic compatibility
RUN conda install -n graphrag -c conda-forge -y \
    "numpy=1.26.4" \
    cython \
    && conda clean -afy

# Install spaCy 3.8.3 (available version)
# Note: We're using spaCy 3.8.3 instead of 3.8.4 because:
# 1. GraphRAG depends on spaCy >=3.8.4, but this version may not be available for ARM64
# 2. We'll install GraphRAG with --no-deps to bypass the version check
# 3. spaCy 3.8.3 is functionally compatible and available for our architecture
RUN conda run -n graphrag pip install spacy==3.8.3 && \
    conda run -n graphrag python -m spacy download en_core_web_sm

# Clone GraphRAG repo
RUN git clone --depth 1 https://github.com/microsoft/graphrag.git /tmp/graphrag

# Install tomli for parsing TOML files
RUN conda install -n graphrag -c conda-forge tomli -y && \
    conda clean -afy

# Use external Python script to parse dependencies
COPY parse_deps.py /tmp/parse_deps.py
RUN conda run -n graphrag python /tmp/parse_deps.py && \
    conda run -n graphrag pip install -r /tmp/graphrag-deps.txt

# Install GraphRAG with --no-deps flag
RUN conda run -n graphrag pip install --no-deps graphrag==2.1.0

# Copy and install requirements except graphrag
COPY requirements.txt .
RUN grep -v "graphrag" requirements.txt > requirements_no_graphrag.txt && \
    conda run -n graphrag pip install --no-cache-dir -r requirements_no_graphrag.txt

COPY . .

EXPOSE 20213

# Use conda environment for running the application
CMD ["conda", "run", "-n", "graphrag", "uvicorn", "webserver.main:app", "--host", "0.0.0.0", "--port", "20213"]
