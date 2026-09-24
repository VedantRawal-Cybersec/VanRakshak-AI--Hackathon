FROM python:3.13-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY backend/requirements.txt /app/requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/app /app/app
COPY web /web
COPY config /config

RUN useradd --system --create-home --home-dir /home/vanrakshak --shell /usr/sbin/nologin vanrakshak \
    && chown -R vanrakshak:vanrakshak /app /web /config
USER vanrakshak

EXPOSE 8000
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
