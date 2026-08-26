"""
Security middleware and utilities for production-ready security
"""

import logging
import secrets
from typing import Optional
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import decorator_from_middleware
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """Add security headers to all responses, including CSP nonces"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        # Only add security headers in production
        if not settings.DEBUG:
            # Clickjacking protection
            response['X-Frame-Options'] = 'SAMEORIGIN'

            # MIME type sniffing protection
            response['X-Content-Type-Options'] = 'nosniff'

            # XSS protection (legacy, but still useful)
            response['X-XSS-Protection'] = '1; mode=block'

            # Referrer policy
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

            # Permissions policy (replaces Feature-Policy)
            response['Permissions-Policy'] = (
                'geolocation=(), '
                'microphone=(), '
                'camera=(), '
                'payment=()'
            )

            # Generate a fresh CSP nonce and attach it so templates
            # can use {% nonce %} or the built-in {% csp_nonce "script" %}.
            nonce = secrets.token_hex(16)
            response['X-CSP-Nonce'] = nonce
            request.csp_nonce = nonce

            # Content Security Policy with nonce support.
            # NOTE: templates currently rely on inline <style>/<script>
            # (no nonce attributes), plus these verified external origins:
            #   styles  -> fonts.googleapis.com      (base.html font <link>)
            #   scripts -> cdn.jsdelivr.net          (Chart.js, profile page)
            #   frames  -> www.youtube.com[/nocookie] (trailer embeds)
            # Keep this list in sync with what templates actually load.
            response['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' data: https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https:; "
                "frame-src https://www.youtube.com https://www.youtube-nocookie.com; "
                "frame-ancestors 'self'; "
                "upgrade-insecure-requests"
            )

        return response


class RateLimitMiddleware:
    """Rate limiting middleware using cache"""
    
    # Default limits: requests per hour
    DEFAULT_LIMIT = 100
    AUTHENTICATED_LIMIT = 1000
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Check rate limit
        if not self._check_rate_limit(request):
            logger.warning(f"Rate limit exceeded for {get_client_ip(request)}")
            return JsonResponse({
                'success': False,
                'error': {
                    'code': 'RATE_LIMIT_EXCEEDED',
                    'message': 'Too many requests. Please try again later.',
                    'retry_after': 60,
                }
            }, status=429)
        
        response = self.get_response(request)
        return response
    
    def _check_rate_limit(self, request: HttpRequest) -> bool:
        """
        Check if request exceeds rate limit.
        
        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limit(request.path):
            return True
        
        # Get identifier (user ID or IP address)
        if request.user.is_authenticated:
            identifier = f"rate_limit:user:{request.user.id}"
            limit = self.AUTHENTICATED_LIMIT
        else:
            identifier = f"rate_limit:ip:{get_client_ip(request)}"
            limit = self.DEFAULT_LIMIT
        
        # Get current count from cache
        current_count = cache.get(identifier, 0)
        
        if current_count >= limit:
            return False
        
        # Increment counter (expires after 1 hour)
        cache.set(identifier, current_count + 1, 3600)
        
        return True
    
    @staticmethod
    def _should_skip_rate_limit(path: str) -> bool:
        """Paths that should skip rate limiting"""
        skip_paths = [
            '/static/',
            '/media/',
            '/health/',
        ]
        
        for skip_path in skip_paths:
            if path.startswith(skip_path):
                return True
        
        return False


class RequestValidationMiddleware:
    """Validate incoming requests for security issues"""
    
    # Maximum content length (10MB)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Validate content length
        if request.META.get('CONTENT_LENGTH'):
            try:
                content_length = int(request.META.get('CONTENT_LENGTH', 0))
                if content_length > self.MAX_CONTENT_LENGTH:
                    logger.warning(
                        f"Request content too large: {content_length} bytes "
                        f"from {get_client_ip(request)}"
                    )
                    return JsonResponse({
                        'success': False,
                        'error': {
                            'code': 'PAYLOAD_TOO_LARGE',
                            'message': 'Request payload is too large',
                        }
                    }, status=413)
            except (ValueError, TypeError):
                pass
        
        response = self.get_response(request)
        return response


def get_client_ip(request: HttpRequest) -> str:
    """
    Extract client IP address from request.
    
    Handles proxies (X-Forwarded-For header) properly.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # X-Forwarded-For can contain multiple IPs; take the first
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', 'UNKNOWN')
    
    return ip


def is_safe_redirect_url(url: str, allowed_hosts: Optional[list] = None) -> bool:
    """
    Check if URL is safe for redirect.
    
    Prevents open redirect vulnerabilities.
    """
    if not url:
        return False
    
    # Don't allow protocol-relative URLs
    if url.startswith('//'):
        return False
    
    # Don't allow absolute URLs with external domains
    if url.startswith('http://') or url.startswith('https://'):
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if allowed_hosts is None:
            allowed_hosts = settings.ALLOWED_HOSTS
        
        if parsed.netloc not in allowed_hosts:
            return False
    
    return True


class IPWhitelistMiddleware:
    """
    Whitelist-based middleware for sensitive endpoints.
    
    Restricts access based on IP addresses.
    """
    
    # IPs allowed to access admin/sensitive endpoints
    WHITELIST_IPS = []
    
    # Paths that require IP whitelist
    PROTECTED_PATHS = ['/admin/', '/api/admin/']
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Load whitelist from settings
        self.WHITELIST_IPS = getattr(settings, 'IP_WHITELIST', [])
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Check if path is protected
        for protected_path in self.PROTECTED_PATHS:
            if request.path.startswith(protected_path):
                if not self._is_ip_whitelisted(request):
                    logger.warning(
                        f"Unauthorized access attempt to {request.path} "
                        f"from {get_client_ip(request)}"
                    )
                    return JsonResponse({
                        'success': False,
                        'error': {
                            'code': 'FORBIDDEN',
                            'message': 'Access denied',
                        }
                    }, status=403)
        
        response = self.get_response(request)
        return response
    
    def _is_ip_whitelisted(self, request: HttpRequest) -> bool:
        """Check if request IP is whitelisted"""
        if not self.WHITELIST_IPS:
            # If no whitelist defined, allow access
            return True
        
        client_ip = get_client_ip(request)
        return client_ip in self.WHITELIST_IPS
