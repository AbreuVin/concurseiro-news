FROM python:3.12-slim

WORKDIR /app

# Dependências de sistema necessárias para compilar pacotes nativos
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pré-baixa o modelo de embedding durante o build
# Evita download no startup e garante que o container funcione offline
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# Copia o código-fonte
COPY . .

# Cria diretório de dados (será sobrescrito pelo volume em produção)
RUN mkdir -p db/parent_docs

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
