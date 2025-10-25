#!/bin/bash
# Setup script for Nginx on EC2 instance
# Run this script on your EC2 instance as root or with sudo

set -e

echo "========================================="
echo "Savezy Nginx Setup Script"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

# Update system
echo -e "${GREEN}Updating system packages...${NC}"
apt-get update

# Install Nginx
echo -e "${GREEN}Installing Nginx...${NC}"
apt-get install -y nginx

# Install Certbot for SSL
echo -e "${GREEN}Installing Certbot for SSL certificates...${NC}"
apt-get install -y certbot python3-certbot-nginx

# Copy Nginx configuration
echo -e "${GREEN}Setting up Nginx configuration...${NC}"
cp savezy.conf /etc/nginx/sites-available/savezy.conf

# Remove default site if it exists
if [ -f /etc/nginx/sites-enabled/default ]; then
    echo -e "${YELLOW}Removing default Nginx site...${NC}"
    rm /etc/nginx/sites-enabled/default
fi

# Create symlink
echo -e "${GREEN}Enabling Savezy site...${NC}"
ln -sf /etc/nginx/sites-available/savezy.conf /etc/nginx/sites-enabled/

# Test Nginx configuration
echo -e "${GREEN}Testing Nginx configuration...${NC}"
nginx -t

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Nginx configuration is valid!${NC}"
else
    echo -e "${RED}Nginx configuration has errors. Please check and fix.${NC}"
    exit 1
fi

# Restart Nginx
echo -e "${GREEN}Restarting Nginx...${NC}"
systemctl restart nginx
systemctl enable nginx

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Nginx setup complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Make sure your DNS A record points to this server's IP"
echo "2. Run the following command to get SSL certificate:"
echo ""
echo -e "${GREEN}   sudo certbot --nginx -d savezy.devanshkaria.dev${NC}"
echo ""
echo "3. Certbot will automatically configure SSL and set up auto-renewal"
echo ""
echo -e "${YELLOW}To check Nginx status:${NC}"
echo "   sudo systemctl status nginx"
echo ""
echo -e "${YELLOW}To view logs:${NC}"
echo "   sudo tail -f /var/log/nginx/savezy_access.log"
echo "   sudo tail -f /var/log/nginx/savezy_error.log"
