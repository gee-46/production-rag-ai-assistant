# API Version Migration & Legacy Deprecation Guide

## 1. Authentication Endpoints
- **v1.0 (Deprecated)**: The legacy endpoint `/api/v1/auth` is deprecated and scheduled for sunset on December 31, 2026. Legacy v1 uses outdated DES-56 encryption.
- **v2.0 (Active)**: Production systems must migrate to `/api/v2/oauth/token` utilizing modern `AES-256-GCM` cipher suites and PKCE verification.

## 2. Rate Limiting and Headers
- Legacy v1 returned `X-RateLimit-Remaining`.
- Active v2 returns standard `RateLimit-Limit`, `RateLimit-Remaining`, and `RateLimit-Reset` per IETF draft standards.
- Default burst quota for authenticated tenants is `1200 requests per minute`.
