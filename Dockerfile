# ana — engine image (Streamlit UI). Python pinned, non-root user, model cache outside the image.
FROM python:3.12-slim

# libgomp1 is needed by torch/sentence-transformers at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first so this layer is cached across code-only changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

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