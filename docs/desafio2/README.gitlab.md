# 🏗️ Desafio 2 — Docker + CI/CD do Backend e Frontend (CondoCombat)

## 🎯 Objetivo

Criar **Dockerfiles** e um **docker-compose.yml** para o backend (FastAPI) e frontend (Next.js) do CondoCombat, e configurar **3 arquivos de pipeline** de **Integração Contínua (CI)** no GitLab CI/CD que executam lint, testes, build e push das imagens para o **DockerHub**.

As pipelines devem:

1. **Pipeline do Backend** (`.gitlab-ci/backend.yml`): Executar lint (Ruff) → testes (pytest) → build Docker → push DockerHub
2. **Pipeline do Frontend** (`.gitlab-ci/frontend.yml`): Executar lint (ESLint) → testes (Vitest) → build Docker → push DockerHub
3. **Arquivo principal** (`.gitlab-ci.yml`): Incluir os dois pipelines com `include:` e filtrar por `rules:changes`
4. **Rodar localmente** com Docker Compose usando as imagens publicadas

Pipelines configuradas como **arquivos separados** no GitLab CI/CD.

---

## 📦 Sobre o Projeto

### Backend (FastAPI)

| Item | Detalhe |
|------|---------|
| Framework | FastAPI + SQLAlchemy Async + Pydantic v2 |
| Porta | 8000 |
| Testes | pytest (216 testes) |
| Lint | Ruff |
| Banco | PostgreSQL 16 (asyncpg) |
| Comando dev | `uvicorn app.main:app --reload` |
| Comando teste | `pytest` |
| Comando lint | `ruff check app/` |
| Dockerfile | Multi-stage (deps → runtime) |
| Entrypoint | `entrypoint.sh` (valida SECRET_KEY + alembic upgrade head) |

### Frontend (Next.js)

| Item | Detalhe |
|------|---------|
| Framework | Next.js 14 (App Router) + TailwindCSS + shadcn/ui |
| Porta | 3000 |
| Testes | Vitest (79 testes) |
| Lint | ESLint |
| Build | `npm run build` (output: standalone) |
| Dockerfile | Multi-stage (deps → builder → runner) |

---

## ✅ Passo a Passo

### Passo 1 — Pré-requisitos

- [ ] Conta no [Docker Hub](https://hub.docker.com/signup)
- [ ] Repositório no [GitLab](https://gitlab.com) ou GitLab self-hosted
- [ ] Docker instalado localmente
- [ ] `docker-compose` instalado (v2+)
- [ ] Python 3.12+ e Node.js 20+ (para testes locais)

---

### Passo 2 — Criar Dockerfile do Backend

Crie `backend/Dockerfile` com **multi-stage build** (2 estágios):

```dockerfile
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
```

---

### Passo 3 — Criar Entrypoint do Backend

Crie `backend/entrypoint.sh`:

```bash
#!/bin/bash
set -e

# Valida SECRET_KEY obrigatória
if [ -z "$SECRET_KEY" ]; then
    echo "❌ ERRO: SECRET_KEY não está definida!"
    echo "   Gere uma com: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
    exit 1
fi

echo "🔧 Rodando migrations do Alembic..."
alembic upgrade head

echo "🚀 Iniciando servidor FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

> ⚠️ **Importante**: Dê permissão de execução: `chmod +x backend/entrypoint.sh`

---

### Passo 4 — Criar Dockerfile do Frontend

Crie `frontend/Dockerfile` com **multi-stage build** (3 estágios):

```dockerfile
# =============================================================================
# Stage 1: Dependencies — instala node_modules
# =============================================================================
FROM node:20-alpine AS deps

WORKDIR /app

# Copia apenas os arquivos de dependências (aproveita cache)
COPY package.json package-lock.json ./

# Instala dependências exatas do lockfile
RUN npm ci

# =============================================================================
# Stage 2: Builder — compila a aplicação
# =============================================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Copia dependências do stage deps
COPY --from=deps /app/node_modules ./node_modules

# Copia código fonte
COPY . .

# Build da aplicação Next.js
RUN npm run build

# =============================================================================
# Stage 3: Runner — imagem de produção
# =============================================================================
FROM node:20-alpine AS runner

WORKDIR /app

# Instala dependências de runtime (mínimas)
RUN npm add next@latest

# Cria usuário não-root
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copia arquivos buildados
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Troca para usuário não-root
USER nextjs

# Expõe porta e health check
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Inicia servidor Next.js
CMD ["node", "server.js"]
```

> 💡 **Nota**: O Next.js deve ter `output: 'standalone'` no `next.config.js` para funcionar com este Dockerfile.

---

### Passo 5 — Criar docker-compose.yml

Crie `docker-compose.yml` na **raiz do projeto**:

```yaml
# =============================================================================
# CondoCombat — Docker Compose (Backend + Frontend + Database)
# =============================================================================
version: '3.8'

services:
  # PostgreSQL Database
  db:
    image: postgres:16-alpine
    container_name: condocombat-db
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-condocombat}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-condocombat}
      POSTGRES_DB: ${POSTGRES_DB:-condocombat}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-condocombat}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Backend API (FastAPI)
  api:
    image: your-dockerhub-username/condocombat-backend:latest
    container_name: condocombat-api
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-condocombat}:${POSTGRES_PASSWORD:-condocombat}@db:5432/${POSTGRES_DB:-condocombat}
      SECRET_KEY: ${SECRET_KEY}
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  # Frontend (Next.js)
  web:
    image: your-dockerhub-username/condocombat-frontend:latest
    container_name: condocombat-web
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - api
    restart: unless-stopped

