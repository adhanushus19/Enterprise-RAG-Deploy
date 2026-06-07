# Security Considerations: Enterprise AI Knowledge Assistant

This document outlines the security controls implemented to protect the RAG platform and corporate intellectual property.

---

## 1. Threat Modeling & Controls

| Threat Vector | Description | Implemented Mitigation |
| :--- | :--- | :--- |
| **Unauthorized Access** | Unauthenticated users invoking query endpoints, exposing sensitive company files. | Enforced header-based authentication `X-API-Key` on all FastAPI routes. |
| **API Denial of Service** | Attackers flooding inference endpoints, inflating OpenAI API token costs. | Custom IP-based rate-limiting middleware restricting traffic to 60 requests/min. |
| **Path Traversal / Ingress** | Malicious file uploads (e.g. `../../etc/passwd`) targeting server filesystem. | File path sanitization, type-checking, and isolated target upload folders. |
| **Data Leakage (LLM)** | Sensitive documents transmitted to external LLM providers for training. | Configured prompts and API calls to opt-out of data sharing (Enterprise OpenAI API models do not train on customer data). |

---

## 2. Secure File Ingestion

### Business Problem
Allowing employees to upload arbitrary documents can lead to server compromise (shell injections, malicious macros) or database corruption.

### Design Rationale
- **Extension Whitelisting:** We strictly permit only `pdf`, `docx`, `pptx`, and `xlsx` extensions. Any other type triggers a 400 Bad Request error.
- **Physical Isolation:** Files are renamed on disk using timestamp prefixes (e.g., `171779929_policy.pdf`) to prevent naming collisions and file overwriting.
- **Background Processing:** Ingestion tasks are executed inside a separate background thread, ensuring any parser crash does not compromise the main HTTP server request lifecycle.

---

## 3. Environment Variable & Secret Management

- **No Hardcoded Secrets:** All credentials (`DATABASE_URL`, `QDRANT_HOST`, `OPENAI_API_KEY`) are loaded dynamically using Pydantic Settings from system variables or `.env` files.
- **Docker Compose Scoping:** Production container configurations pass secrets as environment variables injected from target environments (e.g., Github Secrets, AWS Secrets Manager), keeping them out of source control.

---

## 4. Engineering Tradeoffs & Scalability
* **API Key Auth vs. OAuth2/OIDC:** We chose header-based API key validation for simplicity, performance, and compatibility with service-to-service automation. For full user-level access controls, future iterations should transition to OAuth2 with JSON Web Tokens (JWT) integrated with Okta or Azure AD.
* **Rate Limiting Storage:** The current rate limiter uses an in-memory dictionary. If scaled horizontally across multiple containers, this should be migrated to a shared **Redis** instance to enforce global limits.

---

## 5. Future Improvements
- **Document Access Control Lists (ACLs):** Extend the database schema to associate documents with user roles, ensuring retrieval only searches documents the current user is authorized to read.
- **PII Redaction:** Integrate a preprocessing node (e.g., Microsoft Presidio) to strip Personally Identifiable Information (PII) before transmitting chunks to the OpenAI API.
- **Vulnerability Scanning:** Configure GitHub Actions to execute `bandit` and `safety` scans on pull requests.
