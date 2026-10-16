# ana — engine image (Streamlit UI). Python pinned, non-root user, model cache outside the image.
# Base image pinned by digest (python:3.12-slim as of 2026-10-16); bump deliberately.
FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1

# libgomp1 is needed by torch/sentence-transformers at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first so this layer is cached across code-only changes.
# Exact versions from requirements.lock (regenerate with: uv pip compile requirements.txt -o requirements.lock
#   --python-version 3.12 --python-platform x86_64-manylinux_2_28).
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

COPY . .

# Run as a non-root user (container hardening).
RUN useradd --create-home --uid 1000 ana \
    && chown -R ana:ana /app

USER ana

# HF_HOME points inside /app so the embedding model download persists via a mounted volume.
ENV CLIENT=demo \
    HF_HOME=/app/.cache/huggingface \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]