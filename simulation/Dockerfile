FROM python:3.11-slim
WORKDIR /app
COPY simulation/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY communication/ ./communication/
COPY simulation/ ./
CMD ["python", "main.py"]
