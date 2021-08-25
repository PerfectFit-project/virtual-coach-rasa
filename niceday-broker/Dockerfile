FROM node:14.16.1

WORKDIR /app

COPY . .

# Install goalie-js from cloned repository
RUN npm install ./build/goalie-js

CMD [ "npm", "start" ]
