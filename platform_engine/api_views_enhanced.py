"""
Enhanced API views with input validation, error handling, and proper logging.
This module should be merged into api_views.py or used as a reference for refactoring.
"""

import logging
from typing import Optional, Dict, Any, List

from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

from platform_engine.utils.validators import InputValidator, validate_request_data
from platform_engine.utils.exceptions import custom_exception_handler
from platform_engine.utils.logging import log_api_request, log_execution, app_logger, api_logger
from platform_engine.models import (
    Movie, Recommendation, InteractionTelemetry, WatchHistory, Review, Wishlist
)
from platform_engine.ml_engine.recommender import get_recommendations
from platform_engine.ml_engine.semantic_recommender import semantic_recommendations

logger = logging.getLogger(__name__)


# =====================================================
# RATE LIMITING
# =====================================================

class StandardUserRateThrottle(UserRateThrottle):
    """Rate limit: 1000 requests per hour for authenticated users"""
    scope = 'user'
    rate = '1000/hour'


class StandardAnonRateThrottle(AnonRateThrottle):
    """Rate limit: 100 requests per hour for anonymous users"""
    scope = 'anon'
    rate = '100/hour'


# =====================================================
# REST API ENDPOINTS - MOVIES
# =====================================================

@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([StandardAnonRateThrottle])
@log_api_request
def get_all_movies_stream(request):
    """
    Return paginated list of top movies ordered by popularity.
    
    Query Parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20, max: 100)
        - sort: Sort order (popularity, rating, year) (default: popularity)
    
    Returns:
        List of movies with metadata
    """
    try:
        # Validate pagination parameters
        page = request.query_params.get('page', '1')
        page_size = request.query_params.get('page_size', '20')
        sort = request.query_params.get('sort', 'popularity')
        
        page_num, size = InputValidator.validate_pagination_params(page, page_size)
        
        # Validate sort parameter
        valid_sorts = {
            'popularity': '-popularity_score',
            'rating': '-vote_average',
            'year': '-release_year',
        }
        sort_field = valid_sorts.get(sort.lower(), '-popularity_score')
        
        # Query movies
        offset = (page_num - 1) * size
        movies = Movie.objects.order_by(sort_field)[offset:offset + size]
        total_count = Movie.objects.count()
        
        # Build response
        data = [
            {
                "id": movie.id,
                "title": movie.title,
                "poster_url": movie.poster_url,
                "release_year": movie.release_year,
                "rating": float(movie.vote_average) if movie.vote_average else 0,
                "popularity": float(movie.popularity_score) if movie.popularity_score else 0,
            }
            for movie in movies
        ]
        
        api_logger.info("Movies stream retrieved", extra={
            'page': page_num,
            'page_size': size,
            'total': total_count,
            'sort': sort,
        })
        
        return Response({
            'success': True,
            'data': data,
            'pagination': {
                'page': page_num,
                'page_size': size,
                'total': total_count,
                'has_next': offset + size < total_count,
            }
        })
        
    except ValueError as e:
        logger.warning(f"Invalid pagination parameters: {e}")
        return Response({
            'success': False,
            'error': {
                'code': 'INVALID_PARAMETERS',
                'message': str(e),
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error retrieving movies")
        return Response({
            'success': False,
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'An error occurred while retrieving movies',
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([StandardAnonRateThrottle])
@log_api_request
def get_movie_detail(request, movie_id: int):
    """
    Get complete details for a specific movie.
    
    Args:
        movie_id: Movie ID (path parameter)
    
    Returns:
        Complete movie details including cast, director, genres, etc.
    """
    try:
        # Validate movie_id
        movie_id = InputValidator.validate_integer_id(movie_id)
        
        movie = get_object_or_404(Movie, id=movie_id)
        
        # Build response with proper type casting
        response_data = {
            "id": movie.id,
            "title": movie.title,
            "overview": movie.overview or "",
            "genres": movie.genres or "",
            "director": movie.director or "",
            "cast": getattr(movie, "cast_data", None),
            "poster_url": movie.poster_url or "",
            "backdrop_url": getattr(movie, "backdrop_url", None),
            "release_year": movie.release_year or 0,
            "rating": float(movie.vote_average) if movie.vote_average else 0,
            "popularity": float(movie.popularity_score) if movie.popularity_score else 0,
            "budget": movie.budget or 0,
            "revenue": movie.revenue or 0,
            "runtime": movie.runtime or 0,
        }
        
        api_logger.info(f"Movie detail retrieved: {movie.title}")
        
        return Response({
            'success': True,
            'data': response_data
        })
        
    except ValueError as e:
        logger.warning(f"Invalid movie_id: {movie_id}")
        return Response({
            'success': False,
            'error': {
                'code': 'INVALID_ID',
                'message': 'Invalid movie ID format',
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception(f"Error retrieving movie {movie_id}")
        return Response({
            'success': False,
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'An error occurred while retrieving movie details',
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([StandardAnonRateThrottle])
@log_api_request
def search_movies(request):
    """
    Search movies by title, director, genres, or overview.
    
    Query Parameters:
        - q: Search query (required, max 255 characters)
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20, max: 100)
    
    Returns:
        List of matching movies
    """
    try:
        # Validate search query
        query = request.query_params.get("q", "").strip()
        query = InputValidator.validate_search_query(query)
        
        # Validate pagination
        page = request.query_params.get('page', '1')
        page_size = request.query_params.get('page_size', '20')
        page_num, size = InputValidator.validate_pagination_params(page, page_size)
        
        # Search movies
        offset = (page_num - 1) * size
        movies_query = Movie.objects.filter(
            Q(title__icontains=query)
            | Q(genres__icontains=query)
            | Q(director__icontains=query)
            | Q(overview__icontains=query)
        ).order_by("-popularity_score")
        
        total_count = movies_query.count()
        movies = movies_query[offset:offset + size]
        
        results = [
            {
                "id": movie.id,
                "title": movie.title,
                "poster_url": movie.poster_url,
                "year": movie.release_year or 0,
                "rating": float(movie.vote_average) if movie.vote_average else 0,
            }
            for movie in movies
        ]
        
        api_logger.info(f"Search performed", extra={
            'query': query,
            'results': total_count,
            'page': page_num,
        })
        
        return Response({
            'success': True,
            'data': results,
            'pagination': {
                'page': page_num,
                'page_size': size,
                'total': total_count,
                'has_next': offset + size < total_count,
            }
        })
        
    except ValueError as e:
        logger.warning(f"Invalid search parameters: {e}")
        return Response({
            'success': False,
            'error': {
                'code': 'INVALID_PARAMETERS',
                'message': str(e),
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error searching movies")
        return Response({
            'success': False,
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'An error occurred while searching',
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =====================================================
# REST API ENDPOINTS - RECOMMENDATIONS
# =====================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([StandardUserRateThrottle])
@log_api_request
def get_user_recommendations(request):
    """
    Get personalized recommendations for the authenticated user.
    
    Query Parameters:
        - limit: Number of recommendations (default: 12, max: 50)
        - algorithm: Recommendation algorithm (content, semantic, hybrid) (default: hybrid)
    
    Returns:
        List of recommended movies with scores and reasons
    """
    try:
        user = request.user
        limit = int(request.query_params.get('limit', '12'))
        algorithm = request.query_params.get('algorithm', 'hybrid').lower()
        
        # Validate limit
        if limit < 1 or limit > 50:
            limit = 12
        
        # Validate algorithm
        valid_algorithms = ['content', 'semantic', 'hybrid']
        if algorithm not in valid_algorithms:
            algorithm = 'hybrid'
        
        # Get recommendations
        recommendations = Recommendation.objects.filter(
            user=user
        ).select_related(
            "movie"
        ).order_by("-score")[:limit]
        
        data = []
        for item in recommendations:
            data.append({
                "id": item.movie.id,
                "title": item.movie.title,
                "poster": item.movie.poster_url,
                "score": float(item.score) if item.score else 0,
                "reason": item.reason or "Recommended based on your preferences",
                "algorithm": item.algorithm if hasattr(item, 'algorithm') else algorithm,
            })
        
        api_logger.info(f"User recommendations retrieved", extra={
            'user_id': user.id,
            'count': len(data),
            'algorithm': algorithm,
        })
        
        return Response({
            'success': True,
            'data': data,
        })
        
    except Exception as e:
        logger.exception(f"Error retrieving recommendations for user {user.id}")
        return Response({
            'success': False,
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'An error occurred while retrieving recommendations',
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =====================================================
# REST API ENDPOINTS - INTERACTIONS
# =====================================================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([StandardUserRateThrottle])
@log_api_request
def track_interaction(request):
    """
    Record a user interaction (watch, like, rating, etc).
    
    Request Body:
    {
        "movie_id": 123,
        "interaction_type": "WATCH",  # CLICK, WATCH, TRAILER, RATING, VIEW, WISHLIST
        "watch_duration": 3600  # Optional: duration in seconds
    }
    
    Returns:
        Success confirmation
    """
    try:
        # Validate required fields
        request_data = {
            'movie_id': request.data.get('movie_id'),
            'interaction_type': request.data.get('interaction_type', 'VIEW'),
        }
        
        if not request_data['movie_id']:
            return Response({
                'success': False,
                'error': {
                    'code': 'MISSING_FIELD',
                    'message': 'movie_id is required',
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate movie_id
        movie_id = InputValidator.validate_integer_id(request_data['movie_id'])
        movie = get_object_or_404(Movie, id=movie_id)
        
        # Validate interaction type
        interaction_type = InputValidator.validate_interaction_type(
            request_data['interaction_type']
        )
        
        # Optional: validate watch_duration
        watch_duration = request.data.get('watch_duration', 0)
        try:
            watch_duration = int(watch_duration)
            if watch_duration < 0:
                watch_duration = 0
        except (ValueError, TypeError):
            watch_duration = 0
        
        # Create interaction record
        interaction = InteractionTelemetry.objects.create(
            user=request.user,
            movie=movie,
            interaction_type=interaction_type,
            watch_duration=watch_duration,
        )
        
        api_logger.info(f"Interaction tracked", extra={
            'user_id': request.user.id,
            'movie_id': movie_id,
            'interaction_type': interaction_type,
        })
        
        return Response({
            'success': True,
            'message': 'Interaction recorded successfully',
            'data': {
                'id': interaction.id,
                'timestamp': interaction.timestamp.isoformat() if hasattr(interaction, 'timestamp') else None,
            }
        }, status=status.HTTP_201_CREATED)
        
    except ValueError as e:
        logger.warning(f"Invalid interaction data: {e}")
        return Response({
            'success': False,
            'error': {
                'code': 'INVALID_DATA',
                'message': str(e),
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error tracking interaction")
        return Response({
            'success': False,
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'An error occurred while tracking interaction',
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([StandardUserRateThrottle])
@log_api_request
def add_to_wishlist(request):
    """
    Add a movie to user's wishlist.
    
    Request Body:
    {
        "movie_id": 123
    }
    """
    try:
        movie_id = request.data.get('movie_id')
        
        if not movie_id:
            return Response({
                'success': False,
                'error': {
                    'code': 'MISSING_FIELD',
                    'message': 'movie_id is required',
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate movie_id
        movie_id = InputValidator.validate_integer_id(movie_id)
        movie = get_object_or_404(Movie, id=movie_id)
        
        # Add to wishlist
        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user,
            movie=movie
        )
        
        api_logger.info(f"Movie added to wishlist", extra={
            'user_id': request.user.id,
            'movie_id': movie_id,
        })
        
        return Response({
            'success': True,
            'message': 'Added to wishlist' if created else 'Already in wishlist',
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
    except ValueError as e:
        return Response({
            'success': False,
            'error': {
                'code': 'INVALID_DATA',
                'message': str(e),
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Error adding to wishlist")
        return Response({
            'success': False,
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'An error occurred',
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
