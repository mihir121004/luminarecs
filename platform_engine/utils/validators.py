"""
Input validation utilities for consistent data validation
"""

import re
import logging
from django.core.exceptions import ValidationError
from django.utils.html import escape

logger = logging.getLogger(__name__)


class InputValidator:
    """Utility class for input validation"""
    
    # Constants
    MAX_SEARCH_LENGTH = 255
    MAX_QUERY_LENGTH = 500
    MAX_TEXT_LENGTH = 5000
    MIN_QUERY_LENGTH = 1
    
    @staticmethod
    def validate_search_query(query: str, max_length: int = MAX_SEARCH_LENGTH) -> str:
        """
        Validate and sanitize search query.
        
        Args:
            query: Search query string
            max_length: Maximum allowed length
            
        Returns:
            Sanitized query string
            
        Raises:
            ValidationError: If query is invalid
        """
        if not isinstance(query, str):
            raise ValidationError("Search query must be a string")
        
        query = query.strip()
        
        if len(query) < InputValidator.MIN_QUERY_LENGTH:
            raise ValidationError("Search query cannot be empty")
        
        if len(query) > max_length:
            raise ValidationError(f"Search query cannot exceed {max_length} characters")
        
        # Check for potential ReDoS patterns
        if InputValidator._is_potentially_malicious(query):
            raise ValidationError("Search query contains invalid patterns")
        
        return escape(query)
    
    @staticmethod
    def validate_integer_id(id_value, min_value: int = 1, max_value: int = 2**31 - 1) -> int:
        """
        Validate integer ID parameter.
        
        Args:
            id_value: ID value to validate
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            Validated integer ID
            
        Raises:
            ValidationError: If ID is invalid
        """
        try:
            id_int = int(id_value)
        except (ValueError, TypeError):
            raise ValidationError("ID must be a valid integer")
        
        if id_int < min_value or id_int > max_value:
            raise ValidationError(f"ID must be between {min_value} and {max_value}")
        
        return id_int
    
    @staticmethod
    def validate_pagination_params(page: str = "1", page_size: str = "20", max_page_size: int = 100) -> tuple:
        """
        Validate pagination parameters.
        
        Args:
            page: Page number (1-indexed)
            page_size: Items per page
            max_page_size: Maximum allowed page size
            
        Returns:
            Tuple of (page, page_size) as integers
            
        Raises:
            ValidationError: If parameters are invalid
        """
        try:
            page_num = int(page)
            size = int(page_size)
        except (ValueError, TypeError):
            raise ValidationError("Page and page_size must be valid integers")
        
        if page_num < 1:
            raise ValidationError("Page number must be >= 1")
        
        if size < 1 or size > max_page_size:
            raise ValidationError(f"Page size must be between 1 and {max_page_size}")
        
        return page_num, size
    
    @staticmethod
    def validate_rating(rating):
        """
        Validate rating value.
        
        Args:
            rating: Rating value
            
        Returns:
            Validated float rating
            
        Raises:
            ValidationError: If rating is invalid
        """
        try:
            rating_float = float(rating)
        except (ValueError, TypeError):
            raise ValidationError("Rating must be a valid number")
        
        if rating_float < 1 or rating_float > 10:
            raise ValidationError("Rating must be between 1 and 10")
        
        return rating_float
    
    @staticmethod
    def validate_interaction_type(interaction_type: str) -> str:
        """
        Validate interaction type enum.
        
        Args:
            interaction_type: Type of interaction
            
        Returns:
            Validated interaction type
            
        Raises:
            ValidationError: If interaction type is invalid
        """
        valid_types = ['CLICK', 'WATCH', 'TRAILER', 'RATING', 'VIEW', 'WISHLIST']
        
        if not isinstance(interaction_type, str):
            raise ValidationError("Interaction type must be a string")
        
        interaction_type = interaction_type.upper().strip()
        
        if interaction_type not in valid_types:
            raise ValidationError(f"Interaction type must be one of: {', '.join(valid_types)}")
        
        return interaction_type
    
    @staticmethod
    def validate_text_input(text: str, max_length: int = MAX_TEXT_LENGTH, min_length: int = 1) -> str:
        """
        Validate and sanitize text input.
        
        Args:
            text: Text to validate
            max_length: Maximum allowed length
            min_length: Minimum allowed length
            
        Returns:
            Sanitized text
            
        Raises:
            ValidationError: If text is invalid
        """
        if not isinstance(text, str):
            raise ValidationError("Input must be a string")
        
        text = text.strip()
        
        if len(text) < min_length:
            raise ValidationError(f"Text must be at least {min_length} character(s)")
        
        if len(text) > max_length:
            raise ValidationError(f"Text cannot exceed {max_length} characters")
        
        return escape(text)
    
    @staticmethod
    def _is_potentially_malicious(query: str) -> bool:
        """
        Check for potentially malicious patterns in query.
        """
        # Simple pattern check for common ReDoS patterns
        # This is a basic check - a more comprehensive solution would use a library
        dangerous_patterns = [
            r'(\w+\*){10,}',  # Repeated wildcards
            r'(\.|\*){20,}',   # Many dots or asterisks
            r'(\|.+){10,}',    # Many OR operators
        ]
        
        for pattern in dangerous_patterns:
            try:
                if re.search(pattern, query, timeout=1):
                    logger.warning(f"Potentially malicious pattern detected in query: {query[:50]}")
                    return True
            except Exception as e:
                logger.warning(f"Error checking for malicious pattern: {e}")
        
        return False
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent directory traversal and other issues.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove directory traversal attempts
        filename = filename.replace('..', '').replace('/', '').replace('\\', '')
        
        # Keep only alphanumeric, dash, underscore, and dot
        filename = re.sub(r'[^\w\s.-]', '', filename)
        
        # Limit length
        return filename[:255]


def validate_request_data(data: dict, required_fields: list, optional_fields: dict = None) -> dict:
    """
    Validate request data against required and optional fields.
    
    Args:
        data: Request data dictionary
        required_fields: List of required field names
        optional_fields: Dict of optional field names with default values
        
    Returns:
        Validated data dictionary
        
    Raises:
        ValidationError: If required fields are missing
    """
    errors = {}
    
    # Check required fields
    for field in required_fields:
        if field not in data or data[field] is None:
            errors[field] = f"{field} is required"
    
    if errors:
        raise ValidationError(errors)
    
    # Add optional fields with defaults
    if optional_fields:
        for field, default in optional_fields.items():
            if field not in data:
                data[field] = default
    
    return data
