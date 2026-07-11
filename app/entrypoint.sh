#!/bin/sh

echo "Применяем миграции..."
cd /app/app && alembic upgrade head

echo "Запускаем FastAPI..."
uvicorn main:app --host 0.0.0.0 --port 8000