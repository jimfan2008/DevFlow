FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir     fastapi==0.109.0     uvicorn==0.27.0     insightface==0.3.0     onnxruntime==1.17.1     kafka-python==2.0.2     python-dotenv==1.0.1     numpy==1.26.2     pillow==10.2.0

COPY sub-services/face-service/src/ ./src/

EXPOSE 8092

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3   CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8092/health')" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8092"]
