# 🏗️ Desafio 1 — CI/CD da Landing Page (CondoCombat)

## 🎯 Objetivo

Criar uma pipeline de **Integração Contínua (CI)** e **Deploy Contínuo (CD)** para a **Landing Page** do CondoCombat (Astro + TailwindCSS) usando **GitLab CI/CD**.

A pipeline deve:
1. Executar testes automatizados (`vitest`)
2. Fazer o build do projeto (`astro build`)
3. Fazer o deploy na Netlify via **CLI oficial** com token

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
- [ ] Repositório no [GitLab](https://gitlab.com)
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

> 💡 Após criar o site, você terá o **Site ID** (UUID) e o **nome do site** (slug). Ambos serão usados nas variáveis do GitLab.

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

### Passo 4 — Configurar Variáveis no GitLab

Vá em **Settings → CI/CD → Variables** e adicione:

| Variável | Descrição | Onde conseguir | Masked |
|----------|-----------|----------------|--------|
| `NETLIFY_AUTH_TOKEN` | Token de autenticação da Netlify | Netlify → User Settings → Applications → Personal access tokens | ✅ Sim |
| `NETLIFY_SITE_ID` | ID do site na Netlify (UUID) | Netlify → Site configuration → General → Site ID | ✅ Sim |
| `NETLIFY_SITE_NAME` | Nome do site (slug) | Netlify → Site configuration → General → Site name | ❌ Não |

**Como gerar `NETLIFY_AUTH_TOKEN`:**
1. Acesse [app.netlify.com](https://app.netlify.com)
2. User Settings (foto canto superior) → Applications
3. Personal access tokens → New access token
4. Nome: `ci-cd-condocombat` → copie o token
5. Adicione como variável `NETLIFY_AUTH_TOKEN` (marque **Masked**)

**Como obter `NETLIFY_SITE_ID`:**
1. No Netlify, selecione o site no dashboard
2. Vá em **Site configuration** → **General**
3. Copie o **Site ID** (ex: `12345678-9abc-def0-1234-56789abcdef0`)
4. Adicione como variável `NETLIFY_SITE_ID` (marque **Masked**)

> 💡 Pode criar o site manualmente pelo dashboard ou via CLI: `netlify sites:create`

---

### Passo 5 — Criar Pipeline `.gitlab-ci.yml`

Crie o arquivo `.gitlab-ci.yml` na **raiz do repositório**:

```yaml
image: node:20

variables:
  NODE_VERSION: "20"

cache:
  key:
    files:
      - landing/package-lock.json
  paths:
    - landing/node_modules/

stages:
  - test
  - build
  - deploy

test-landing:
  stage: test
  script:
    - cd landing
    - npm ci
    - npm test
  artifacts:
    expire_in: 1 hour
    paths:
      - landing/node_modules/

build-landing:
  stage: build
  script:
    - cd landing
    - npm ci
    - npm run build
  artifacts:
    expire_in: 1 hour
    paths:
      - landing/dist/
  needs:
    - test-landing

deploy-landing:
  stage: deploy
  image: node:20
  script:
    - npm install -g netlify-cli
    - netlify deploy --dir=landing/dist --prod --auth=$NETLIFY_AUTH_TOKEN --site=$NETLIFY_SITE_ID
  needs:
    - build-landing
  only:
    - main
    - master
  environment:
    name: production
    url: https://$NETLIFY_SITE_NAME.netlify.app
```

**Explicação dos stages:**

| Stage | Descrição |
|-------|-----------|
| `test` | Instala deps e executa os testes do Vitest |
| `build` | Faz o build com `astro build` → gera `dist/` |
| `deploy` | Instala Netlify CLI e faz deploy para produção |

O `needs` garante a ordem: **test → build → deploy**.

**Configuração de Environment:**
- O `environment.url` com `https://$NETLIFY_SITE_NAME.netlify.app` faz o GitLab mostrar link direto para o site nos pipelines.

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
```

---

### Passo 7 — Commit e Push

```bash
git add .
git commit -m "feat: add CI/CD pipeline for landing page"
git push origin main
```

A pipeline será disparada automaticamente. Acompanhe em **CI/CD → Pipelines** no GitLab.

---

### Passo 8 — Verificar Deploy

Após a pipeline concluir:
1. Acesse a URL do site: `https://{site-name}.netlify.app`
2. Confirme que a landing page carrega corretamente
3. No GitLab, o pipeline mostrará um botão "Visit site" graças ao `environment.url`
4. Configure domínio personalizado depois, se desejar (Netlify → Domain settings)

---

## ✅ Critérios de Avaliação

| Critério | Peso | Descrição |
|----------|------|-----------|
| Testes passando na pipeline | 25% | `vitest run` executa sem erros |
| Build concluído com sucesso | 20% | `astro build` gera a pasta `dist/` |
| Deploy publicado na Netlify | 30% | Site acessível via URL pública |
| Pipeline automatizada (CI/CD) | 15% | Pipeline roda sozinha no push para `main` |
| Organização e clareza do código | 10% | YAML limpo, boas práticas, variáveis bem configuradas |

---

## 💡 Dicas Importantes

1. **Monorepo**: O CondoCombat tem `landing/`, `frontend/`, `backend/`. Use `only:changes` no GitLab CI/CD para focar apenas na landing:
   ```yaml
   only:
     changes:
       - landing/**/*
       - .gitlab-ci.yml
   ```
2. **Netlify CLI**: Instale como dev dependency (`npm install -D netlify-cli`) para versão fixa no `package.json`.
3. **Teste em draft primeiro**: Faça deploy sem `--prod` para verificar antes de publicar.
4. **Logs**: Se falhar, verifique logs da pipeline (GitLab CI/CD) e da Netlify (Deploys → clicar no deploy com problema).
5. **URL do site**: Após deploy, disponível em `https://{site-name}.netlify.app`.

---

## 📚 Referências

- [Netlify CLI — Comando deploy](https://github.com/netlify/cli/blob/main/docs/commands/deploy.md)
- [GitLab CI/CD — Documentação](https://docs.gitlab.com/ee/ci/)
- [Astro — Guia de deploy na Netlify](https://docs.astro.build/en/guides/deploy/netlify/)
- [CondoCombat — Landing Page](../../landing/)