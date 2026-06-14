# syntax=docker/dockerfile:1

FROM node:22-slim AS build

WORKDIR /app
COPY package.json package-lock.json ./
COPY .npmrc ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.29-alpine
COPY --from=build /app/dist/smart-trade-frontend/browser /usr/share/nginx/html
EXPOSE 80
