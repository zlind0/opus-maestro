FROM node:20 as build

WORKDIR /app

COPY package.json ./

RUN npm install

COPY . .

RUN npm run build

FROM node:20

WORKDIR /app

# Copy node_modules from build stage to preserve vite and other dev dependencies
COPY --from=build /app/node_modules ./node_modules

# Copy built dist
COPY --from=build /app/dist ./dist

# Install serve globally for production serving
RUN npm install -g serve

EXPOSE 5173

CMD ["serve", "-s", "dist", "-l", "5173"]
