FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TASK_ENV_BIND=0.0.0.0
ENV TASK_ENV_PORT=9024

WORKDIR /app
COPY . /app
RUN chmod +x /app/setup.sh /app/generate_data.py /app/app.py

EXPOSE 9024
CMD ["/app/setup.sh"]
