FROM node:24-alpine AS build

RUN npm install -g pnpm@12.6.0

WORKDIR /app

COPY package.json pnpm-lock.yaml ./

RUN pnpm install --frozen-lockfile

COPY . .

# Dev login screen; off in production builds.
ARG VITE_DEV_AUTH=false
ENV VITE_DEV_AUTH=$VITE_DEV_AUTH

RUN pnpm build

FROM caddy:2-alpine

COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv

EXPOSE 80
