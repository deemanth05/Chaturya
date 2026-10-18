FROM node:24-slim AS ui
WORKDIR /ui
ENV NEXT_TELEMETRY_DISABLED=1
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
# Docker CLI is used only by the fixed sandbox launcher; model-generated code never gets the socket.
RUN apt-get update && apt-get install -y --no-install-recommends docker.io && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml ./
COPY backend/workbench/ ./backend/workbench/
RUN pip install --no-cache-dir .
COPY config/ ./config/
COPY college-console/ ./college-console/
COPY --from=ui /ui/out/ ./college-console/
ENV WORKBENCH_ROOT=/app WORKBENCH_PROFILE=college WORKBENCH_DATA=/app/data HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 LANGSMITH_TRACING=false OTEL_SDK_DISABLED=true
CMD ["python", "-m", "workbench", "serve", "--host", "0.0.0.0", "--port", "8000"]

