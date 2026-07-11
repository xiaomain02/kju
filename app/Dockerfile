FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/app/

COPY app/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:////app/app/data/kanban.db

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]