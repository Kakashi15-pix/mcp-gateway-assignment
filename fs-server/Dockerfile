FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8002 \
    FS_ROOT=/data

WORKDIR /app
RUN useradd --create-home --uid 10001 appuser && mkdir /data && chown appuser:appuser /data
COPY requirements-wc.txt .
RUN pip install --no-cache-dir --requirement requirements-wc.txt
COPY fs-server.py .
USER appuser

EXPOSE 8002
VOLUME ["/data"]
CMD ["python", "fs-server.py"]
