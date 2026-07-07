# Security Policy

We take the security of DocuMindAI and its users seriously. This document describes our supported versions, how to report vulnerabilities responsibly, and our response commitments.

---

## ✅ Supported Versions

Only the latest release on the `main` branch receives active security updates.

| Version | Status |
|---------|--------|
| `main` (latest) | ✅ Actively supported |
| Older tags / forks | ❌ Not supported — please update to `main` |

If you are running a custom fork or an older release, we strongly recommend pulling the latest changes from upstream before reporting a vulnerability.

---

## 🔒 Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub Issues, Discussions, or Pull Requests.**

Public disclosure before a fix is available puts all DocuMindAI users at risk.

### How to Report

Send a private email to:

> **security@documindai.com**
> *(or contact the repository maintainer directly via GitHub private message)*

### What to Include

To help us triage and reproduce the issue quickly, please provide:

1. **Vulnerability description** — What is the weakness? What can an attacker do?
2. **Affected component(s)** — e.g., authentication, document upload, OCR pipeline, admin API
3. **Severity assessment** — your estimate of CVSS or impact (Low / Medium / High / Critical)
4. **Steps to reproduce** — a minimal, numbered reproduction path
5. **Proof of concept** — a script, screenshot, or request payload if available
6. **Environment** — self-hosted Docker, Railway, or other deployment type
7. **Your contact details** — so we can coordinate disclosure

Encryption is welcome. Contact us first and we will provide a PGP key if needed.

---

## ⏱️ Response Timeline

We commit to the following response SLA:

| Milestone | Target |
|-----------|--------|
| **Acknowledge receipt** | Within **48 hours** |
| **Initial triage & severity assessment** | Within **7 days** |
| **Fix & coordinated disclosure** | Within **30 days** for High/Critical |
| **Public CVE disclosure** | After fix is released and users have had time to update |

We will keep you informed of progress throughout the process. If we need more time due to complexity, we will communicate that proactively.

---

## 🎯 Security Scope

### In Scope

The following are considered valid security vulnerabilities:

- **Authentication & Authorization** — JWT forgery, token leakage, privilege escalation, CSRF bypass
- **Injection** — SQL injection, prompt injection into the LLM pipeline, path traversal in document storage
- **Data Exposure** — Unauthorized access to other users' documents, chat sessions, or personal data
- **API Security** — Missing authentication on protected endpoints, rate-limit bypass, IDOR
- **Secrets Leakage** — API keys or secrets exposed in logs, responses, or Git history
- **Dependency Vulnerabilities** — Critical CVEs in production dependencies (`requirements.txt`, `package.json`)
- **Infrastructure** — Docker container escape, Redis exposure, unprotected admin endpoints

### Out of Scope

The following are **not** treated as security vulnerabilities:

- Issues in forks or versions not based on the current `main` branch
- Social engineering or phishing attacks against maintainers
- Missing security headers on a self-hosted instance where the operator has not followed the deployment guide
- Rate-limit bypasses that require pre-existing admin access
- Theoretical vulnerabilities without a working proof of concept

---

## 🔐 Security Hardening (Self-Hosted Deployments)

If you are deploying DocuMindAI yourself, follow these recommendations:

- **Use strong secrets**: generate `AUTH_SECRET_KEY` and `CSRF_SECRET_KEY` with at least 64 random characters
- **Never expose Redis or PostgreSQL** ports directly to the public internet — keep them internal
- **Enable HTTPS**: place the application behind a TLS-terminating reverse proxy (e.g., Nginx, Caddy, or Railway's built-in TLS)
- **Use environment variables** for all secrets — never hardcode keys in application code or Docker images
- **Rotate Gemini API keys** regularly and use the multi-key rotation feature to limit blast radius
- **Review `.env.example`** before deploying — do not use default or example values in production

---

## 🏆 Responsible Disclosure

We follow a **coordinated disclosure** model:

1. You report privately → we confirm and fix → we release a patch → we credit you (with your permission) → public disclosure.

We do not currently offer a paid bug bounty, but we will publicly credit responsible reporters in release notes and the repository's acknowledgements section.

Thank you for helping keep DocuMindAI and its users safe. 🙏
