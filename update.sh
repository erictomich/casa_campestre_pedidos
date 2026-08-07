#!/bin/bash
# Atualiza o projeto na VPS: puxa o codigo mais novo do Git e reconstroi o container.
# Uso (na VPS, dentro da pasta do projeto):
#   ./update.sh
set -e

echo "==> Puxando mudanças do Git..."
git pull

echo "==> Reconstruindo e subindo o container..."
docker compose up -d --build

echo "==> Pronto! Últimas linhas do log:"
docker compose logs --tail=30
