FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8001

WORKDIR /app
RUN useradd --create-home --uid 10001 appuser
COPY requirements-k8s.txt .
RUN pip install --no-cache-dir --requirement requirements-k8s.txt
COPY k8s-server.py .
USER appuser

EXPOSE 8001
CMD ["python", "k8s-server.py"]
