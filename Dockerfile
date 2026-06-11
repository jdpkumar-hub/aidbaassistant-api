FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r services/awr-api/requirements.txt

WORKDIR /app/services/awr-api

CMD uvicorn main:app --host 0.0.0.0 --port $PORT
