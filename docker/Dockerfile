# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

# System deps: libpq for psycopg2, poppler+tesseract for PDF OCR fallback.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev gcc poppler-utils tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 --retries=10 --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data/uploads /home/appuser/.cache/huggingface \
    && chown -R appuser:appuser /app /home/appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8000/health').status == 200 else sys.exit(1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