volumes:
  pgdata:
    driver: local
```

> 🔑 Substitua `your-dockerhub-username` pelo seu username do Docker Hub.

---

### Passo 6 — Criar Arquivo Principal `.gitlab-ci.yml`

Crie `.gitlab-ci.yml` na **raiz do repositório**:

```yaml
# =============================================================================
# CondoCombat — Pipeline Principal (Inclui Backend + Frontend)
# =============================================================================

stages:
  - lint
  - test
  - build

# Inclui pipelines modulares
include:
  - local: '.gitlab-ci/backend.yml'
  - local: '.gitlab-ci/frontend.yml'

# Variáveis globais
variables:
  DOCKER_DRIVER: overlay2
  DOCKER_TLS_CERTDIR: ""
```

---

### Passo 7 — Criar Pipeline do Backend

Crie o diretório `.gitlab-ci/` e dentro dele o arquivo `backend.yml`:

```yaml
# =============================================================================
# Pipeline do Backend — Lint → Test → Build → Push
# =============================================================================
stages:
  - lint
  - test
  - build

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

# ---------------------------------------------------------------------------
# Lint — Ruff
# ---------------------------------------------------------------------------
lint:
  stage: lint
  image: python:3.12-slim
  cache:
    key: backend-pip
    paths:
      - .cache/pip
  before_script:
    - pip install ruff
  script:
    - cd backend
    - ruff check app/
  rules:
    - changes:
        - backend/**/*

# ---------------------------------------------------------------------------
# Test — pytest
# ---------------------------------------------------------------------------
test:
  stage: test
  image: python:3.12-slim
  cache:
    key: backend-pip
    paths:
      - .cache/pip
  before_script:
    - pip install -r backend/requirements.txt
  script:
    - cd backend
    - pytest
  variables:
    SECRET_KEY: $SECRET_KEY
  rules:
    - changes:
        - backend/**/*

# ---------------------------------------------------------------------------
# Build — Docker image → Push to DockerHub
# ---------------------------------------------------------------------------
build:
  stage: build
  image: docker:27
  services:
    - docker:dind
  variables:
    DOCKER_TLS_CERTDIR: ""
  before_script:
    - docker login -u $DOCKERHUB_USERNAME -p $DOCKERHUB_TOKEN
  script:
    - docker build -t $DOCKERHUB_USERNAME/condocombat-backend:latest ./backend
    - docker push $DOCKERHUB_USERNAME/condocombat-backend:latest
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
      changes:
        - backend/**/*
```

---

### Passo 8 — Criar Pipeline do Frontend

Crie o arquivo `.gitlab-ci/frontend.yml`:

```yaml
# =============================================================================
# Pipeline do Frontend — Lint → Test → Build → Push
# =============================================================================
stages:
  - lint
  - test
  - build

variables:
  npm_config_cache: "$CI_PROJECT_DIR/.npm"

cache:
  key: frontend-npm
  paths:
    - .npm

# ---------------------------------------------------------------------------
# Lint — ESLint
# ---------------------------------------------------------------------------
lint:
  stage: lint
  image: node:20-alpine
  before_script:
    - cd frontend
    - npm ci
  script:
    - cd frontend
    - npm run lint
  rules:
    - changes:
        - frontend/**/*

# ---------------------------------------------------------------------------
# Test — Vitest
# ---------------------------------------------------------------------------
test:
  stage: test
  image: node:20-alpine
  before_script:
    - cd frontend
    - npm ci
  script:
    - cd frontend
    - npm test
  rules:
    - changes:
        - frontend/**/*

# ---------------------------------------------------------------------------
# Build — Docker image → Push to DockerHub
# ---------------------------------------------------------------------------
build:
  stage: build
  image: docker:27
  services:
    - docker:dind
  variables:
    DOCKER_TLS_CERTDIR: ""
  before_script:
    - docker login -u $DOCKERHUB_USERNAME -p $DOCKERHUB_TOKEN
  script:
    - docker build -t $DOCKERHUB_USERNAME/condocombat-frontend:latest ./frontend
    - docker push $DOCKERHUB_USERNAME/condocombat-frontend:latest
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
      changes:
        - frontend/**/*
