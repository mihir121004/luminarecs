"""
Structured logging utilities for production-ready logging
"""

import logging
import json
import traceback
from datetime import datetime
from functools import wraps
from django.conf import settings
from django.http import JsonResponse
from rest_framework import status


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info),
            }
        
        # Add custom fields if present
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        
        return json.dumps(log_data)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with proper configuration.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))
    return logger


# Create module-level loggers
logger = get_logger(__name__)
app_logger = get_logger('platform_engine')
ai_logger = get_logger('platform_engine.ml_engine')
api_logger = get_logger('platform_engine.api')


def log_execution(func):
    """
    Decorator to log function execution time and parameters.
    
    Usage:
        @log_execution
        def my_function(arg1, arg2):
            return arg1 + arg2
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        module_name = func.__module__
        
        logger_instance = get_logger(module_name)
        logger_instance.debug(f"Starting {func_name}", extra={
            'function': func_name,
            'args': str(args)[:100],  # Limit length
            'kwargs': str(kwargs)[:100],
        })
        
        start_time = datetime.utcnow()
        
        try:
            result = func(*args, **kwargs)
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger_instance.debug(f"Completed {func_name}", extra={
                'function': func_name,
                'duration_ms': duration_ms,
            })
            
            return result
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger_instance.error(f"Error in {func_name}", extra={
                'function': func_name,
                'duration_ms': duration_ms,
                'error': str(e),
            }, exc_info=True)
            raise
    
    return wrapper


def log_api_request(view_func):
    """
    Decorator to log API request/response details.
    
    Usage:
        @log_api_request
        def api_endpoint(request):
            return Response({'success': True})
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        start_time = datetime.utcnow()
        request_id = getattr(request, '_request_id', None)
        user_id = request.user.id if request.user.is_authenticated else None
        
        api_logger.info(f"API Request: {request.method} {request.path}", extra={
            'request_id': request_id,
            'method': request.method,
            'path': request.path,
            'user_id': user_id,
            'ip_address': get_client_ip(request),
        })
        
        try:
            response = view_func(request, *args, **kwargs)
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            status_code = getattr(response, 'status_code', 200)
            api_logger.info(f"API Response: {status_code}", extra={
                'request_id': request_id,
                'status_code': status_code,
                'duration_ms': duration_ms,
                'user_id': user_id,
            })
            
            return response
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            api_logger.error(f"API Error: {request.method} {request.path}", extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.path,
                'user_id': user_id,
                'duration_ms': duration_ms,
            }, exc_info=True)
            raise
    
    return wrapper


class RequestLoggingMiddleware:
    """Middleware to add request ID and log all requests"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Generate request ID
        import uuid
        request._request_id = str(uuid.uuid4())

        # Log request including which cookies the client actually sent
        # (names only - never values - plus the Host header). This makes
        # CSRF/session debugging possible without leaking secrets.
        cookie_names = ", ".join(sorted(request.COOKIES.keys())) or "<none>"
        logger.debug(
            f"Request: {request.method} {request.path} "
            f"[host={request.get_host()}] [cookies: {cookie_names}]",
            extra={
                'request_id': request._request_id,
                'method': request.method,
                'path': request.path,
                'ip_address': get_client_ip(request),
            },
        )
        
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            logger.error(f"Unhandled exception in request", extra={
                'request_id': request._request_id,
                'method': request.method,
                'path': request.path,
            }, exc_info=True)
            raise


def get_client_ip(request) -> str:
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_db_query(query: str, duration_ms: float):
    """Log database query execution"""
    if duration_ms > 100:  # Log slow queries
        logger.warning(f"Slow database query ({duration_ms}ms)", extra={
            'query': query[:200],  # Limit query length
            'duration_ms': duration_ms,
        })


def log_cache_operation(operation: str, key: str, duration_ms: float, hit: bool = None):
    """Log cache operations"""
    logger.debug(f"Cache {operation}: {key}", extra={
        'operation': operation,
        'key': key,
        'duration_ms': duration_ms,
        'hit': hit,
    })


def log_ml_operation(operation: str, model: str, duration_ms: float, success: bool = True):
    """Log ML/AI operation execution"""
    level = logging.INFO if success else logging.ERROR
    ai_logger.log(level, f"ML Operation: {operation} ({model})", extra={
        'operation': operation,
        'model': model,
        'duration_ms': duration_ms,
        'success': success,
    })


# Convenience functions for common logging scenarios

def log_user_action(user_id, action: str, details: dict = None):
    """Log user action for audit trail"""
    app_logger.info(f"User action: {action}", extra={
        'user_id': user_id,
        'action': action,
        'details': details,
    })


def log_security_event(event_type: str, details: dict = None):
    """Log security-related events"""
    logger = get_logger('platform_engine.security')
    logger.warning(f"Security event: {event_type}", extra={
        'event_type': event_type,
        'details': details,
    })


def log_performance_metric(metric_name: str, value: float, unit: str = "ms"):
    """Log performance metrics"""
    logger.info(f"Performance metric: {metric_name}={value}{unit}", extra={
        'metric': metric_name,
        'value': value,
        'unit': unit,
    })
