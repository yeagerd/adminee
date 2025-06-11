# 1. Base image
FROM node:18-alpine AS base

# 2. Set working directory
WORKDIR /app

# 3. Copy package files and install dependencies
COPY frontend/package.json ./
COPY frontend/package-lock.json ./
RUN npm install

# 4. Copy the rest of the frontend application code
COPY frontend/ ./

# 5. Build the Next.js application
RUN npm run build

# 6. Expose port 3000
EXPOSE 3000

# 7. Define the command to start the application
CMD ["npm", "start"]
