# Best effort only. The supported dev setup is `cd mobile && npx expo start` on the host.
# Node 22: Expo SDK 58 requires Node ^22.13 (node:20 does not work).
FROM node:22-slim

ENV EXPO_NO_TELEMETRY=1 \
    CI=0

WORKDIR /app

COPY package.json package-lock.json .npmrc ./
RUN npm ci

COPY . .

EXPOSE 8081
CMD ["npx", "expo", "start", "--lan"]
