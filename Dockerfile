# Alpha: no HTTP health server; use FSAA_HEALTH_DIR file probes or HEALTHCHECK NONE.
# HEALTHCHECK NONE — operator documents external probes (file mtime on FSAA_HEALTH_DIR/live).
FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -e .
ENV WORKSPACE_ROOT=/workspace
# Copy workspace layout at runtime (automation, chat.py, AIOS_Luna_Aria) — mount volumes in production.
CMD ["fsaa", "validate-policy"]
