FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY eval ./eval

RUN mkdir -p /app/dados

EXPOSE 8000

CMD ["python", "-m", "src.inicializacao", "servir"]
