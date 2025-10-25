# Nginx Setup for savezy.devanshkaria.dev

This directory contains Nginx configuration files for setting up a reverse proxy to your Flask application.

## Prerequisites

1. **DNS Configuration**: Ensure your domain `savezy.devanshkaria.dev` has an A record pointing to your EC2 instance's public IP
2. **EC2 Security Group**: Open ports 80 (HTTP) and 443 (HTTPS) in your EC2 security group
3. **Docker Container**: Your Flask app should be running on port 3000

## Quick Setup

### Option 1: Automated Setup (Recommended)

1. Copy files to your EC2 instance:
```bash
scp -i your-key.pem nginx/savezy.conf nginx/setup-nginx.sh ec2-user@your-ec2-ip:~/
```

2. SSH into your EC2 instance:
```bash
ssh -i your-key.pem ec2-user@your-ec2-ip
```

3. Run the setup script:
```bash
chmod +x setup-nginx.sh
sudo ./setup-nginx.sh
```

4. Get SSL certificate:
```bash
sudo certbot --nginx -d savezy.devanshkaria.dev
```

### Option 2: Manual Setup

1. **Install Nginx**:
```bash
sudo apt-get update
sudo apt-get install -y nginx
```

2. **Copy configuration**:
```bash
sudo cp savezy.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/savezy.conf /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site
```

3. **Test configuration**:
```bash
sudo nginx -t
```

4. **Restart Nginx**:
```bash
sudo systemctl restart nginx
sudo systemctl enable nginx
```

5. **Install Certbot and get SSL certificate**:
```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d savezy.devanshkaria.dev
```

## Verify Setup

1. **Check Nginx status**:
```bash
sudo systemctl status nginx
```

2. **Test HTTP redirect**:
```bash
curl -I http://savezy.devanshkaria.dev
# Should return 301 redirect to HTTPS
```

3. **Test HTTPS**:
```bash
curl https://savezy.devanshkaria.dev/check
# Should return: {"status": "healthy", "message": "Savezy API is running"}
```

4. **View logs**:
```bash
sudo tail -f /var/log/nginx/savezy_access.log
sudo tail -f /var/log/nginx/savezy_error.log
```

## SSL Certificate Auto-Renewal

Certbot automatically sets up a cron job for certificate renewal. To test:

```bash
sudo certbot renew --dry-run
```

## Troubleshooting

### Nginx won't start
```bash
# Check configuration
sudo nginx -t

# Check if port 80/443 is already in use
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :443
```

### SSL certificate issues
```bash
# Check certificate status
sudo certbot certificates

# Renew manually
sudo certbot renew --force-renewal
```

### Can't reach the application
```bash
# Check if Docker container is running
docker ps

# Check if app is accessible locally
curl http://localhost:3000/check

# Check Nginx error logs
sudo tail -100 /var/log/nginx/savezy_error.log
```

### 502 Bad Gateway
This usually means Nginx can't reach your Flask app:
```bash
# Verify Docker container is running on port 3000
docker ps
curl http://localhost:3000/check

# Check if firewall is blocking
sudo ufw status
```

## Configuration Details

- **Domain**: savezy.devanshkaria.dev
- **Backend**: localhost:3000 (Docker container)
- **SSL**: Let's Encrypt via Certbot
- **Logs**: 
  - Access: `/var/log/nginx/savezy_access.log`
  - Error: `/var/log/nginx/savezy_error.log`

## Security Features

✅ HTTP to HTTPS redirect  
✅ TLS 1.2 and 1.3 only  
✅ Security headers (X-Frame-Options, X-Content-Type-Options, etc.)  
✅ HSTS (HTTP Strict Transport Security)  
✅ 10MB upload limit  

## Updating Configuration

After making changes to the Nginx configuration:

```bash
# Test configuration
sudo nginx -t

# Reload Nginx (no downtime)
sudo systemctl reload nginx

# Or restart Nginx (brief downtime)
sudo systemctl restart nginx
```

## Useful Commands

```bash
# Start Nginx
sudo systemctl start nginx

# Stop Nginx
sudo systemctl stop nginx

# Restart Nginx
sudo systemctl restart nginx

# Reload configuration (no downtime)
sudo systemctl reload nginx

# Check status
sudo systemctl status nginx

# Enable on boot
sudo systemctl enable nginx

# View access logs
sudo tail -f /var/log/nginx/savezy_access.log

# View error logs
sudo tail -f /var/log/nginx/savezy_error.log
```
