FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8003

WORKDIR /app
RUN useradd --create-home --uid 10001 appuser
COPY requirements-wc.txt .
RUN pip install --no-cache-dir --requirement requirements-wc.txt
COPY wc-server.py .
USER appuser

EXPOSE 8003
CMD ["python", "wc-server.py"]
