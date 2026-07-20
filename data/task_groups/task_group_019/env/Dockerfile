FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TASK_ENV_BIND=0.0.0.0
ENV TASK_ENV_PORT=9019

WORKDIR /app

RUN pip install --no-cache-dir Flask==3.0.3

COPY . /app

RUN chmod +x /app/setup.sh && python3 /app/generate_data.py

EXPOSE 9019

ENTRYPOINT ["/app/setup.sh"]
