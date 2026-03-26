# XAU/USD Trading Platform - Local Development Targets

.PHONY: build-all build-ingest build-ai build-notify build-orchestrator build-frontend deploy-local apply-argocd

IMAGE_TAG ?= local

build-all: build-ingest build-ai build-notify build-orchestrator build-frontend

build-ingest:
	docker build -t xau-data-ingest:$(IMAGE_TAG) services/data-ingest

build-ai:
	docker build -t xau-ai-analyzer:$(IMAGE_TAG) services/ai-analyzer

build-notify:
	docker build -t xau-notification:$(IMAGE_TAG) services/notification

build-orchestrator:
	docker build -t xau-orchestrator:$(IMAGE_TAG) services/orchestrator

build-frontend:
	docker build -t xau-frontend:$(IMAGE_TAG) frontend

# Requires local kubeconfig context pointing to Docker Desktop
deploy-local: build-all
	kubectl apply -k k8s/local # Applies the Kustomize overlay directly if ArgoCD is bypassed

apply-argocd:
	kubectl apply -f k8s/local/argocd-app-local.yaml

port-forward-frontend:
	kubectl port-forward svc/frontend 3000:80 -n exness-trading
