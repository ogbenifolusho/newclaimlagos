# CLAIM LAGOS – Security Notes

## Implemented
- JWT access + refresh tokens (HS256); passwords bcrypt-hashed
- RBAC roles seeded; `get_current_user` on mutating routes
- Security headers middleware (X-Frame-Options, nosniff, XSS, Referrer-Policy, HSTS on HTTPS)
- Rate limiting (in-memory per IP; auth tighter)
- Audit log table for significant actions
- Secrets via environment variables / `.env` (not in git)
- No automated public social publishing

## Hostinger / VPS recommendations
- UFW: allow 22, 80, 443 only
- Fail2ban on SSH
- TLS via Let's Encrypt or Hostinger panel
- Keep Docker and base images updated
- Restrict MinIO console (9001) to localhost or VPN

## Data protection
- Political / personal data: minimise retention of raw social payloads
- Export access requires authentication
- Geo public data marked `is_placeholder` until official sources replace it

## Residual risks (document for Phase 9+)
- In-memory rate limit resets on process restart → Redis rate limit preferred at scale
- MFA fields exist but enforcement UI not complete
- Synthetic ingest must not be mistaken for live intelligence in briefings