```

---

### Passo 9 — Configurar Variáveis no GitLab

Vá em **Settings → CI/CD → Variables** e adicione:

| Variável | Valor | Masked | Protected | Descrição |
|----------|-------|--------|-----------|-----------|
| `DOCKERHUB_USERNAME` | seu-usuario-dockerhub | ❌ | ❌ | Username do Docker Hub |
| `DOCKERHUB_TOKEN` | token-de-acesso-do-dockerhub | ✅ | ✅ | Access Token do Docker Hub (Settings → Security → Access Tokens) |
| `SECRET_KEY` | chave-secreta-32-chars | ✅ | ✅ | Gere com: `python -c 'import secrets; print(secrets.token_urlsafe(32))'` |
| `POSTGRES_USER` | condocombat | ❌ | ❌ | Usuário do banco (padrão) |
| `POSTGRES_PASSWORD` | condocombat | ✅ | ✅ | Senha do banco |
| `POSTGRES_DB` | condocombat | ❌ | ❌ | Nome do banco |

**Como gerar token do Docker Hub:**
1. Acesse [hub.docker.com](https://hub.docker.com) → Account Settings → Security → New Access Token
2. Nome: `gitlab-ci-condocombat` → Permissão: `Read & Write`
3. Copie o token e adicione como `DOCKERHUB_TOKEN` (marque **Masked**)

**Como gerar `SECRET_KEY`:**
```bash
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

---

### Passo 10 — Commit e Push

```bash
git add .
git commit -m "feat: add Dockerfiles, docker-compose and GitLab CI/CD pipelines"
git push origin main
```

As pipelines serão disparadas automaticamente. Acompanhe em **CI/CD → Pipelines** no GitLab.

---

### Passo 11 — Verificar Pipeline e Imagens

Após a pipeline concluir:
1. No GitLab: **CI/CD → Pipelines** → verifique se todos os stages passaram (lint → test → build)
2. No Docker Hub: acesse seu perfil → Repositories → confirme as imagens:
   - `seu-usuario/condocombat-backend:latest`
   - `seu-usuario/condocombat-frontend:latest`
3. Teste o docker-compose com as imagens publicadas:
   ```bash
   # Atualize o docker-compose.yml com seu username
   docker compose pull
   docker compose up -d
   ```

---

### Passo 12 — Validar Docker-Compose

```bash
# 1. Subir stack completa
docker compose up -d

# 2. Verificar saúde dos containers
docker compose ps
docker compose logs -f api

# 3. Testar endpoints
curl http://localhost:8000/health    # Backend
curl http://localhost:3000           # Frontend

# 4. Parar e limpar
docker compose down -v
```

---

## ✅ Critérios de Avaliação

| Critério | Peso | Descrição |
|----------|------|-----------|
| Dockerfiles multi-stage corretos | 20% | Backend (2 stages) + Frontend (3 stages) com cache otimizado |
| docker-compose.yml funcional | 15% | 3 serviços (db, api, web) com health checks e dependências |
| Pipeline Backend (lint→test→build→push) | 20% | Executa na branch main, só em mudanças em `backend/**` |
| Pipeline Frontend (lint→test→build→push) | 20% | Executa na branch main, só em mudanças em `frontend/**` |
| Pipeline principal com include + rules:changes | 15% | `.gitlab-ci.yml` inclui os 2 arquivos e filtra corretamente |
| Variáveis CI/CD configuradas no GitLab | 10% | DOCKERHUB_USERNAME, DOCKERHUB_TOKEN, SECRET_KEY, etc. |

---

## 💡 Dicas Importantes

1. **Monorepo**: Use `rules:changes` em cada job para rodar apenas quando a pasta correspondente mudar (`backend/**/*` ou `frontend/**/*`).
2. **Cache Docker**: A ordem das instruções no Dockerfile importa. Coloque `COPY requirements.txt` / `COPY package.json package-lock.json` **antes** do código fonte.
3. **Cache pip/npm**: As pipelines configuram `PIP_CACHE_DIR` e `npm_config_cache` — isso acelera execuções subsequentes.
4. **Variáveis Protegidas**: Marque `DOCKERHUB_TOKEN` e `SECRET_KEY` como **Masked**. Se `main` for protected branch, marque também como **Protected**.
5. **Health checks**: Todos os containers têm health checks. O backend usa `condition: service_healthy` no `depends_on` para aguardar o banco.
6. **SECRET_KEY**: Obrigatória no backend. Se não definida, o container crasha no entrypoint com `ValueError`.
7. **Sem Deploy**: A pipeline termina no push para o DockerHub. Deploy em produção é etapa separada (não obrigatória neste desafio).

---

## 📚 Referências

- [Docker — Multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
- [GitLab CI/CD — Include keyword](https://docs.gitlab.com/ee/ci/yaml/include.html)
- [GitLab CI/CD — Rules:changes](https://docs.gitlab.com/ee/ci/yaml/jobs_job_rules.html#ruleschanges)
- [GitLab CI/CD — Cache](https://docs.gitlab.com/ee/ci/caching/)
- [Docker Hub — Access Tokens](https://docs.docker.com/security/for-developers/access-tokens/)
- [FastAPI — Docker](https://fastapi.tiangolo.com/deployment/docker/)
- [Next.js — Docker](https://nextjs.org/docs/app/building-your-application/deploying/docker)
- [CondoCombat — Backend](../../backend/)
- [CondoCombat — Frontend](../../frontend/)