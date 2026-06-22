FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir     fastapi==0.109.0     uvicorn==0.27.0     paddlepaddle==2.6.0     paddleocr==2.7.0.4     kafka-python==2.0.2     python-dotenv==1.0.1     pillow==10.2.0

COPY sub-services/ocr-service/src/ ./src/

EXPOSE 8091

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3   CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8091/health')" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8091"]
