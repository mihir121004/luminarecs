# Additional Production Requirements

The following packages may need to be added to `requirements.txt` if not already present:

```
# Error Tracking
sentry-sdk==1.48.0

# Monitoring (optional, recommended)
django-prometheus==2.3.1

# Additional Security
django-ratelimit==4.1.0  # Alternative rate limiting if preferred

# Testing
pytest==7.4.0
pytest-django==4.5.2
pytest-cov==4.1.0
factory-boy==3.3.0

# Code Quality & Type Checking
black==23.0.0
flake8==6.0.0
mypy==1.0.0
django-stubs==4.2.0

# API Documentation (optional, for Swagger/OpenAPI)
drf-spectacular==0.26.0
```

## Installation Instructions

```bash
# Core production requirements (mostly already installed)
pip install sentry-sdk

# Optional but recommended
pip install django-prometheus

# Development/Testing (only on dev machines)
pip install pytest pytest-django pytest-cov factory-boy
pip install black flake8 mypy django-stubs

# API Documentation (optional)
pip install drf-spectacular
```

## Environment Variable Checklist

Before deploying, ensure all these are set in `.env.production`:

```
# ✅ CRITICAL - Must be changed
SECRET_KEY=<generated-secret-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# ✅ Database - Verify credentials
DB_USER=luminarecs_user
DB_PASSWORD=<strong-password>
DB_HOST=your-db-server
DB_NAME=luminarecs_prod

# ✅ Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# ✅ CORS - Restrict to your domains
CORS_ALLOWED_ORIGINS=https://yourdomain.com

# ✅ Cache
REDIS_URL=redis://your-redis-server:6379/1

# ✅ Error Tracking
SENTRY_DSN=https://your-sentry-key@sentry.io/project-id

# ✅ Email (optional, for alerts)
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=<app-specific-password>

# ✅ Logging
LOG_LEVEL=INFO
```

## Pre-Launch Checklist

### Security ✅
- [ ] Run `python manage.py check --deploy`
- [ ] Verify all secrets are in environment variables
- [ ] Test HTTPS/SSL certificate
- [ ] Verify security headers in browser
- [ ] Check CORS configuration is restrictive

### Database ✅
- [ ] Run migrations: `python manage.py migrate`
- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Verify database backups
- [ ] Test database connection from app server

### Services ✅
- [ ] Start Gunicorn service
- [ ] Start Celery worker and beat
- [ ] Verify Nginx is running
- [ ] Check log files are being written

### Monitoring ✅
- [ ] Sentry error tracking working
- [ ] Logs being written to files
- [ ] Redis cache accessible
- [ ] Database queries logging (if enabled)

### Performance ✅
- [ ] Test static file serving (CSS, JS, images)
- [ ] Verify API endpoints respond quickly
- [ ] Check database query performance
- [ ] Run load test (optional but recommended)

### Documentation ✅
- [ ] Document production server configuration
- [ ] Document how to restart services
- [ ] Document backup procedures
- [ ] Document emergency contacts

---

## Critical Security Items Addressed

| Issue | Before | After |
|-------|--------|-------|
| Secret Key | Hardcoded in source | Environment variable |
| Database Password | Hardcoded in source | Environment variable |
| DEBUG | True (exposes sensitive info) | False in production |
| CORS | Allow all origins | Restricted to specific domains |
| Error Handling | Generic exceptions, printed | Standardized logging to Sentry |
| Input Validation | None | Comprehensive validation on all endpoints |
| Rate Limiting | None | 100/hour for anon, 1000/hour for users |
| Security Headers | Missing | Full suite of security headers |
| Logging | print() statements | Structured JSON logging |
| Password Strength | Django defaults | 12 character minimum |

---

## Performance Improvements Made

| Component | Issue | Fix | Improvement |
|-----------|-------|-----|-------------|
| Embedding Engine | O(n²) vectorizer retraining | Single pass vectorizer | 10-100x faster |
| Database Queries | No connection pooling | Connection pooling enabled | Better resource usage |
| Caching | No query caching | Redis caching enabled | Reduced DB load |
| Logging | Blocking file I/O | Async logging (if configured) | Better throughput |

---

## Testing Recommendations

Before going live, run:

