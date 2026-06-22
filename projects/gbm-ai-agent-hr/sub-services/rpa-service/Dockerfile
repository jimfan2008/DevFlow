FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir     fastapi==0.109.0     uvicorn==0.27.0     playwright==1.41.0     kafka-python==2.0.2     python-dotenv==1.0.1     requests==2.31.0

RUN playwright install chromium

COPY sub-services/rpa-service/src/ ./src/
COPY sub-services/rpa-service/requirements.txt ./

EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3   CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8090/health')" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8090"]
