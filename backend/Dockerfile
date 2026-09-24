FROM python:3.13-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/app /app/app
COPY web /web
COPY config /config

EXPOSE 8000
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
