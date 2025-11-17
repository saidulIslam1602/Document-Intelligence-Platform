# SSL Certificate Directory

This directory is for SSL certificates when running in production with HTTPS.

## Development (Self-Signed Certificate)

To generate a self-signed certificate for development:

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout key.pem \
  -out cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

## Production

In production, use proper SSL certificates from a Certificate Authority (CA) like:
- Let's Encrypt (free)
- DigiCert
- Comodo

Place your certificates here:
- `cert.pem` - SSL certificate
- `key.pem` - Private key
- `ca-bundle.pem` - Certificate chain (if applicable)
