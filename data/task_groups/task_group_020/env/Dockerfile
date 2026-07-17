FROM python:3.11-slim

WORKDIR /env
COPY . /env/

RUN chmod +x setup.sh && \
    find train_tasks -path '*/eval/*.sh' -exec chmod +x {} \;

ENV TASK_ENV_BIND=0.0.0.0
ENV TASK_ENV_PORT=9020
ENV TASK_ENV_ENABLE_JUDGE=0

EXPOSE 9020
CMD ["bash", "setup.sh"]
