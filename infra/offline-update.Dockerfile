# Source-only update using an already prepared image with matching dependencies.
# This path installs nothing; use backend.Dockerfile during dependency preparation.
ARG BASE_IMAGE=chaturya-workbench:local
FROM ${BASE_IMAGE}
WORKDIR /app
COPY backend/workbench/ ./backend/workbench/
COPY config/ ./config/
COPY college-console/ ./college-console/
ENV PYTHONPATH=/app/backend WORKBENCH_PROFILE=college
