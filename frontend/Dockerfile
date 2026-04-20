FROM node:20-alpine

WORKDIR /app
# Install dependencies (dev deps needed for `npm run dev` / Vite)
COPY package.json package-lock.json* ./
RUN npm install --legacy-peer-deps

# Copy project files (during development we'll usually mount the host source)
COPY . .

# Run the dev server on all interfaces so the container is reachable from host
EXPOSE 80
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "80"]
