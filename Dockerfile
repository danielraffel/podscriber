# Use the recommended Python base image with slim build
FROM python:3.12-slim-bookworm

# Set environment variables
ENV CHROMADB_DB_PATH=/app/chroma_db
ENV PATH="/root/.cargo/bin:$PATH"

# Install necessary system dependencies, including openssh-client
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Create an application directory inside the container
WORKDIR /app

# Clone the GitHub repository without a key
RUN git clone https://github.com/danielraffel/podcast-archive.git \
    && echo "GitHub repository cloned successfully." || echo "Failed to clone GitHub repository."
    
# Verify repository contents
RUN ls -alh /app/podcast-archive || echo "Repository not found!"

# Change to the podcast-archive directory
WORKDIR /app/podcast-archive

# Verify the current working directory
RUN echo "Current working directory: $(pwd)"

# Check for pyproject.toml
RUN ls -alh pyproject.toml || echo "pyproject.toml not found!"

# Install UV and verify installation
RUN curl -LsSf https://astral.sh/uv/install.sh -o /uv-installer.sh \
    && sh /uv-installer.sh \
    && rm /uv-installer.sh \
    && uv --version && echo "UV installed successfully!" || echo "UV installation failed!"

# Run uv sync and check for errors
RUN uv sync && echo "uv sync succeeded!" || echo "uv sync failed!"

# Check where Python packages are installed by uv sync
RUN ls -alh /app/podcast-archive/.venv || echo "Virtual environment not found!"
RUN ls -alh /app/podcast-archive/.venv/bin || echo "Bin directory not found!"

# Add virtual environment's bin directory to PATH
ENV PATH="/app/podcast-archive/.venv/bin:$PATH"

# Verify uvicorn installation
RUN which uvicorn && echo "uvicorn installed successfully!" || echo "uvicorn not found in PATH"

# As a backup, explicitly install uvicorn if not installed
RUN pip install --no-cache-dir uvicorn

# Expose port 8000 for FastAPI
EXPOSE 8000

# Start the FastAPI app using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]