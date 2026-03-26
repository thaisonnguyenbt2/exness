# XAU/USD Platform

A complete microservices-based, Kubernetes-orchestrated, AI-powered trading analytical platform for the XAU/USD gold market.

## Architecture

This platform leverages 5 distinct microservices to generate high-confidence trading signals:

1. **Data Ingestion Service** (`services/data-ingest`): Connects to the Finnhub WebSocket to stream real-time price ticks. Builds OHLCV candlesticks (M1, M5, M15, M30, H1) and calculates technical indicators (RSI, MACD, Bollinger Bands, EMA, ADX) using `pandas-ta`. 
2. **AI Analyzer Service** (`services/ai-analyzer`): Subscribes to candlestick feeds via Redis. Throttles analysis requests and sends massive blocks of market context to Google's **Gemini 1.5 Flash** AI model. The AI returns strictly-typed JSON forecasting market movements with dynamic confidence ratings.
3. **Orchestrator Service** (`services/orchestrator`): A Python FastAPI and Celery backend. Evaluates newly generated AI signals, translates them into "Paper Trades," and actively simulates Stop-Loss and Take-Profit ledger hits dynamically without risking actual capital. 
4. **Notification Service** (`services/notification`): A Node.js daemon that formats AI signals into gorgeous human-readable markdown messages and dispatches them via the Telegram messaging API (with strict rate limit caching to prevent alert fatigue).
5. **Frontend Dashboard** (`frontend`): A responsive full-stack **Next.js 14** React application visualizing live WebSockets metrics natively via `recharts` onto a Candlestick DOM. Monitors trade ledgers and AI statuses in real-time.

## Tech Stack
* **Languages**: Python 3.12, Node.js 20, TypeScript, WebSockets.
* **Storage**: MongoDB (Timeseries ticks & document store), Redis (Pub/Sub message bus).
* **Infrastructure**: Kubernetes, Nginx Ingress, ArgoCD, Docker Compose, GitHub Actions.

---

## Getting Started

### Prerequisites
* Docker & Docker Desktop installed.
* Kubernetes cluster enabled inside Docker Desktop.
* Make installed locally.

### 1. Environment Setup
You will need to provide API keys. Create a `.env` file at the root or configure your Kubernetes secrets for the platform containers.
Required API keys:
- `FINNHUB_API_KEY`: Real-time WebSockets
- `GEMINI_API_KEY`: Google's AI Studio inference
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: Dispatching alerts

### 2. Running Locally (Docker Desktop + Kubernetes)

The platform is designed to run locally using Kustomize overlays mapped to the Docker Desktop cluster. This workflow builds the docker images straight into your local cache so the platform boots instantly without needing a heavy cloud-registry pipeline.

```bash
# Compile and tag all 5 Microservice Docker images directly to your local daemon cache
make build-all

# Apply the local Kustomize overlay directly to Docker Desktop Kubernetes
make deploy-local

# Forward the Nginx LoadBalancer or Frontend Service port exactly to localhost
make port-forward-frontend
```
*You can now open your browser to `http://localhost:3000` to view the Dashboard!*

---

### Alternative: GitOps via local ArgoCD

If you prefer to visualize the microservices scaling via an ArgoCD dashboard mapping back to your Git Repository:
```bash
# 1. Ensure images are built locally
make build-all

# 2. Add the GitOps Local Tracking Application to ArgoCD
# (Make sure to update the repoURL in k8s/local/argocd-app-local.yaml first!)
make apply-argocd
```

### Alternative: Raw Docker Compose
For testing components separately outside of the K8s ecosystem using raw bridging:
```bash
docker network create trading-net
docker run -d --name redis --net trading-net redis:7-alpine
docker run -d --name mongodb --net trading-net mongo:6

docker build -t xau-data-ingest services/data-ingest
docker run -d --net trading-net --env-file .env.local -p 8080:8080 xau-data-ingest
```

### Build a service alone
```
docker compose up --build -d ai-analyzer
```