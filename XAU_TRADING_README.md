# XAU/USD AI Trading Microservices Platform

A production-ready Kubernetes microservices architecture designed to collect real-time XAU/USD trading data, synthesize it into indicator candles, analyze the market continuously with Google's Gemini AI, and disseminate rich alert forecasts.

## Services Layout
- `services/data-ingest/` - Finnhub WebSockets, MongoDB metrics, Redis channels.
- `services/ai-analyzer/` - Subscribes to trades, builds AI logic, outputs JSON analysis.
- `services/notification/` - Subscribes to AI logic, throttles, dispatches rich Telegram UI.
- `frontend/` - Next.js 14 Dashboard pulling realtime charts over WebSockets.
- `k8s/` - Comprehensive Oracle Cloud standard YAML configurations.

## Bootstrapping Locally (Docker-Compose)
For testing outside of Kubernetes, simply mount the `.env` variables and rely on standard bridge networks.
```bash
docker network create trading-net
docker run -d --name redis --net trading-net redis:7-alpine
docker run -d --name mongodb --net trading-net mongo:6

# Spin up microservices pointing to the linked containers
docker build -t xau-data-ingest services/data-ingest
docker run -d --net trading-net --env-file .env.local -p 8080:8080 xau-data-ingest
```

## Bootstrapping Kubernetes (Oracle Cloud / Native K8s)
The platform is designed around GitOps principles.
1. Apply foundational constraints and state stores:
```bash
kubectl apply -f k8s/config.yaml
kubectl apply -f k8s/infra.yaml
```
2. Setup the declarative engine:
```bash
kubectl apply -f k8s/argocd-app.yaml
```
3. ArgoCD will naturally ingest the entire GitHub repository and construct the Deployments defined in `k8s/data-ingest.yaml`, `k8s/ai-notification.yaml`, and `k8s/frontend-ingress.yaml`.

## Telemetry
The core routing leverages an NGINX architecture where `trading.sandbox.local` points to the Next.js frontend on `/` and reverse-proxies directly to the `data-ingest` backend through `/api` routing rules to establish seamless WebSocket streams.

## Important Note regarding the Orchestrator
The `Orchestrator` microservice handles advanced features like Paper Trading ledgers and performance metric Celery crons. The frontend (`/trades` endpoint) has been locally mocked to assume an orchestration platform. Building out the orchestrator ledger falls outside the current scaffold but is easily implemented by subscribing to the MongoDB `trades` collection. 
