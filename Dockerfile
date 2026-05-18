FROM python:3.12.7-slim AS builder

WORKDIR /app

COPY pyproject.toml requirements.txt* ./
RUN pip install --no-cache-dir -e ".[dev]" \
    && if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

COPY backend/ ./backend/
COPY .env* ./

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM builder AS runtime

RUN pip install --no-cache-dir gunicorn

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
