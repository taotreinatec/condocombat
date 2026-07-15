# =============================================================================
# Stage 1: Dependencies — instala dependências Python
# =============================================================================
FROM python:3.12-slim AS deps

WORKDIR /app

# Instala sistema básico e dependências de compilação
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements e instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 2: Runtime — imagem final
# =============================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Instala dependências de runtime
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário não-root
RUN useradd --create-home --shell /bin/bash app

# Copia dependências do stage deps
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copia código fonte
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

# Copia e configura script de entrada
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Troca para usuário não-root
USER app

# Expõe porta e health check
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Entry point
ENTRYPOINT ["./entrypoint.sh"]