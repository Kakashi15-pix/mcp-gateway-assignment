FROM node:22.23.4-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:stable-alpine

ENV GATEWAY_UPSTREAM=gateway:9000
ENV GATEWAY_UPSTREAM=gateway:9000
ENV DNS_RESOLVER=127.0.0.11
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 8080
