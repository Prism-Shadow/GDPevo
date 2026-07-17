FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TASK_ENV_BIND=0.0.0.0
ENV TASK_ENV_PORT=9014

WORKDIR /app
COPY . /app

RUN chmod +x /app/setup.sh && python3 /app/generate_data.py >/tmp/payer_ops_generate_data.log

EXPOSE 9014
ENTRYPOINT ["/app/setup.sh"]
