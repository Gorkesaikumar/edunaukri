# EduNaukri Production Nginx Architecture

This directory (`docker/nginx`) houses the production-grade reverse proxy configuration for **EduNaukri**. It handles TLS termination, HTTP/2 multiplexing, static asset delivery, security headers, rate limiting, and WebSocket proxying for Daphne/Django Channels.

---

## 🏛️ Architecture Overview

```
                        ┌─────────────────────────────────────┐
                        │        Client Browser / API         │
                        └──────────────────┬──────────────────┘
                                           │ HTTPS (Port 443) / HTTP (Port 80)
                                           ▼
                        ┌─────────────────────────────────────┐
                        │    Nginx Reverse Proxy Container    │
                        │        (nginx:1.27-alpine)          │
                        └─┬─────────┬───────────────┬───────┬─┘
                          │         │               │       │
      ┌───────────────────┘         │               │       └────────────────────┐
      ▼                             ▼               ▼                            ▼
┌───────────┐                ┌───────────┐   ┌─────────────┐             ┌───────────────┐
│/staticfiles│                │  /media/  │   │ /api/ & /   │             │   /ws/ &      │
│  (1 year) │                │ (30 days) │   │ (HTTP Proxy)│             │/live-activity/│
└───────────┘                └─────┬─────┘   └──────┬──────┘             └───────┬───────┘
      │                            │                │                            │
      │ (Served directly           │ (Blocks        │ (Daphne / Django App       │ (WebSocket
      │  from volume)              │  scripts)      │  on internal port 8000)    │  Upgrade)
      │                            ▼                ▼                            ▼
      │                     [Execution Block]  [Django Backend]             [Channels Hub]
```

---

## 🔒 Key Features & Configurations

### 1. SSL/TLS & Bootstrap Resilience
* **Automated Bootstrap**: When the Nginx container builds (`docker/nginx/Dockerfile`), it runs `openssl` to generate a **self-signed fallback certificate** (`edunaukari.crt`), **RSA private key** (`edunaukari.key`), and a **2048-bit Diffie-Hellman parameter file** (`dhparam.pem`) in `/etc/nginx/ssl/live/`.
* **Zero-Crash Startup**: This allows Nginx to start immediately on brand-new servers before Certbot/Let's Encrypt certificates are provisioned. Once real certificates are mounted into `/etc/nginx/ssl/live/` via Docker volumes, Nginx automatically serves valid production certificates.
* **Modern Cryptography**: Enforces `TLSv1.2` and `TLSv1.3` only with forward secrecy ciphers (`ECDHE-ECDSA-AES128-GCM-SHA256...`).
* **Session Optimization**: Uses `ssl_session_cache shared:SSL:10m;` and `ssl_session_timeout 1d;` for fast TLS re-handshakes without session ticket risks (`ssl_session_tickets off;`).

### 2. Static & Media Asset Delivery (`open_file_cache`)
* **Static Files (`/staticfiles/` & `/static/`)**:
  * Served directly by Nginx from the `static_data` volume without touching Django.
  * Emits `Cache-Control "public, max-age=31536000, immutable"` (`1 year`) for maximum CDN and browser caching efficiency.
* **Media Files (`/media/`)**:
  * Served directly by Nginx from the `media_data` volume with `Cache-Control "public, max-age=2592000"` (`30 days`).
  * **Security Hardening**: Enforces an explicit execution blocker against malicious uploads (`location ~* ^/media/.*\.(py|pl|php|sh|cgi|asp|jsp|exe)$ { return 403; }`).

### 3. Rate Limiting & DDoS Mitigation (`nginx.conf`)
Three distinct shared memory zones protect backend resources:
1. `addr_limit` (`limit_conn_zone`): Caps simultaneous connections per IP (`limit_conn addr_limit 20;`) to prevent slowloris and resource starvation attacks.
2. `general_limit` (`limit_req_zone rate=20r/s`): Standard page view and general browsing rate limit (`burst=20 nodelay`).
3. `auth_limit` (`limit_req_zone rate=5r/s`): Strict rate limit applied to authentication, sign-in, and super-admin login routes (`burst=10 nodelay`) to prevent credential stuffing and brute-force attacks.
4. `api_limit` (`limit_req_zone rate=50r/s`): High-throughput burst allocation for REST API endpoints (`burst=30 nodelay`).

### 4. Large File Uploads & Buffering
* Configured with `client_max_body_size 100m;` and `client_body_buffer_size 128k;` to support candidate resume uploads, portfolio documents, and faculty video presentations.
* `proxy_request_buffering off;` allows large multipart streams to pass cleanly to Daphne without temporary file bottlenecks.

### 5. WebSockets & Live Activity Proxy
* Routes matching `/ws/` or `/live-activity/` automatically upgrade HTTP requests to WebSockets (`proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";`).
* Configured with `proxy_read_timeout 86400s;` (`24 hours`) to keep live notification feeds and real-time candidate pipelines connected without arbitrary timeouts.

---

## 🛠️ Certbot / Let's Encrypt Integration Guide

To issue free Let's Encrypt certificates on your production domain:

1. Ensure your DNS records (`A` and `AAAA`) for `www.edunaukari.com` and `edunaukari.com` point to your server IP.
2. Run Certbot using a temporary container sharing the `certbot_data` (`/var/www/certbot`) and `ssl_data` (`/etc/nginx/ssl/live`) volumes:
   ```bash
   docker run -it --rm \
     -v edunaukri_certbot_data:/var/www/certbot \
     -v edunaukri_ssl_data:/etc/letsencrypt \
     certbot/certbot certonly --webroot \
     -w /var/www/certbot \
     -d edunaukari.com -d www.edunaukari.com \
     --email admin@edunaukari.com --agree-tos --no-eff-email
   ```
3. Copy or symlink the issued Let's Encrypt files inside `ssl_data` so they match `edunaukari.crt` and `edunaukari.key`, or update `/etc/nginx/conf.d/edunaukri.conf` to point directly to `/etc/letsencrypt/live/edunaukari.com/fullchain.pem` and `privkey.pem`.
4. Reload Nginx without downtime:
   ```bash
   docker compose exec nginx nginx -s reload
   ```
