FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TASK_ENV_BIND=0.0.0.0 \
    TASK_ENV_PORT=9018 \
    TASK_ENV_ENABLE_JUDGE=0

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir flask==3.0.3 && \
    chmod +x /app/setup.sh && \
    python3 /app/generate_data.py

EXPOSE 9018

CMD ["/app/setup.sh"]