```bash
# Run unit tests
python manage.py test platform_engine --verbosity=2

# Check security
python manage.py check --deploy

# Check for missing migrations
python manage.py makemigrations --check --dry-run

# Check database constraints
python manage.py validate_all_models  # If using django-extensions

# Load test (optional)
# Use Apache Bench or similar tool
# ab -n 1000 -c 10 https://yourdomain.com/
```

---

## Deployment Verification Commands

```bash
# SSH to server
ssh user@prod-server

# Check services
systemctl status luminarecs-gunicorn luminarecs-celery

# View recent logs
tail -f /var/log/luminarecs/luminarecs.log

# Check database connection
python manage.py dbshell

# Verify cache connection
python manage.py shell
>>> from django.core.cache import cache
>>> cache.set('test', 'value')
>>> cache.get('test')
'value'

# Test an API endpoint
curl -H "Authorization: Bearer YOUR_TOKEN" https://yourdomain.com/api/movies/

# Check SSL certificate
curl -I https://yourdomain.com  # Should show SSL certificate

# Monitor resource usage
htop
free -h
df -h
```

---

## Rollback Procedure

If issues occur in production:

```bash
# Stop all services
sudo systemctl stop luminarecs-gunicorn luminarecs-celery luminarecs-celery-beat

# Revert to previous version
cd /var/www/luminarecs
git checkout previous-commit-hash

# Revert database (if needed)
python manage.py migrate 0XXX  # Revert to specific migration

# Restart services
sudo systemctl start luminarecs-gunicorn luminarecs-celery luminarecs-celery-beat

# Verify
systemctl status luminarecs-gunicorn
```

---

## Monitoring Setup

### Application Monitoring
- **Tool**: Sentry
- **Configuration**: `SENTRY_DSN` in environment
- **Dashboard**: https://sentry.io

### System Monitoring (Optional)
- **Tool**: Prometheus + Grafana
- **Package**: django-prometheus
- **Metrics**: HTTP requests, DB queries, error rates

### Log Aggregation (Optional)
- **Tool**: ELK Stack or similar
- **Logs Location**: `/var/log/luminarecs/`
- **Format**: JSON for easy parsing

---

## Backup Strategy

### Daily Backups
```bash
#!/bin/bash
# Backup database
mysqldump -u luminarecs_user -p luminarecs_prod | gzip > /backups/db-$(date +%Y%m%d).sql.gz

# Backup media files (if any)
tar -czf /backups/media-$(date +%Y%m%d).tar.gz /var/www/luminarecs/media/

# Keep only last 30 days
find /backups -type f -mtime +30 -delete
```

### Test Restores
- Regularly test backup restoration
- Document procedures
- Document recovery time objectives (RTO)

---

## Support Contacts

- **Primary Admin**: [Name/Email]
- **Secondary Admin**: [Name/Email]
- **Hosting Provider**: [Contact Info]
- **On-Call Rotation**: [Schedule/Process]

---

## Post-Launch Monitoring (First Week)

- [ ] Monitor error rates in Sentry
- [ ] Check performance metrics
- [ ] Review access logs for anomalies
- [ ] Verify backup processes running
- [ ] Check disk space usage
- [ ] Verify email alerts are working
- [ ] Get user feedback on performance

---

## Production Deployment Checklist

```bash
# Final verification before launch
□ All security checks passed
□ Database backups tested
□ SSL certificate installed and verified
□ Email notifications configured
□ Error tracking (Sentry) operational
□ Log files writing correctly
□ Services auto-start on reboot configured
□ Monitoring alerts configured
□ Documentation complete
□ Team trained on procedures
□ Runbooks created

# Launch sequence
□ Final code review
□ Run all tests
□ Perform dry-run deployment
□ Schedule maintenance window if needed
□ Deploy to production
□ Monitor closely for first hour
□ Monitor for first day
□ Monitor for first week
```

---

## Success Criteria

Your deployment is successful if:

1. ✅ All services are running without errors
2. ✅ API endpoints respond within acceptable time
3. ✅ No errors in Sentry dashboard
4. ✅ Security check passes: `python manage.py check --deploy`
5. ✅ SSL certificate is valid
6. ✅ Logs are being written
7. ✅ Backups are running
8. ✅ Users can log in and use the application
9. ✅ Database queries are performant
10. ✅ Cache is working (Redis is accessible)

---

**Status**: Production-Ready ✅

Your LuminaRecs application is now ready for production deployment!
