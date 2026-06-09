FROM python:3.11-slim

WORKDIR /app

# Copy the entire project
COPY . .

# Install uv for dependency management
RUN pip install uv && uv sync --frozen

# Create data directory for persistent storage
RUN mkdir -p /data

# Expose MCP HTTP port (default 8080 for SSE)
EXPOSE 8080

# Environment variables
ENV DEVFLOW_HOME=/data
ENV MCP_TRANSPORT=sse
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8080

# Entry point
CMD ["uv", "run", "python", "-m", "devflow_mcp"]