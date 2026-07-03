FROM python:3.13-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
COPY agents/requirements.txt agents/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt -r agents/requirements.txt

COPY backend/ backend/
COPY agents/ agents/

ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}
