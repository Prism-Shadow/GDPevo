FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TASK_ENV_BIND=0.0.0.0 \
    TASK_ENV_PORT=9023

WORKDIR /opt/observatory
COPY . /opt/observatory
RUN chmod 755 setup.sh \
    && python3 generate_data.py --output generated/observatory.sqlite \
    && python3 generate_data.py --check --output generated/observatory.sqlite \
    && useradd --system --uid 10001 --home /opt/observatory observatory \
    && chown -R observatory:observatory /opt/observatory

USER observatory
EXPOSE 9023
ENTRYPOINT ["./setup.sh"]
