FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TASK_ENV_BIND=0.0.0.0 \
    TASK_ENV_PORT=9022 \
    TASK_ENV_RUNTIME_DIR=/var/lib/atlas

RUN groupadd --system atlas \
    && useradd --system --gid atlas --home-dir /app --shell /usr/sbin/nologin atlas \
    && mkdir -p /app /var/lib/atlas \
    && chown atlas:atlas /var/lib/atlas

WORKDIR /app
COPY . /app/
RUN chmod 0555 /app/setup.sh /app/generate_data.py /app/app.py \
    && chmod 0444 /app/atlas_baseline.sqlite3 /app/manifest.json /app/endpoints.txt /app/judge_api.py \
    && chmod 0444 /app/train_judge_specs.json /app/judge_answers/*.json

USER atlas:atlas
EXPOSE 9022
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('TASK_ENV_PORT','9022')+'/health',timeout=2).read()" || exit 1

ENTRYPOINT ["/app/setup.sh"]
