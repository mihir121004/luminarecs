"""
Test suite for LuminaRecs API endpoints.

Run tests with: python manage.py test platform_engine
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.conf import settings
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from platform_engine.models import (
    Movie, Review, InteractionTelemetry, UserTasteProfile, Wishlist, WatchHistory,
)
from platform_engine.utils.validators import InputValidator
from django.core.exceptions import ValidationError


class InputValidatorTestCase(TestCase):
    """Tests for input validation utilities"""
    
    def test_validate_search_query_valid(self):
        """Test valid search query"""
        query = "inception"
        result = InputValidator.validate_search_query(query)
        self.assertEqual(result, "inception")
    
    def test_validate_search_query_empty(self):
        """Test empty search query raises error"""
        with self.assertRaises(ValidationError):
            InputValidator.validate_search_query("")
    
    def test_validate_search_query_too_long(self):
        """Test query exceeding max length"""
        query = "a" * 300
        with self.assertRaises(ValidationError):
            InputValidator.validate_search_query(query)
    
    def test_validate_integer_id_valid(self):
        """Test valid integer ID"""
        result = InputValidator.validate_integer_id(123)
        self.assertEqual(result, 123)
    
    def test_validate_integer_id_invalid(self):
        """Test invalid integer ID"""
        with self.assertRaises(ValidationError):
            InputValidator.validate_integer_id("not_an_int")
    
    def test_validate_pagination_params_valid(self):
        """Test valid pagination parameters"""
        page, size = InputValidator.validate_pagination_params("1", "20")
        self.assertEqual(page, 1)
        self.assertEqual(size, 20)
    
    def test_validate_pagination_params_invalid_page(self):
        """Test invalid page number"""
        with self.assertRaises(ValidationError):
            InputValidator.validate_pagination_params("0", "20")
    
    def test_validate_rating_valid(self):
        """Test valid rating"""
        result = InputValidator.validate_rating(7.5)
        self.assertEqual(result, 7.5)
    
    def test_validate_rating_out_of_range(self):
        """Test rating out of range"""
        with self.assertRaises(ValidationError):
            InputValidator.validate_rating(11)


class MovieAPITestCase(APITestCase):
    """Tests for Movie API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create test movies
        self.movie1 = Movie.objects.create(
            tmdb_id=10001,
            title="Test Movie 1",
            overview="A test movie",
            genres="Action,Drama",
            director="Test Director",
            vote_average=8.5,
            popularity_score=100,
        )
        
        self.movie2 = Movie.objects.create(
            tmdb_id=10002,
            title="Test Movie 2",
            overview="Another test movie",
            genres="Comedy,Romance",
            director="Another Director",
            vote_average=7.2,
            popularity_score=50,
        )
    
    def test_get_all_movies(self):
        """Test retrieving all movies"""
        response = self.client.get(reverse("movie-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_get_movie_detail_valid(self):
        """Test retrieving movie details"""
        response = self.client.get(reverse("movie-detail", args=[self.movie1.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.movie1.id)
    
    def test_search_movies_valid(self):
        """Test movie search"""
        response = self.client.get(reverse("movie-search"), {"q": "Test Movie 1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], self.movie1.id)

    def test_tracking_requires_an_authenticated_user(self):
        response = self.client.post(
            reverse("track-interaction"),
            {"movie_id": self.movie1.id, "interaction_type": "VIEW"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticationTestCase(APITestCase):
    """Tests for authentication"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_user_creation(self):
        """Test user can be created"""
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertTrue(UserTasteProfile.objects.filter(user=self.user).exists())

    def test_signup_creates_one_taste_profile(self):
        response = self.client.post(reverse("signup"), {
            "username": "newuser",
            "email": "new@example.com",
            "password": "long-enough-test-password",
        })
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        user = User.objects.get(username="newuser")
        self.assertEqual(UserTasteProfile.objects.filter(user=user).count(), 1)


class SecurityHeadersTestCase(TestCase):
    """Tests for security headers"""
    
    def setUp(self):
        """Set up test client"""
        self.client = Client()
    
    def test_cors_headers_restricted(self):
        """Test that CORS is properly restricted"""
        # CORS should only allow specific origins
        if not settings.DEBUG:
            self.assertFalse(settings.CORS_ALLOW_ALL_ORIGINS)


class PublicPageSmokeTestCase(TestCase):
    """Ensure public pages render and their templates resolve all URL names."""

    def test_public_pages_render(self):
        for url_name in (
            "lockscreen", "landing", "login", "signup", "homepage", "discover", "trailers",
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, status.HTTP_200_OK)


class AuthenticatedPageSmokeTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("viewer", password="test-password-123")
        self.movie = Movie.objects.create(tmdb_id=20001, title="Test Feature")
        self.client.force_login(self.user)

    def test_profile_and_watch_history_render_for_a_new_user(self):
        for url_name in ("profile", "watch_history"):
            with self.subTest(url_name=url_name):
                self.assertEqual(self.client.get(reverse(url_name)).status_code, status.HTTP_200_OK)

    def test_wishlist_requires_post_and_can_be_updated(self):
        url = reverse("add_to_wishlist", args=[self.movie.id])
        self.assertEqual(self.client.get(url).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        response = self.client.post(url)
        self.assertRedirects(response, reverse("wishlist"))
        self.assertTrue(Wishlist.objects.filter(user=self.user, movie=self.movie).exists())


class WatchHistoryPaginationTestCase(TestCase):
    """Tests for watch history pagination."""

    def setUp(self):
        self.user = User.objects.create_user("paginator", password="test-password-123")
        self.client.force_login(self.user)
        # Create 15 movies so pagination (12 per page) yields 2 pages
        for i in range(15):
            movie = Movie.objects.create(tmdb_id=30000 + i, title=f"Movie {i}")
            WatchHistory.objects.create(user=self.user, movie=movie)

    def test_watch_history_is_paginated(self):
        response = self.client.get(reverse("watch_history"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.context["page_obj"]), 12)
        self.assertTrue(response.context["page_obj"].has_next())

    def test_watch_history_second_page(self):
        response = self.client.get(reverse("watch_history"), {"page": 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.context["page_obj"]), 3)


class MovieDetailsWatchHistoryTestCase(TestCase):
    """Tests that movie_details does not inflate watch history on GET."""

    def setUp(self):
        self.user = User.objects.create_user("viewer2", password="test-password-123")
        self.movie = Movie.objects.create(tmdb_id=40001, title="No Inflation")
        self.client.force_login(self.user)

    def test_get_does_not_create_watch_history(self):
        self.client.get(reverse("movie_details", args=[self.movie.id]))
        self.assertFalse(
            WatchHistory.objects.filter(user=self.user, movie=self.movie).exists()
        )

    def test_post_creates_watch_history(self):
        self.client.post(
            reverse("movie_details", args=[self.movie.id]),
            {"rating": 8, "comment": "Great"},
        )
        self.assertTrue(
            WatchHistory.objects.filter(user=self.user, movie=self.movie).exists()
        )


class HybridRecommendationsTestCase(TestCase):
    """Tests for the hybrid recommendation engine."""

    def setUp(self):
        self.user = User.objects.create_user("hybrid", password="test-password-123")
        self.movie = Movie.objects.create(
            tmdb_id=50001,
            title="Hybrid Test",
            genres="Action,Drama",
            vote_average=8.0,
            popularity_score=100,
        )

    def test_hybrid_recommendations_returns_list(self):
        from platform_engine.ml_engine.hybrid_engine import hybrid_recommendations
        results = hybrid_recommendations(self.user, limit=5)
        self.assertIsInstance(results, list)


if __name__ == '__main__':
    import unittest
    unittest.main()
