FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TASK_ENV_BIND=0.0.0.0
ENV TASK_ENV_PORT=9020

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x setup.sh && python generate_data.py

EXPOSE 9020

CMD ["./setup.sh"]
