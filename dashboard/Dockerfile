FROM python:3.11-slim
WORKDIR /app
COPY dashboard/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY communication/ ./communication/
COPY analytics/ ./analytics/
COPY database/ ./database/
COPY dashboard/ ./
CMD ["python", "server.py"]
