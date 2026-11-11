# Stage 1: build the React frontend
FROM node:24-slim AS web
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: FastAPI backend that also serves frontend/dist
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt backend/
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY seed/ seed/
COPY --from=web /app/frontend/dist frontend/dist
ENV DATA_DIR=/app/data
WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
