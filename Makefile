# XAU/USD Trading Platform - Local Development Targets

.PHONY: build-all build-ingest build-ai build-notify build-orchestrator build-frontend deploy-local apply-argocd install-argocd dev stop-dev stop-local update-local release-local release-prod deploy-oracle login-oracle

dev:
	docker compose up --build

stop-dev:
	docker compose down

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
	@echo "Waiting for frontend pods to be ready..."
	@kubectl wait --for=condition=available deployment/frontend -n exness-trading --timeout=120s
	kubectl port-forward svc/frontend 3000:80 -n exness-trading

stop-local:
	kubectl delete -f k8s/local/argocd-app-local.yaml
	@echo "Local Kubernetes deployment (ArgoCD app) has been stopped."

update-local: build-all
	kubectl rollout restart deployment -n exness-trading
	@echo "Local images rebuilt and Kubernetes pods meticulously restarted with the newest code."

release-local:
	$(eval NEW_TAG := local-$(shell date +%Y%m%d%H%M%S))
	@echo "🚀 Initiating local Release Pipeline with unique tag: $(NEW_TAG)"
	$(MAKE) build-all IMAGE_TAG=$(NEW_TAG)
	@echo "Updating kustomization.yaml overlays to target new tag..."
	@awk '{gsub(/newTag: .*/, "newTag: $(NEW_TAG)"); print}' k8s/local/kustomization.yaml > k8s/local/kustomization.tmp && mv k8s/local/kustomization.tmp k8s/local/kustomization.yaml
	@echo "✅ Images successfully built and k8s/local/kustomization.yaml updated!"
	@echo "You can now safely commit these files to GitHub. ArgoCD will naturally detect the tag shift and roll out the deployments seamlessly."

release-prod:
	$(eval NEW_TAG := prod-$(shell date +%Y%m%d%H%M%S))
	@echo "🚀 Initiating PRODUCTION Release Pipeline with tag: $(NEW_TAG)"
	$(MAKE) build-all IMAGE_TAG=$(NEW_TAG)
	@echo "Tagging images for Oracle Cloud Registry (OCI)..."
	docker tag xau-data-ingest:$(NEW_TAG) ocir.io/tenancy/data-ingest:$(NEW_TAG)
	docker tag xau-ai-analyzer:$(NEW_TAG) ocir.io/tenancy/ai-analyzer:$(NEW_TAG)
	docker tag xau-notification:$(NEW_TAG) ocir.io/tenancy/notification:$(NEW_TAG)
	docker tag xau-orchestrator:$(NEW_TAG) ocir.io/tenancy/orchestrator:$(NEW_TAG)
	docker tag xau-frontend:$(NEW_TAG) ocir.io/tenancy/frontend:$(NEW_TAG)
	@echo "Pushing images to Oracle Cloud Registry..."
	docker push ocir.io/tenancy/data-ingest:$(NEW_TAG) || echo "Warning: Push failed. Ensure you are logged into OCIR."
	docker push ocir.io/tenancy/ai-analyzer:$(NEW_TAG) || true
	docker push ocir.io/tenancy/notification:$(NEW_TAG) || true
	docker push ocir.io/tenancy/orchestrator:$(NEW_TAG) || true
	docker push ocir.io/tenancy/frontend:$(NEW_TAG) || true
	@echo "Updating k8s/base/kustomization.yaml base manifests to target new production tag..."
	@awk '{gsub(/newTag: .*/, "newTag: $(NEW_TAG)"); print}' k8s/base/kustomization.yaml > k8s/base/kustomization.tmp && mv k8s/base/kustomization.tmp k8s/base/kustomization.yaml
	@echo "✅ Production Images processed and k8s/base updated!"
	@echo "Commit these changes to GitHub. ArgoCD in Oracle Cloud will automatically rollout the new pipeline."

apply-argocd:
	kubectl apply -f k8s/local/argocd-app-local.yaml

port-forward-frontend:
	kubectl port-forward svc/frontend 3000:80 -n exness-trading

# --- Oracle Cloud Deployment Variables ---
OCI_COMPARTMENT_ID ?= ocid1.tenancy.oc1..aaaaaaaaff4o35xfzgmq34zkq5vemqx6otahtjemr54yu5am6drh2x7d3nyq
OCI_SUBNET_ID ?= ocid1.subnet.oc1.ap-singapore-1.aaaaaaaarsogtewxonrijwxo4p4lod2cttutk5hu4ysxmrarckd25faem7yq
OCI_IMAGE_ID ?= ocid1.image.oc1..xxxx
OCI_AD ?= Uocm:US-ASHBURN-AD-1
SSH_PUB_KEY ?= ~/.ssh/id_rsa.pub

deploy-oracle:
	@echo "🚀 Launching Oracle Cloud Compute Instance with Automated GitOps Pipeline..."
	oci compute instance launch \
		--display-name "exness-trading-node" \
		--compartment-id "$(OCI_COMPARTMENT_ID)" \
		--availability-domain "$(OCI_AD)" \
		--shape "VM.Standard.A1.Flex" \
		--shape-config '{"ocpus": 4, "memoryInGBs": 24}' \
		--subnet-id "$(OCI_SUBNET_ID)" \
		--image-id "$(OCI_IMAGE_ID)" \
		--ssh-authorized-keys-file "$(SSH_PUB_KEY)" \
		--user-data-file ./cloud-init.yaml \
		--assign-public-ip true
	@echo "✅ Instance provisioning started! Tailscale and ArgoCD will be available in ~5 minutes."

login-oracle:
	@export PATH="$$PATH:$$HOME/bin"; \
	echo "🔍 Querying Oracle Cloud for Public IP of 'exness-trading-node'..."; \
	INSTANCE_OCID=$$(oci compute instance list --compartment-id "$(OCI_COMPARTMENT_ID)" --display-name "exness-trading-node" --query "data[0].id" --raw-output) && \
	if [ -z "$$INSTANCE_OCID" ] || [ "$$INSTANCE_OCID" = "null" ]; then \
		echo "❌ Cannot find instance. Are you sure it was deployed in this compartment?"; exit 1; \
	fi && \
	INSTANCE_IP=$$(oci compute instance list-vnics --instance-id "$$INSTANCE_OCID" --query "data[0].\"public-ip\"" --raw-output) && \
	echo "✅ Found Public IP: $$INSTANCE_IP" && \
	echo "🔑 Initializing SSH connection..." && \
	ssh -o StrictHostKeyChecking=no -i $$(echo "$(SSH_PUB_KEY)" | sed 's/\.pub//') ubuntu@$$INSTANCE_IP
