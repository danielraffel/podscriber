# Start from a minimal base image since UV will manage Python and dependencies
FROM alpine:latest

# Set environment variables
ENV CHROMADB_DB_PATH=/home/chroma_db

# Clone the podcast-archive repository and set the working directory
WORKDIR /home

# Install necessary tools like git and curl
RUN apk add --no-cache git curl

# Clone the podcast-archive GitHub repository
RUN git clone https://github.com/danielraffel/podcast-archive.git

# Change to the podcast-archive directory
WORKDIR /home/podcast-archive

# Install UV and sync project dependencies
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && uv sync

# Expose port 8000 for FastAPI
EXPOSE 8000

# Start the FastAPI app using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]