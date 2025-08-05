FROM node:20 AS build
 
WORKDIR /app
 
COPY package*.json ./
RUN npm install
 
COPY . .
RUN npm run build -- --configuration=production

# Add this line to debug
RUN ls -la /app/dist/

FROM nginx:alpine
RUN rm -rf /usr/share/nginx/html/*

# Try different paths based on your Angular version
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html
# OR try: COPY --from=build /app/dist/frontend /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
