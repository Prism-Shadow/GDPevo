FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TASK_ENV_BIND=0.0.0.0
ENV TASK_ENV_PORT=9009

WORKDIR /app
COPY . /app
RUN chmod +x /app/setup.sh && find /app/judge_train_eval -name '*.sh' -exec chmod +x {} + && python3 /app/generate_data.py >/tmp/task_group_009_generate_data.log

EXPOSE 9009
ENTRYPOINT ["/app/setup.sh"]
