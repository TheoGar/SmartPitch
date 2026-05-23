FROM python:3.11-slim
WORKDIR /app
RUN mkdir -p /app/data
COPY analytics/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY communication/ ./communication/
COPY database/ ./database/
COPY analytics/ ./
CMD ["python", "main.py"]
