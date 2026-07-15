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