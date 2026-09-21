# Frontend Dockerfile
# Docker build command : cd diamond/frontend &&
# docker build --secret id=frontend_build_env,src=.env.build \
#   -t diamond_frontend:0.1.0 .
# Docker run command : docker run --env-file .env -p 3000:3000 diamond_frontend:0.1.0

FROM node:24.21.0-alpine AS base
RUN corepack enable && corepack prepare pnpm@12.3.4 --activate

FROM base AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --ignore-scripts

FROM base AS builder
WORKDIR /app
ARG FLASK_URL
ARG NEXT_PUBLIC_GLOBUS_CLIENT_ID
# Both are NEXT_PUBLIC_/build-time values Next.js inlines into the client
# bundle -- a runtime ECS env var can't supply them after the fact, so they
# must be passed as --build-arg and rebuilt whenever they change.
RUN [ -n "$FLASK_URL" ] || { echo "ERROR: Missing required env_var: FLASK_URL"; exit 1; }
RUN [ -n "$NEXT_PUBLIC_GLOBUS_CLIENT_ID" ] || { echo "ERROR: Missing required env_var: NEXT_PUBLIC_GLOBUS_CLIENT_ID"; exit 1; }
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build

FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --prod --frozen-lockfile --ignore-scripts

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.ts ./

EXPOSE 3000

CMD ["pnpm", "start"]