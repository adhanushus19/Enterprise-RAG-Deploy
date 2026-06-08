# Security Considerations: Enterprise AI Knowledge Assistant

This document outlines the security controls implemented to protect the RAG platform and corporate intellectual property.

---

## 1. Threat Modeling & Controls

| Threat Vector | Description | Implemented Mitigation |
| :--- | :--- | :--- |
| **Unauthorized Access** | Unauthenticated users invoking query endpoints, exposing sensitive company files. | Enforced header-based authentication `X-API-Key` on all FastAPI routes. |
| **API Denial of Service** | Attackers flooding inference endpoints, inflating OpenAI API token costs. | Custom IP-based rate-limiting middleware restricting traffic to 60 requests/min. |
| **Path Traversal / Ingress** | Malicious file uploads (e.g. `../../etc/passwd`) targeting server filesystem. | File path sanitization via `os.path.basename` extraction and isolated target folders. |
| **Large-file OOM Attacks** | Attackers uploading huge files to exhaust server memory during parsing. | Enforces strict **10MB** maximum file upload limit on the API gateway level. |
| **Data Leakage (LLM)** | Sensitive documents transmitted to external LLM providers for training. | Configured prompts and API calls to opt-out of data sharing (Enterprise OpenAI API models do not train on customer data). |

---

## 2. Secure File Ingestion

### Extension Validation
- Upload endpoints strictly whitelist only standard extensions: `pdf`, `docx`, `pptx`, `xlsx`.
- Filenames are sanitized on ingress to block directory traversal or escape characters.

### Upload Limits
- The FastAPI gateway reads a maximum of `10MB + 1` bytes before validating the payload size.
- If the content length exceeds `10MB`, it raises a `413 Payload Too Large` error and terminates the connection before processing, preventing memory exhaustion.

### Thread Isolation
- Physical files are saved with unique timestamp prefixes.
- Parsers run as background tasks outside the primary HTTP request loop to prevent system thread blocks.

---

## 3. Container Hardening

### Non-Root Users
The Docker files are hardened to prevent escalation exploits:
- **Backend Container:** Runs under unprivileged user `appuser` (UID `10001`, GID `10001`).
- **Frontend Container:** Runs under unprivileged user `appuser` (UID `10002`, GID `10002`).
- Both containers isolate application source files from root-level directories.

### Volumes and Permissions
- The uploads mount directory is explicitly owned by user `10001` or `10002` to prevent write/read permissions issues.

---

## 4. Secret Management

- Secrets (e.g., `OPENAI_API_KEY`, `DATABASE_URL`) are loaded dynamically via Pydantic settings.
- No raw secrets are stored in git repositories or docker images.
- In production, secrets are injected as environment variables via cloud secrets managers (e.g., AWS Secrets Manager, Azure Key Vault, or Kubernetes Secrets).
