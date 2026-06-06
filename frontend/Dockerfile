# Use official Node.js image
FROM node:20-alpine

# Set the working directory
WORKDIR /app

# Copy package.json and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the frontend code
COPY . .

# Expose Vite's default port
EXPOSE 5173

# Run Vite and expose it to the network (--host is required for Docker)
CMD ["npm", "run", "dev", "--", "--host"]