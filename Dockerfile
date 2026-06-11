FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r services/awr-api/requirements.txt

WORKDIR /app/services/awr-api

CMD uvicorn main:app --host 0.0.0.0 --port $PORT

==========================


aidbaassistant-api-production.up.railway.app

https://aidbaassistant-api-production.up.railway.app/health

561a82d2-7625-4d9c-8957-2b0f4f580d9e

https://aidbaassistant-api-production.up.railway.app/report/<analysis_id>/pdf

https://aidbaassistant-api-production.up.railway.app/report/561a82d2-7625-4d9c-8957-2b0f4f580d9e/pdf