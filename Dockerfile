FROM python:3.12-slim

RUN pip install --no-cache-dir requests

COPY check.py /app/check.py

# notified.json is read and written here; mount a host folder to keep it between runs
WORKDIR /data

CMD ["python", "/app/check.py"]
