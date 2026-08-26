# LuminaRecs Production Deployment Guide

## Overview

This guide provides step-by-step instructions to deploy LuminaRecs to production in a secure, scalable manner.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Environment Setup](#environment-setup)
3. [Database Setup](#database-setup)
4. [Security Configuration](#security-configuration)
5. [Web Server Setup](#web-server-setup)
6. [Celery Worker Setup](#celery-worker-setup)
7. [Monitoring & Logging](#monitoring--logging)
8. [Deployment Steps](#deployment-steps)
9. [Post-Deployment Verification](#post-deployment-verification)
10. [Troubleshooting](#troubleshooting)

---

## Pre-Deployment Checklist

- [ ] All secrets moved to environment variables (no hardcoded secrets in code)
- [ ] DEBUG set to False
- [ ] ALLOWED_HOSTS configured for your domain
- [ ] CORS_ALLOWED_ORIGINS restricted to specific domains
- [ ] Database credentials secured and not in version control
- [ ] SSL/TLS certificate obtained
- [ ] Logging infrastructure configured
- [ ] Error tracking (Sentry) configured
- [ ] Redis server available
- [ ] Celery worker configured
- [ ] Static files collected
- [ ] Database migrations tested
- [ ] Backup strategy in place

---

## Environment Setup

### 1. Create Production Environment File

```bash
# On production server
cd /var/www/luminarecs
cp .env.example .env.production
```

### 2. Edit .env.production with Production Values

```bash
nano .env.production
```

**Critical settings to configure:**

```
# Django Settings
SECRET_KEY=your-very-long-random-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,api.yourdomain.com

# Database
DB_ENGINE=django.db.backends.mysql
DB_NAME=luminarecs_prod
DB_USER=luminarecs_user
DB_PASSWORD=very-strong-password-here
DB_HOST=your-db-server.com
DB_PORT=3306

# Redis
REDIS_URL=redis://your-redis-server.com:6379/1

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True

# CORS
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=app-specific-password

# Error Tracking
SENTRY_DSN=https://your-sentry-key@sentry.io/project-id

# Logging
LOG_LEVEL=INFO
```

### 3. Generate Secure Secret Key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the output and set as SECRET_KEY in .env.production.

---

## Database Setup

### 1. Create Production Database

```sql
CREATE DATABASE luminarecs_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'luminarecs_user'@'localhost' IDENTIFIED BY 'very-strong-password';
GRANT ALL PRIVILEGES ON luminarecs_prod.* TO 'luminarecs_user'@'localhost';
FLUSH PRIVILEGES;
```

### 2. Run Migrations

```bash
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=core.settings
python manage.py migrate --noinput
```

### 3. Collect Static Files

```bash
python manage.py collectstatic --noinput --clear
```

### 4. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

### 5. Load Initial Data (If available)

```bash
python manage.py loaddata initial_data.json  # If you have seed data
```

---

## Security Configuration

### 1. Run Django Security Check

```bash
python manage.py check --deploy
```

This will identify any security issues in your configuration.

### 2. Configure SSH Keys

```bash
# On production server, set up SSH key-based authentication
ssh-keygen -t ed25519 -C "deploy@luminarecs"
# Add public key to your CI/CD pipeline
```

### 3. Set File Permissions

```bash
# Restrict access to environment file
chmod 600 /var/www/luminarecs/.env.production

# Ensure Django app files are readable
chmod 755 /var/www/luminarecs
find /var/www/luminarecs -type f -name "*.py" -exec chmod 644 {} \;
```

### 4. Configure Firewall

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 80/tcp     # HTTP (redirect to HTTPS)
sudo ufw allow 443/tcp    # HTTPS
sudo ufw enable
```

---

## Web Server Setup

### Using Gunicorn + Nginx

#### 1. Install Gunicorn

```bash
pip install gunicorn
```

#### 2. Create Systemd Service File

**File:** `/etc/systemd/system/luminarecs-gunicorn.service`

```ini
[Unit]
Description=LuminaRecs Gunicorn Application Server
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/luminarecs
Environment="PATH=/var/www/luminarecs/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings"
EnvironmentFile=/var/www/luminarecs/.env.production
ExecStart=/var/www/luminarecs/venv/bin/gunicorn \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind unix:/run/luminarecs.sock \
    --timeout 60 \
    --access-logfile /var/log/luminarecs/access.log \
    --error-logfile /var/log/luminarecs/error.log \
    core.wsgi:application

[Install]
WantedBy=multi-user.target
```

#### 3. Create Nginx Configuration

**File:** `/etc/nginx/sites-available/luminarecs`

```nginx
upstream luminarecs_app {
    server unix:/run/luminarecs.sock fail_timeout=0;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Logging
    access_log /var/log/nginx/luminarecs_access.log;
    error_log /var/log/nginx/luminarecs_error.log;

    # Client Upload Size
    client_max_body_size 10M;

    # Static files
    location /static/ {
        alias /var/www/luminarecs/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /var/www/luminarecs/media/;
        expires 30d;
    }

    # Django app
    location / {
        proxy_pass http://luminarecs_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

#### 4. Enable Nginx Site

```bash
sudo ln -s /etc/nginx/sites-available/luminarecs /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

#### 5. Set Up SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## Celery Worker Setup

### 1. Create Celery Service File

**File:** `/etc/systemd/system/luminarecs-celery.service`

```ini
[Unit]
Description=LuminaRecs Celery Worker
After=network.target redis-server.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/luminarecs
Environment="PATH=/var/www/luminarecs/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings"
EnvironmentFile=/var/www/luminarecs/.env.production
ExecStart=/var/www/luminarecs/venv/bin/celery \
    -A core \
    worker \
    --loglevel=info \
    --logfile=/var/log/luminarecs/celery.log \
    --pidfile=/var/run/celery.pid \
    --concurrency=4

[Install]
WantedBy=multi-user.target
```

### 2. Create Celery Beat Service (For Scheduled Tasks)

**File:** `/etc/systemd/system/luminarecs-celery-beat.service`

```ini
[Unit]
Description=LuminaRecs Celery Beat Scheduler
After=network.target redis-server.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/luminarecs
Environment="PATH=/var/www/luminarecs/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings"
EnvironmentFile=/var/www/luminarecs/.env.production
ExecStart=/var/www/luminarecs/venv/bin/celery \
    -A core \
    beat \
    --loglevel=info \
    --logfile=/var/log/luminarecs/celery-beat.log

[Install]
WantedBy=multi-user.target
```

### 3. Enable and Start Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable luminarecs-celery.service
sudo systemctl enable luminarecs-celery-beat.service
sudo systemctl start luminarecs-celery.service
sudo systemctl start luminarecs-celery-beat.service
```

---

## Monitoring & Logging

### 1. Configure Log Rotation

**File:** `/etc/logrotate.d/luminarecs`

```
/var/log/luminarecs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload luminarecs-gunicorn > /dev/null 2>&1 || true
    endscript
}
```

### 2. Set Up Sentry (Error Tracking)

1. Create account at https://sentry.io
2. Create new project for Django
3. Add Sentry DSN to .env.production
4. Errors will automatically be tracked

### 3. Monitor with Prometheus (Optional)

```bash
pip install django-prometheus
```

Add to INSTALLED_APPS in settings:
```python
INSTALLED_APPS = [
    'django_prometheus',
    # ... other apps
]
```

Add to MIDDLEWARE:
```python
MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusMiddleware',
    # ... other middleware
]
```

---

## Deployment Steps

### Automated Deployment Script

**File:** `deploy.sh`

```bash
#!/bin/bash
set -e

# Variables
DEPLOY_DIR="/var/www/luminarecs"
REPO_URL="https://github.com/yourusername/luminarecs.git"
BRANCH="main"

echo "Starting deployment..."

# Pull latest code
cd $DEPLOY_DIR
git fetch origin
git checkout $BRANCH
git pull origin $BRANCH

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput --clear

# Restart services
sudo systemctl restart luminarecs-gunicorn
sudo systemctl restart luminarecs-celery
sudo systemctl restart luminarecs-celery-beat

echo "Deployment completed successfully!"
```

### Manual Deployment

```bash
# SSH into production server
ssh user@your-production-server.com

# Navigate to project directory
cd /var/www/luminarecs

# Pull latest code
git fetch origin
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart services
sudo systemctl restart luminarecs-gunicorn
sudo systemctl restart luminarecs-celery

# Verify status
sudo systemctl status luminarecs-gunicorn
sudo systemctl status luminarecs-celery
```

---

## Post-Deployment Verification

### 1. Check Application Health

```bash
# Check if Gunicorn is running
sudo systemctl status luminarecs-gunicorn

# Check Nginx
sudo systemctl status nginx

# Check Celery workers
sudo systemctl status luminarecs-celery

# View logs
tail -f /var/log/luminarecs/error.log
tail -f /var/log/nginx/luminarecs_error.log
```

### 2. Test Endpoints

```bash
# Test homepage
curl https://yourdomain.com/

# Test API
curl https://yourdomain.com/api/movies/

# Test admin panel
curl https://yourdomain.com/admin/
```

### 3. Run Security Checks

```bash
python manage.py check --deploy
```

### 4. Verify SSL Certificate

```bash
curl -I https://yourdomain.com
# Should show SSL certificate details
```

### 5. Check Database Connection

```bash
python manage.py dbshell
SELECT VERSION();
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'dotenv'"

```bash
# Solution: Install python-dotenv
pip install python-dotenv
```

### Issue: "Secret key is missing"

```bash
# Solution: Ensure .env.production is loaded
export DJANGO_SETTINGS_MODULE=core.settings
python manage.py shell
# Check if SECRET_KEY is set
```

### Issue: Database Connection Error

```bash
# Check database credentials
echo $DB_USER $DB_PASSWORD $DB_HOST $DB_PORT

# Test MySQL connection
mysql -u luminarecs_user -p -h your-db-server.com luminarecs_prod
```

### Issue: Static Files Not Loading

```bash
# Recollect static files
python manage.py collectstatic --noinput --clear

# Check file permissions
ls -la /var/www/luminarecs/staticfiles/

# Verify Nginx configuration
sudo nginx -t
```

### Issue: Celery Tasks Not Running

```bash
# Check Celery worker status
sudo systemctl status luminarecs-celery

# View Celery logs
tail -f /var/log/luminarecs/celery.log

# Restart Celery
sudo systemctl restart luminarecs-celery
```

### Issue: High Memory Usage

```bash
# Check memory usage
free -h

# Limit Gunicorn workers
# Edit: /etc/systemd/system/luminarecs-gunicorn.service
# Change: --workers 2  (reduce from 4)

# Restart
sudo systemctl restart luminarecs-gunicorn
```

---

## Maintenance

### Regular Tasks

- **Daily**: Monitor logs and error tracking
- **Weekly**: Check disk space and backups
- **Monthly**: Review security updates and patch
- **Quarterly**: Load testing and performance review

### Backup Strategy

```bash
#!/bin/bash
# Daily backup script
BACKUP_DIR="/backups/luminarecs"
mkdir -p $BACKUP_DIR

# Backup database
mysqldump -u luminarecs_user -p luminarecs_prod | gzip > $BACKUP_DIR/db-$(date +%Y%m%d).sql.gz

# Backup uploaded files (if any)
tar -czf $BACKUP_DIR/media-$(date +%Y%m%d).tar.gz /var/www/luminarecs/media/

# Keep only last 30 days
find $BACKUP_DIR -type f -mtime +30 -delete
```

---

## Security Hardening Checklist

- [ ] SECRET_KEY is random and secure
- [ ] DEBUG = False
- [ ] ALLOWED_HOSTS configured correctly
- [ ] CORS restricted to specific domains
- [ ] SSL/TLS certificate installed and valid
- [ ] HSTS header enabled
- [ ] Security headers configured in Nginx
- [ ] Database credentials in environment variables
- [ ] Log files have restricted permissions
- [ ] Regular security updates applied
- [ ] Firewall rules configured
- [ ] SSH key-based authentication enabled
- [ ] Backups tested and verified
- [ ] Error tracking (Sentry) configured
- [ ] Rate limiting enabled

---

## Support & Debugging

For additional help:
1. Check Django logs: `/var/log/luminarecs/`
2. Check Nginx logs: `/var/log/nginx/`
3. Check Celery logs: `/var/log/luminarecs/celery.log`
4. Run `python manage.py check --deploy`
5. Review Sentry error tracking dashboard

