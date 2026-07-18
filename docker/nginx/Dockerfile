FROM nginx:1.27-alpine

# Install openssl for generating fallback development/bootstrap certificates and DH parameters
RUN apk add --no-cache openssl

# Create directories for SSL certs, ACME challenges, and static/media mounts
RUN mkdir -p /etc/nginx/ssl/live \
             /var/www/certbot \
             /app/staticfiles \
             /app/media

# Generate fallback self-signed certificate & 2048-bit DH parameters during build
# This ensures Nginx starts cleanly even before Let's Encrypt certificates are mounted via volumes
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/live/edunaukari.key \
    -out /etc/nginx/ssl/live/edunaukari.crt \
    -subj "/CN=edunaukari.local/O=EduNaukari/C=IN" \
    && openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048

# Remove default Nginx config
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy custom main configuration and virtual hosts
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY docker/nginx/conf.d/ /etc/nginx/conf.d/

# Verify configuration syntax during build
RUN nginx -t

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
