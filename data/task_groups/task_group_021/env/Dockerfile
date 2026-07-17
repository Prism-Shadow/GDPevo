FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TASK_ENV_BIND=0.0.0.0 \
    TASK_ENV_PORT=9021 \
    TASK_ENV_ENABLE_JUDGE=0

WORKDIR /opt/asteria
COPY . /opt/asteria/

RUN mkdir -p /opt/asteria/data \
    && python /opt/asteria/generate_data.py \
        --output /opt/asteria/data/asteria_quality.db \
        --manifest /opt/asteria/manifest.json \
        --truth /opt/asteria/construction_truth.json \
    && python /opt/asteria/generate_data.py \
        --verify \
        --output /opt/asteria/data/asteria_quality.db \
        --manifest /opt/asteria/manifest.json \
        --truth /opt/asteria/construction_truth.json \
    && chmod 0555 /opt/asteria/setup.sh \
    && chmod 0444 /opt/asteria/data/asteria_quality.db /opt/asteria/manifest.json /opt/asteria/construction_truth.json /opt/asteria/judge_specs.json \
    && find /opt/asteria/judge_tasks -type f -exec chmod 0444 {} + \
    && useradd --system --uid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin asteria \
    && chown -R asteria:asteria /opt/asteria

USER 10001:10001
EXPOSE 9021

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('TASK_ENV_PORT','9021')+'/health',timeout=2).read()"

ENTRYPOINT ["/opt/asteria/setup.sh"]
