# ── Crescendo-Heatmap — standalone CLI container ─────────────────────────────
FROM python:3.12-slim

LABEL org.opencontainers.image.title="Crescendo-Heatmap"
LABEL org.opencontainers.image.description="Visualise multi-turn adversarial safety-score decay"
LABEL org.opencontainers.image.version="0.1.0"

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
COPY examples/ ./examples/

RUN pip install --no-cache-dir -e .

# Mount your conversation files at /data
VOLUME ["/data"]

ENTRYPOINT ["crescendo-heatmap"]
CMD ["--help"]

# ── Usage examples ────────────────────────────────────────────────────────────
# Analyse a conversation file and output heatmap HTML to current directory:
#   docker run --rm \
#     -v $(pwd):/data \
#     crescendo-heatmap \
#     --input /data/conversation.json \
#     --output /data/report.html \
#     --json /data/summary.json
#
# Use the bundled sample:
#   docker run --rm -v $(pwd):/data crescendo-heatmap \
#     --input /app/examples/sample_conversation.json \
#     --output /data/report.html
