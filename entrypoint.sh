#!/bin/bash
set -e

TABLE="${TABLE_NAME:-doe_ba}"

# Na primeira execução o índice não existe — roda o pipeline antes de subir o bot
if [ ! -d "/app/db/${TABLE}.lance" ]; then
    echo "[Entrypoint] Indice nao encontrado. Executando pipeline inicial..."
    python -m src.etl.pipeline
fi

exec python main.py
