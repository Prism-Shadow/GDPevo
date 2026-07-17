FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TASK_ENV_BIND=0.0.0.0 \
    TASK_ENV_PORT=9024 \
    TASK_ENV_ENABLE_JUDGE=0

WORKDIR /opt/engineering-ops
COPY . /opt/engineering-ops/

RUN python3 /opt/engineering-ops/generate_data.py >/dev/null \
    && python3 -c "import server; assert len(server.DATA['work_items']) > 0" \
    && chmod 0555 /opt/engineering-ops/setup.sh \
    && find /opt/engineering-ops -type f ! -name setup.sh -exec chmod 0444 {} + \
    && useradd --system --uid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin engineeringops \
    && chown -R engineeringops:engineeringops /opt/engineering-ops

USER 10001:10001
EXPOSE 9024

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD python3 -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('TASK_ENV_PORT','9024')+'/health',timeout=2).read()"

ENTRYPOINT ["/opt/engineering-ops/setup.sh"]
