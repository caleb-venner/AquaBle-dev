# Multi-stage build for Home Assistant add-on
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.13-alpine3.21

FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend
COPY ../frontend/package*.json ./
RUN npm ci
COPY ../frontend/ ./
RUN npm run build

# Main add-on image
FROM ${BUILD_FROM}

# Copy frontend build artifacts
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Copy Python source code
COPY ../src /app/src
COPY ../pyproject.toml /app/

# Install Python dependencies
RUN pip3 install --no-cache-dir -e .

# Copy S6 service configuration
COPY rootfs/ /

# Set environment variables
ENV PYTHONPATH=/app/src
ENV AQUA_BLE_FRONTEND_DIST=/app/frontend/dist

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1