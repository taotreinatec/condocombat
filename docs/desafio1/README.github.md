# 🏗️ Desafio 1 — CI/CD da Landing Page (CondoCombat)

## 🎯 Objetivo

Criar uma pipeline de **Integração Contínua (CI)** e **Deploy Contínuo (CD)** para a **Landing Page** do CondoCombat (Astro + TailwindCSS).

A pipeline deve:
1. Executar testes automatizados (`vitest`)
2. Fazer o build do projeto (`astro build`)
3. Fazer o deploy na Netlify via **CLI oficial** com token

Pipeline configurada para **GitHub Actions**.

---

## 📦 Sobre o Projeto

### Landing Page (`landing/`)

| Item | Detalhe |
|------|---------|
| Framework | Astro 5 + TailwindCSS 3 |
| Pasta de build | `dist/` |
| Testes | Vitest |
| Comando build | `npm run build` → `astro build` |
| Comando teste | `npm test` → `vitest run` |
| Porta dev | `localhost:4321` |

```bash
# Instalar dependências
npm install

# Rodar testes
npm test

# Build local
npm run build

# Preview do build
npm run preview
```

---

## ✅ Passo a Passo

### Passo 1 — Pré-requisitos

- [ ] Conta na [Netlify](https://app.netlify.com/signup)
- [ ] Repositório no [GitHub](https://github.com)
- [ ] Netlify CLI instalada (opcional, para testes locais):
  ```bash
  npm install -g netlify-cli
  ```

---

### Passo 2 — Criar Site na Netlify

Antes de configurar a pipeline, é necessário ter um site criado na Netlify. Existem duas formas:

#### Opção A — Via Dashboard (recomendado para iniciantes)

1. Acesse [app.netlify.com/drop](https://app.netlify.com/drop)
2. Arraste a pasta `dist/` do seu projeto para a área de upload (pode ser uma pasta vazia por enquanto)
3. O site será criado automaticamente com uma URL aleatória (ex: `brave-curie-a1b2c3.netlify.app`)
4. Clique em **"Project configuration"** no menu lateral
5. Vá em **"Change project name"** e renomeie para algo significativo (ex: `condocombat-landing`)
6. Copie o **Project ID** (UUID)

#### Opção B — Via CLI

```bash
# Instalar Netlify CLI (se ainda não tiver)
npm install -g netlify-cli

# Login na Netlify
netlify login

# Criar novo site
netlify sites:create --name condocombat-landing

# O comando retorna o Site ID — anote-o!
```

> 💡 Após criar o site, você terá o **Site ID** (UUID) e o **nome do site** (slug). Ambos serão usados nos secrets do GitHub.

---

### Passo 3 — Criar arquivo `netlify.toml`

Crie `landing/netlify.toml` na raiz da landing page:

```toml
[build]
  command = "npm run build"
  publish = "dist"

[build.environment]
  NODE_VERSION = "20"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

> ℹ️ Informa à Netlify qual comando executar e qual pasta publicar. Ajuda na consistência entre deploys locais e via pipeline.

---

### Passo 4 — Configurar Secrets no GitHub

Vá em **Settings → Secrets and variables → Actions** e adicione:

| Secret | Onde conseguir |
|--------|----------------|
| `NETLIFY_AUTH_TOKEN` | Netlify → User Settings → Applications → Personal access tokens → New access token |
| `NETLIFY_SITE_ID` | Netlify → Site configuration → General → Site ID (UUID) |
| `NETLIFY_SITE_NAME` | Netlify → Site configuration → General → Site name (slug) |

**Como gerar `NETLIFY_AUTH_TOKEN`:**
1. Acesse [app.netlify.com](https://app.netlify.com)
2. User Settings (foto canto superior) → Applications
3. Personal access tokens → New access token
4. Nome: `ci-cd-condocombat` → copie o token
5. Adicione como secret `NETLIFY_AUTH_TOKEN`

**Como obter `NETLIFY_SITE_ID`:**
1. No Netlify, selecione o site no dashboard
2. Vá em **Site configuration** → **General**
3. Copie o **Site ID** (ex: `12345678-9abc-def0-1234-56789abcdef0`)
4. Adicione como secret `NETLIFY_SITE_ID`

> 💡 Pode criar o site manualmente pelo dashboard ou via CLI: `netlify sites:create`

---

### Passo 5 — Criar Workflow GitHub Actions

Crie o diretório `.github/workflows/` na **raiz do repositório** (não dentro de `landing/`) e adicione `deploy-landing.yml`:

```yaml
name: Deploy Landing Page

on:
  push:
    branches: [main, master]
    paths:
      - 'landing/**'
      - '.github/workflows/deploy-landing.yml'
  workflow_dispatch:

env:
  NODE_VERSION: '20'

jobs:
  ci:
    name: CI — Test & Build
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ./landing

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: ./landing/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test

      - name: Build
        run: npm run build

      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: landing-dist
          path: landing/dist/

  cd:
    name: CD — Deploy to Netlify
    needs: ci
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}

      - name: Download build artifact
        uses: actions/download-artifact@v4
        with:
          name: landing-dist
          path: landing/dist/

      - name: Install Netlify CLI
        run: npm install -g netlify-cli

      - name: Deploy to Netlify
        run: |
          netlify deploy \
            --dir=landing/dist \
            --prod \
            --auth=${{ secrets.NETLIFY_AUTH_TOKEN }} \
            --site=${{ secrets.NETLIFY_SITE_ID }}
```

**Explicação dos jobs:**

| Job | Responsabilidade |
|-----|------------------|
| `ci` | Instalar deps → rodar testes → build → salvar artefato |
| `cd` | Baixar artefato → instalar CLI → deploy na Netlify |

O job `cd` só executa se o `ci` passar (`needs: ci`).

**Gatilhos (`on.push.paths`):**
- `landing/**` — qualquer arquivo da landing page
- `.github/workflows/deploy-landing.yml` — o próprio workflow

Isso evita rodar a pipeline quando outras partes do monorepo (backend, frontend) são alteradas.

---

### Passo 6 — Validar Localmente Antes de Subir

```bash
# 1. Testes
cd landing && npm test

# 2. Build
npm run build

# 3. Testar deploy (draft) localmente com a CLI
netlify deploy --dir=dist --auth=$NETLIFY_AUTH_TOKEN --site=$NETLIFY_SITE_ID

# 4. Se o draft estiver OK, faça o deploy para produção
netlify deploy --dir=dist --prod --auth=$NETLIFY_AUTH_TOKEN --site=$NETLIFY_SITE_ID

# 5. (Opcional) Simular a pipeline completo localmente com act
#    https://github.com/nektos/act
act --job ci --container-architecture linux/amd64
```

---

### Passo 7 — Commit e Push

```bash
git add .
git commit -m "feat: add CI/CD pipeline for landing page"
git push origin main
```

A pipeline será disparada automaticamente. Acompanhe em **Actions** no GitHub.

---

### Passo 8 — Verificar Deploy

Após a pipeline concluir:
1. Acesse a URL do site: `https://{site-name}.netlify.app`
2. Confirme que a landing page carrega corretamente
3. Configure domínio personalizado depois, se desejar (Netlify → Domain settings)

---

## ✅ Critérios de Avaliação

| Critério | Peso | Descrição |
|----------|------|-----------|
| Testes passando na pipeline | 25% | `vitest run` executa sem erros |
| Build concluído com sucesso | 20% | `astro build` gera a pasta `dist/` |
| Deploy publicado na Netlify | 30% | Site acessível via URL pública |
| Pipeline automatizada (CI/CD) | 15% | Pipeline roda sozinha no push para `main` |
| Organização e clareza do código | 10% | YAML limpo, boas práticas, secrets bem configurados |

---

## 💡 Dicas Importantes

1. **Monorepo**: O CondoCombat tem `landing/`, `frontend/`, `backend/`. Use `paths` no GitHub Actions para focar apenas na landing.
2. **Netlify CLI**: Instale como dev dependency (`npm install -D netlify-cli`) para versão fixa no `package.json`.
3. **Teste em draft primeiro**: Faça deploy sem `--prod` para verificar antes de publicar.
4. **Logs**: Se falhar, verifique logs da pipeline (GitHub Actions) e da Netlify (Deploys → clicar no deploy com problema).
5. **URL do site**: Após deploy, disponível em `https://{site-name}.netlify.app`.

---

## 📚 Referências

- [Netlify CLI — Comando deploy](https://github.com/netlify/cli/blob/main/docs/commands/deploy.md)
- [GitHub Actions — Documentação](https://docs.github.com/en/actions)
- [act — Execute GitHub Actions localmente](https://github.com/nektos/act)
- [Astro — Guia de deploy na Netlify](https://docs.astro.build/en/guides/deploy/netlify/)
- [CondoCombat — Landing Page](../../landing/)