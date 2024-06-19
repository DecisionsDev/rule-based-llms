# Chatbot Frontend

## Prerequisites

1. Install Node 20+

## Getting started

The first time, you need to install the necessary JavaScript components for the application:
```sh
npm install
```

Running in development mode:

```sh
npm run dev
```

Build bundle for production:

```sh
npm run build
```

Preview production build:

```sh
npm run preview
```

Running linter:

```sh
# Check
npm run lint
# Fix
npm run lint:fix
```

## Running in docker

Build image:

```sh
docker build . --build-arg API_URL=http://localhost:9000 -t nginx-app -m 4g 
```

Run image:

```sh
docker run -p 8080:80 nginx-app
```
