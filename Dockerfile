# Multi-stage build for EZZone
# Stage 1: Build Vue.js frontend
FROM node:20-slim AS frontend-builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source and configuration
COPY index.html vite.config.js ./
COPY frontend/ ./frontend/

# Build for production
RUN npm run build

# Stage 2: Python application with Pixi
FROM ghcr.io/prefix-dev/pixi:0.39.2 AS runtime

WORKDIR /app

# Copy pixi configuration
COPY pixi.toml pixi.lock ./

# Install dependencies with pixi (locked)
RUN pixi install --locked

# Copy application code
COPY backend/ ./backend/
COPY tests/fixtures/ ./tests/fixtures/

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/dist ./dist

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV PORT=8080

# Expose port (Railway uses PORT env var)
EXPOSE $PORT

# Run with gunicorn via pixi (shell form for variable expansion)
CMD pixi run start-prod
