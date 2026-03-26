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

install-argocd:
	@kubectl get namespace argocd > /dev/null 2>&1 || kubectl create namespace argocd
	@kubectl get crd applications.argoproj.io > /dev/null 2>&1 || (kubectl apply -n argocd --server-side -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml && echo "Waiting for ArgoCD CRDs to settle..." && sleep 5)

# Requires local kubeconfig context pointing to Docker Desktop
deploy-local: build-all install-argocd
	kubectl apply -f k8s/local/argocd-app-local.yaml
	kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'
	@echo "Waiting for frontend service to be created by ArgoCD..."
	@while ! kubectl get svc frontend -n exness-trading > /dev/null 2>&1; do sleep 2; done
	kubectl port-forward svc/frontend 3000:80 -n exness-trading

apply-argocd:
	kubectl apply -f k8s/local/argocd-app-local.yaml

port-forward-frontend:
	kubectl port-forward svc/frontend 3000:80 -n exness-trading
