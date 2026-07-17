FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TASK_ENV_BIND=0.0.0.0 \
    TASK_ENV_PORT=9016 \
    TASK_ENV_DB=/app/generated/clinic.sqlite3

WORKDIR /app
COPY . /app

RUN chmod +x /app/setup.sh && mkdir -p /app/generated

EXPOSE 9016

CMD ["/app/setup.sh"]
