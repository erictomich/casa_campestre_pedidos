# Casa Campestre - imagem de producao
FROM python:3.12-slim

# Nao gerar .pyc e log sem buffer (aparece na hora no docker logs)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DATA_DIR=/app/data

WORKDIR /app

# Dependencias primeiro (aproveita o cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Codigo da aplicacao
COPY . .

# Pasta dos dados (montada como volume) - fica com pedidos.db e pedidos_backup.json
RUN mkdir -p /app/data
VOLUME ["/app/data"]

EXPOSE 8000

# gunicorn como servidor de producao.
# 1 worker + varias threads: mantem o backup JSON consistente (ele e protegido
# por um lock dentro do processo) e da conta de sobra do volume do evento.
CMD gunicorn --workers 1 --threads 8 --bind 0.0.0.0:${PORT} server:app
