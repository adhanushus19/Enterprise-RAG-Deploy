# Deployment Guide: Enterprise AI Knowledge Assistant

This guide outlines deployment strategies for containerized production execution of the RAG Platform across AWS, GCP, and Azure.

---

## 1. Cloud Infrastructure Architecture

We recommend running the backend and frontend as container services, backed by managed PostgreSQL (RDS/Cloud SQL) and managed Qdrant Cloud (or containerized Qdrant with persistent volumes).

### Business Problem
Enterprise environments require high availability, zero-downtime deployments, and compliance with data isolation standards. Deploying RAG systems requires managing state (PostgreSQL metadata, Qdrant vectors) and stateless services (FastAPI backend, Streamlit frontend).

### Design Rationale
We package each service into independent Docker containers configured via environment variables. This allows the backend and frontend to scale independently.

---

## 2. Platform Deployments

### A. AWS ECS (Fargate)
1. **Database:** Provision Amazon RDS PostgreSQL with multi-AZ enabled.
2. **Vector DB:** Deploy Qdrant on ECS with AWS EFS (Elastic File System) volume mounts for vector persistence, or use Qdrant Cloud.
3. **Containers:** Build and push Docker images to AWS ECR (Elastic Container Registry).
4. **ECS Service:** Define task definitions for `backend` and `frontend` using Fargate. Map secrets (e.g. `OPENAI_API_KEY`) from AWS Secrets Manager.
5. **Networking:** Place ECS services behind an Application Load Balancer (ALB) inside private subnets, allowing public ingress only to the frontend.

### B. Google Cloud Run
1. **Database:** Provision Google Cloud SQL for PostgreSQL. Enable Private IP.
2. **Vector DB:** Deploy Qdrant on GKE with a persistent disk volume, or deploy Qdrant Cloud.
3. **Containers:** Push images to Google Artifact Registry.
4. **Deploy Service:**
   ```bash
   gcloud run deploy knowledge-backend \
     --image gcr.io/project-id/backend:latest \
     --add-cloudsql-instances project-id:region:db-instance \
     --set-env-vars DATABASE_URL=postgresql://user:pass@/db?host=/cloudsql/project-id:region:db-instance \
     --vpc-connector connector-name \
     --no-allow-unauthenticated
   ```
5. Deploy `knowledge-frontend` referencing the backend URL.

### C. Azure Container Apps (ACA)
1. **Database:** Deploy Azure Database for PostgreSQL Flexible Server.
2. **Containers:** Push images to Azure Container Registry (ACR).
3. **Deploy:** Deploy backend and frontend into an Azure Container Apps Environment.
4. **Secrets Integration:** Bind Azure Key Vault to Container App environment variables.

---

## 3. Engineering Tradeoffs & Scalability

* **Fargate vs. EKS (Kubernetes):** ECS Fargate offers a lower operational overhead for standard applications. However, if the company plans to self-host custom open-source embedding models (e.g., using Triton with GPU), EKS is preferred for finer GPU slicing controls.
* **Auto-Scaling Policy:** FastAPI container scaling should be based on **CPU/Memory utilization** (scale up at 70%) combined with **Request Count per target** to handle sudden surges in file uploads.

---

## 4. Failure Scenarios & Security
- **Database Failover:** Enable Multi-AZ or High Availability flag on GCP/AWS databases. If the primary database fails, the application automatically retries connections while DNS shifts to the secondary replica.
- **Data Encryption:** Enforce TLS 1.3 for all database connections (PostgreSQL and Qdrant) and encrypt storage volumes (EBS/Cloud Disk) at rest using customer-managed keys (KMS).
- **Future Improvements:** Implement Terraform or Bicep templates in the `/infrastructure` directory to automate resource provisioning via GitOps pipelines.
