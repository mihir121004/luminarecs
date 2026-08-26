"""
Custom exception handlers for REST Framework
"""

import logging
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error response format.
    
    Response format:
    {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable error message",
            "details": {}  # Optional - for validation errors
        }
    }
    """
    
    # Call DRF's default exception handler first to get the standard response
    response = drf_exception_handler(exc, context)
    
    # If no response is returned by DRF, handle it ourselves
    if response is None:
        logger.exception(f"Unhandled exception: {exc}", exc_info=(type(exc), exc, exc.__traceback__))
        return Response(
            {
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                    "details": str(exc) if getattr(exc, 'detail', None) else None,
                }
            },
            status=HTTP_500_INTERNAL_SERVER_ERROR,
        )
    
    # Transform DRF response to our standard format
    standard_response = transform_to_standard_format(response, exc, context)
    
    return standard_response


def transform_to_standard_format(response, exc, context):
    """
    Transform DRF's default error response to our standard format.
    """
    
    # Get error details from response
    error_data = response.data
    status_code = response.status_code
    
    # Determine error code and message
    error_code = get_error_code(exc, status_code)
    error_message = get_error_message(exc, error_data)
    
    # Build standardized response
    standard_response = Response(
        {
            "success": False,
            "error": {
                "code": error_code,
                "message": error_message,
                "details": format_error_details(error_data),
            }
        },
        status=status_code,
    )
    
    return standard_response


def get_error_code(exc, status_code):
    """
    Map exception to error code.
    """
    from rest_framework.exceptions import (
        ValidationError,
        NotFound,
        PermissionDenied,
        NotAuthenticated,
        MethodNotAllowed,
        Throttled,
    )
    
    exc_type = type(exc)
    
    if exc_type == ValidationError:
        return "VALIDATION_ERROR"
    elif exc_type == NotFound:
        return "NOT_FOUND"
    elif exc_type == PermissionDenied:
        return "PERMISSION_DENIED"
    elif exc_type == NotAuthenticated:
        return "NOT_AUTHENTICATED"
    elif exc_type == MethodNotAllowed:
        return "METHOD_NOT_ALLOWED"
    elif exc_type == Throttled:
        return "RATE_LIMIT_EXCEEDED"
    elif 400 <= status_code < 500:
        return f"CLIENT_ERROR_{status_code}"
    else:
        return f"SERVER_ERROR_{status_code}"


def get_error_message(exc, error_data):
    """
    Extract human-readable error message from exception.
    """
    from rest_framework.exceptions import ValidationError
    
    if isinstance(exc, ValidationError):
        return "The provided data is invalid. Please check the details."
    
    if isinstance(error_data, dict):
        # Try to get first error message
        if 'detail' in error_data:
            detail = error_data['detail']
            if isinstance(detail, str):
                return detail
            return str(detail)
        elif 'non_field_errors' in error_data:
            errors = error_data['non_field_errors']
            if errors:
                return str(errors[0])
    
    if isinstance(error_data, str):
        return error_data
    
    # Fallback
    if hasattr(exc, 'detail'):
        return str(exc.detail)
    
    return "An error occurred while processing your request."


def format_error_details(error_data):
    """
    Format error details for response.
    """
    if isinstance(error_data, dict):
        # For validation errors, include field details
        details = {}
        for key, value in error_data.items():
            if key != 'detail':
                if isinstance(value, list):
                    details[key] = [str(v) for v in value]
                else:
                    details[key] = str(value)
        return details if details else None
    
    return None
