# Nginx Deployment Guide for savezy.devanshkaria.dev

## Complete Setup Steps

### 1. DNS Configuration

First, add an A record in your DNS settings:

- **Type**: A
- **Name**: savezy (or @savezy if subdomain)
- **Value**: Your EC2 instance public IP
- **TTL**: 300 (or default)

Wait 5-10 minutes for DNS propagation, then verify:

```bash
nslookup savezy.devanshkaria.dev
```

### 2. EC2 Security Group Configuration

Ensure your EC2 security group allows:

| Type | Protocol | Port Range | Source |
|------|----------|------------|--------|
| HTTP | TCP | 80 | 0.0.0.0/0 |
| HTTPS | TCP | 443 | 0.0.0.0/0 |
| SSH | TCP | 22 | Your IP |
| Custom TCP | TCP | 3000 | localhost only |

### 3. Copy Files to EC2

From your local machine:

```bash
# Copy nginx configuration files
scp -i your-key.pem nginx/savezy.conf nginx/setup-nginx.sh ec2-user@YOUR_EC2_IP:~/

# Or use the GitHub Actions workflow (recommended)
git add nginx/
git commit -m "Add nginx configuration"
git push origin main
```

### 4. SSH into EC2 and Setup Nginx

```bash
ssh -i your-key.pem ec2-user@YOUR_EC2_IP

# Make setup script executable
chmod +x setup-nginx.sh

# Run setup script
sudo ./setup-nginx.sh
```

The script will:
- Install Nginx
- Install Certbot
- Configure the reverse proxy
- Enable and start Nginx

### 5. Get SSL Certificate

```bash
sudo certbot --nginx -d savezy.devanshkaria.dev
```

Follow the prompts:
- Enter your email
- Agree to terms
- Choose whether to redirect HTTP to HTTPS (recommended: Yes)

### 6. Update Production Environment Variables

On your EC2 instance, update the `.env` file:

```bash
cd ~/savezy-backend
nano .env
```

Update these values:

```bash
FLASK_ENV=production
GOOGLE_REDIRECT_URI=https://savezy.devanshkaria.dev/api/auth/google/callback
CORS_ORIGINS=https://savezy.devanshkaria.dev
```

### 7. Restart Docker Container

```bash
cd ~/savezy-backend
docker-compose down
docker-compose up -d
```

### 8. Verify Everything Works

```bash
# Test health endpoint
curl https://savezy.devanshkaria.dev/check

# Should return:
# {"status": "healthy", "message": "Savezy API is running"}

# Check Nginx logs
sudo tail -f /var/log/nginx/savezy_access.log
```

## Architecture Overview

```
Internet
    ↓
[Port 80/443] → Nginx (Reverse Proxy)
    ↓
[Port 3000] → Docker Container (Flask App)
    ↓
SQLite Database
```

## Important URLs

- **API Base**: https://savezy.devanshkaria.dev
- **Health Check**: https://savezy.devanshkaria.dev/check
- **Google OAuth Callback**: https://savezy.devanshkaria.dev/api/auth/google/callback
- **Token Verification**: https://savezy.devanshkaria.dev/api/auth/token/verify2

## Update Google OAuth Settings

Don't forget to update your Google Cloud Console:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to APIs & Services → Credentials
3. Edit your OAuth 2.0 Client ID
4. Add to **Authorized redirect URIs**:
   - `https://savezy.devanshkaria.dev/api/auth/google/callback`

## Maintenance Commands

### View Logs

```bash
# Nginx access logs
sudo tail -f /var/log/nginx/savezy_access.log

# Nginx error logs
sudo tail -f /var/log/nginx/savezy_error.log

# Docker logs
docker-compose logs -f app
```

### Restart Services

```bash
# Restart Nginx
sudo systemctl restart nginx

# Restart Docker container
cd ~/savezy-backend
docker-compose restart app
```

### SSL Certificate Renewal

Certbot auto-renews certificates. To test:

```bash
sudo certbot renew --dry-run
```

### Update Nginx Configuration

```bash
# Edit configuration
sudo nano /etc/nginx/sites-available/savezy.conf

# Test configuration
sudo nginx -t

# Reload Nginx (no downtime)
sudo systemctl reload nginx
```

## Troubleshooting

### 502 Bad Gateway

**Cause**: Nginx can't reach the Flask app

**Solution**:
```bash
# Check if Docker container is running
docker ps

# Check if app responds locally
curl http://localhost:3000/check

# Restart container if needed
docker-compose restart app
```

### SSL Certificate Issues

**Cause**: Certificate expired or not found

**Solution**:
```bash
# Check certificate status
sudo certbot certificates

# Renew certificate
sudo certbot renew --force-renewal

# Restart Nginx
sudo systemctl restart nginx
```

### DNS Not Resolving

**Cause**: DNS not propagated or misconfigured

**Solution**:
```bash
# Check DNS
nslookup savezy.devanshkaria.dev

# Check if A record points to correct IP
dig savezy.devanshkaria.dev
```

### CORS Errors

**Cause**: CORS_ORIGINS not configured correctly

**Solution**:
Update `.env` on EC2:
```bash
CORS_ORIGINS=https://savezy.devanshkaria.dev
```

Then restart:
```bash
docker-compose restart app
```

## Security Checklist

- ✅ HTTPS enabled with Let's Encrypt
- ✅ HTTP redirects to HTTPS
- ✅ Security headers configured
- ✅ HSTS enabled
- ✅ Firewall configured (only ports 80, 443, 22 open)
- ✅ Docker container runs as non-root user
- ✅ Environment variables secured
- ✅ Auto-renewal for SSL certificates

## Performance Optimization

The Nginx configuration includes:
- HTTP/2 support
- Gzip compression (if needed, add to config)
- Static file caching
- Connection keep-alive
- Proxy buffering

## Monitoring

Consider setting up:
- CloudWatch for EC2 metrics
- Nginx access log analysis
- Uptime monitoring (e.g., UptimeRobot)
- SSL certificate expiry monitoring

## Next Steps

1. ✅ DNS configured
2. ✅ Nginx installed and configured
3. ✅ SSL certificate obtained
4. ✅ Docker container running
5. ✅ Google OAuth updated
6. 🔄 Test all endpoints
7. 🔄 Monitor logs for issues
8. 🔄 Set up automated backups

---

**Need Help?** Check the logs first:
```bash
sudo tail -100 /var/log/nginx/savezy_error.log
docker-compose logs --tail=100 app
```
