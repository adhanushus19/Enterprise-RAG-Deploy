# Deployment Guide: Enterprise AI Knowledge Assistant

This guide outlines deployment strategies for containerized production execution of the RAG Platform across Kubernetes, Helm, and major Cloud providers.

---

## 1. Cloud Infrastructure Architecture

We recommend running the backend and frontend as container services, backed by managed PostgreSQL (RDS/Cloud SQL) and managed Qdrant Cloud (or containerized Qdrant with persistent volumes).

### Ingress & Traffic Management
- Place both services behind an Application Load Balancer (ALB) or Ingress Controller.
- Expose the Streamlit frontend (`8501`) to public/VPN subnets.
- Retain the FastAPI backend (`8000`) inside private subnets, accessible only from the frontend container and internal VPC subnets.

---

## 2. Kubernetes Deployment Guidelines

To deploy the platform onto a Kubernetes cluster (e.g., EKS, GKE, AKS), we provide a standard manifest under [infrastructure/k8s/deployment.yaml](file:///e:/sample_webpage/infrastructure/k8s/deployment.yaml).

### Manifest Configuration Details
The configuration provisions:
1. **Namespace:** Isolates the RAG stack (`enterprise-rag`).
2. **ConfigMaps:** Stores configuration keys (`QDRANT_HOST`, `QDRANT_PORT`, etc.).
3. **Deployments:** Runs backend and frontend instances.
   - Restricts CPU/Memory bounds (limits and requests) to protect node stability.
   - Enforces execution under unprivileged UIDs (`10001` for backend, `10002` for frontend).
   - Configures liveness/readiness health probes pointing to `/health`.
4. **Services:** Exposes backend ClusterIP and frontend NodePort/LoadBalancer.
5. **Horizontal Pod Autoscaling (HPA):** Dynamically scales pod count based on CPU usage.

### Execution Steps
1. Configure your Kubernetes context:
   ```bash
   kubectl config use-context <your-cluster-context>
   ```
2. Create Secrets for OpenAI API and DB Credentials:
   ```bash
   kubectl create secret generic rag-secrets \
     --namespace=enterprise-rag \
     --from-literal=OPENAI_API_KEY="sk-proj-yourkey" \
     --from-literal=DATABASE_URL="postgresql://postgres:pass@db-host:5432/rag" \
     --from-literal=API_KEY="enterprise-secret-123"
   ```
3. Apply the deployment manifest:
   ```bash
   kubectl apply -f infrastructure/k8s/deployment.yaml
   ```

---

## 3. Helm Integration

For template-driven cloud deployments, you can wrap these manifests into a Helm chart. A typical `values.yaml` configuration should define:

```yaml
replicaCount: 2

image:
  backend:
    repository: <your-ecr-repo>/backend
    tag: "latest"
    pullPolicy: IfNotPresent
  frontend:
    repository: <your-ecr-repo>/frontend
    tag: "latest"
    pullPolicy: IfNotPresent

resources:
  limits:
    cpu: 1000m
    memory: 1024Mi
  requests:
    cpu: 200m
    memory: 256Mi

securityContext:
  runAsNonRoot: true
  runAsUser: 10001
```

Install using Helm:
```bash
helm upgrade --install enterprise-rag ./charts/enterprise-rag -f values.yaml --namespace enterprise-rag
```

---

## 4. Redis Fallback Caching

To optimize token utilization and decrease latency:
- Swapping the in-memory rate-limiter dictionary for **Redis** is recommended in production.
- Define a `REDIS_URL` env variable in ConfigMaps.
- In `backend/app/main.py`, substitute the local bucket dictionary with a Redis Client connection:
  ```python
  import redis
  redis_client = redis.Redis.from_url(settings.REDIS_URL)
  ```
- Use Redis hash sets with an expiration TTL matching your rate limit windows.
