# Vite dev server for local/full-stack Docker (hot reload).
FROM node:22-alpine

WORKDIR /app

# Install dependencies first for better layer caching.
COPY package.json package-lock.json ./
RUN npm ci

# Source is also bind-mounted in compose for hot reload.
COPY . .

EXPOSE 5173

# --host 0.0.0.0 comes from package.json "dev" script.
CMD ["npm", "run", "dev"]
