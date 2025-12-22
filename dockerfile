FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get install -y postgresql-client && apt-get clean
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install psycopg2-binary alembic

COPY . .

EXPOSE 8000
