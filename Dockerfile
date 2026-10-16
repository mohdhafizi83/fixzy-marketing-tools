# Fixzy Marketing Tools — production image
# Data lives in /data (sqlite). Mount a volume there; see docker-compose.yml.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as unprivileged user; sqlite DB lives on the /data volume.
RUN useradd -r -u 10001 fixzy && mkdir -p /data && chown fixzy:fixzy /data
USER fixzy

# Default DB location (override with DATABASE_URL in .env if you like).
ENV DATABASE_URL=sqlite:////data/fixzy.db

EXPOSE 5558

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:5558/healthz', timeout=4)" || exit 1

CMD ["python", "app.py"]
