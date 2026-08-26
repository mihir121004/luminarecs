# filepath: platform_engine/urls.py
from django.urls import path
from .views import (
    get_all_movies_stream,
    get_movie_detail,
    get_vector_recommendations_endpoint,
    movie_search_api,
    interaction_tracking_api,
)

urlpatterns = [
    path("movies/", get_all_movies_stream, name="movie-list"),
    path("movies/<int:movie_id>/", get_movie_detail, name="movie-detail"),
    path("movies/<int:movie_id>/recommendations/", get_vector_recommendations_endpoint, name="movie-recommendations"),
    path("track/", interaction_tracking_api, name="track-interaction"),
    path("search/", movie_search_api, name="movie-search"),
]
