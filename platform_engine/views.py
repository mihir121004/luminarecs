import logging
import os
import urllib.parse

import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings
from django.core.cache import cache
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Movie,
    Genre,
    Actor,
    Wishlist,
    Review,
    WatchHistory,
    Profile,
    UserTasteProfile,
    InteractionTelemetry,
    Recommendation,
    UserFeedback,
    WatchProgress,
    Collection
)
from .ml_engine.recommender import get_recommendations
from .ml_engine.hybrid_engine import hybrid_recommendations
from .ai.taste_engine import update_user_taste_profile
from platform_engine.ml_engine.semantic_recommender import semantic_recommendations
from platform_engine.models import AIModelVersion
from .ai_engine import generate_user_ai_profile

logger = logging.getLogger(__name__)

# =====================================================
# REST API ENDPOINTS
# =====================================================


@api_view(["GET"])
def get_all_movies_stream(request):
    """Return top movies ordered by popularity."""
    movies = Movie.objects.all().order_by("-popularity_score")[:50]

    data = [
        {
            "id": movie.id,
            "tmdb_id": getattr(movie, "tmdb_id", None),
            "title": movie.title,
            "poster_url": movie.poster_url,
            "release_year": movie.release_year,
            "genres": movie.genres,
            "rating": movie.vote_average,
        }
        for movie in movies
    ]

    return Response(data)


@api_view(["GET"])
def get_movie_detail(request, movie_id):
    """Return complete movie details."""
    movie = get_object_or_404(Movie, id=movie_id)

    return Response(
        {
            "id": movie.id,
            "tmdb_id": getattr(movie, "tmdb_id", None),
            "title": movie.title,
            "overview": movie.overview,
            "genres": movie.genres,
            "director": movie.director,
            "cast": getattr(movie, "cast_data", None),
            "poster_url": movie.poster_url,
            "backdrop_url": getattr(movie, "backdrop_url", None),
            "release_year": movie.release_year,
            "rating": movie.vote_average,
            "popularity": getattr(movie, "popularity_score", None),
        }
    )


@api_view(["GET"])
def search_movies(request):
    """
    Search movies API.

    Example:
    /api/search/?q=inception
    """
    query = request.GET.get("q", "").strip()

    if not query:
        return Response([])

    movies = (
        Movie.objects.filter(
            Q(title__icontains=query)
            | Q(genres__icontains=query)
            | Q(director__icontains=query)
            | Q(overview__icontains=query)
        )
        .order_by("-popularity_score")[:20]
    )

    results = [
        {
            "id": movie.id,
            "title": movie.title,
            "poster_url": movie.poster_url,
            "year": movie.release_year,
            "rating": movie.vote_average,
        }
        for movie in movies
    ]

    return Response(results)


@api_view(["GET"])
def get_vector_recommendations_endpoint(request, movie_id):
    """Content based recommendation API."""
    recommendations = get_recommendations(movie_id, limit=10)
    return Response(recommendations)


@api_view(["POST"])
def track_interaction(request):
    """
    Save user movie interaction.

    Payload:
    {
        movie_id: 1,
        interaction_type: "WATCH",
        watch_duration: 120
    }
    """
    movie_id = request.data.get("movie_id")
    interaction_type = request.data.get("interaction_type", "VIEW")
    watch_duration = request.data.get("watch_duration", 0)

    if not request.user.is_authenticated:
        return Response(
            {"success": False, "error": "Authentication is required"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    valid_interactions = {choice[0] for choice in InteractionTelemetry.TYPES}
    if interaction_type not in valid_interactions:
        return Response(
            {"success": False, "error": "Invalid interaction type"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        watch_duration = max(0, int(watch_duration))
    except (TypeError, ValueError):
        return Response(
            {"success": False, "error": "watch_duration must be a non-negative integer"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        movie = Movie.objects.get(id=movie_id)

        InteractionTelemetry.objects.create(
            user=request.user,
            movie=movie,
            interaction_type=interaction_type,
            watch_duration=watch_duration,
        )

        return Response({"success": True, "message": "Interaction saved"})

    except Movie.DoesNotExist:
        return Response(
            {"success": False, "error": "Movie not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    except Exception:
        return Response(
            {"success": False, "error": "Unable to save interaction"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# =====================================================
# PAGES & WEB VIEWS
# =====================================================


def lockscreen(request):
    return render(request, "lockscreen.html")


def landing(request):
    return render(request, "landing.html")

@login_required
def homepage(request):
    """Main LuminaRecs homepage."""

    movies = Movie.objects.all()

    recommendations = Recommendation.objects.none()

    if request.user.is_authenticated:
        recommendations = (
            Recommendation.objects.filter(user=request.user)
            .select_related("movie")
            .order_by("-score")[:12]
        )

    trending_movies = Movie.objects.order_by("-popularity_score")[:8]

    # Daily Pick Movie
    daily_pick_movie = Movie.objects.order_by("-popularity_score").first()

    daily_pick = None

    if daily_pick_movie:
        daily_pick = {
            "id": daily_pick_movie.id,
            "title": daily_pick_movie.title,
            "poster_url": getattr(daily_pick_movie, "poster_url", ""),
            "reason": (
                daily_pick_movie.overview[:250] + "..."
                if getattr(daily_pick_movie, "overview", None)
                else "A visually breathtaking cinematic masterpiece selected specially for your cinematic profile."
            ),
            "confidence": 98,
            "genre": (
                daily_pick_movie.genre.first().name
                if hasattr(daily_pick_movie, "genre")
                and daily_pick_movie.genre.exists()
                else "Featured Pick"
            ),
        }

    history = []

    if request.user.is_authenticated:
        history = (
            WatchHistory.objects.filter(
                user=request.user,
                completed=False
            )
            .select_related("movie")
            .order_by("-watched_at")[:6]
        )

    # AI Semantic Recommendations
    ai_recommendations = []

    try:
        if request.user.is_authenticated:

            last_watch = (
                WatchHistory.objects.filter(user=request.user)
                .select_related("movie")
                .order_by("-watched_at")
                .first()
            )

            if last_watch:
                ai_recommendations = semantic_recommendations(
                    last_watch.movie.id,
                    limit=8
                )

        elif daily_pick_movie:

            ai_recommendations = semantic_recommendations(
                daily_pick_movie.id,
                limit=8
            )

    except Exception as e:
        print(f"AI Recommendation Error: {e}")

    # User-specific stats for the hero section
    if request.user.is_authenticated:
        user_watched_count = WatchHistory.objects.filter(user=request.user).count()
    else:
        user_watched_count = 0

    context = {
        "recommendations": recommendations,
        "ai_recommendations": ai_recommendations,
        "trending_movies": trending_movies,
        "daily_pick": daily_pick,
        "history": history,
        "movies_watched": user_watched_count,
        "total_movies": movies.count(),
        "favorite_genre": "AI Generated",
        "recommendations_count": recommendations.count() if request.user.is_authenticated else 0,
        "accuracy": 96,
    }

    return render(request, "homepage.html", context)

@login_required
def personalized_recommendations(request):
    recommendations = hybrid_recommendations(request.user, limit=12)

    movies = [
        item["movie"] if isinstance(item, dict) and "movie" in item else item
        for item in recommendations
    ]

    return render(
        request,
        "recommendations.html",
        {"recommendations": recommendations, "movies": movies},
    )


# =====================================================
# GENRE / ACTOR / DIRECTOR PAGES
# =====================================================


def genre_movies(request, genre_name):

    # Convert URL slug to readable genre
    search_genre = genre_name.replace("-", " ")

    movies = (
        Movie.objects.filter(
            Q(genres__icontains=search_genre) |
            Q(genres__icontains=genre_name) |
            Q(genre__name__icontains=search_genre)
        )
        .distinct()
        .order_by("-vote_average", "-release_year")
    )

    # Pagination
    paginator = Paginator(movies, 12)

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "movies": page_obj,
        "page_obj": page_obj,
        "title": search_genre.title(),
        "description": f"Explore {search_genre.title()} movies recommended by LuminaRecs.",
    }

    return render(
        request,
        "genre_movies.html",
        context
    )
def actor_movies(request, actor_name):
    movies = (
        Movie.objects.filter(
            Q(cast_data__icontains=actor_name) | Q(actors__name__icontains=actor_name)
        )
        .distinct()
    )

    return render(
        request,
        "genre_movies.html",
        {
            "movies": movies,
            "title": actor_name,
            "description": f"Movies featuring {actor_name}",
        },
    )


def director_movies(request, director_name):
    movies = Movie.objects.filter(director__icontains=director_name)

    return render(
        request,
        "genre_movies.html",
        {
            "movies": movies,
            "title": director_name,
            "description": f"Movies directed by {director_name}",
        },
    )


def search_movies_page(request):
    query = request.GET.get("q", "").strip()
    results = Movie.objects.none()

    if query:
        results = (
            Movie.objects.filter(
                Q(title__icontains=query)
                | Q(overview__icontains=query)
                | Q(genres__icontains=query)
                | Q(director__icontains=query)
                | Q(tagline__icontains=query)
                | Q(cast_data__icontains=query)
            )
            .distinct()
            .order_by("-popularity_score")
        )

    trending_movies = Movie.objects.order_by("-popularity_score")[:8]
    recommended_movies = Movie.objects.order_by("-vote_average")[:8]

    return render(
        request,
        "search_results.html",
        {
            "query": query,
            "results": results,
            "result_count": results.count(),
            "trending_movies": trending_movies,
            "recommended_movies": recommended_movies,
        },
    )


# =====================================================
# AUTHENTICATION
# =====================================================


def _get_social_providers():
    """
    Return the OAuth providers that have API credentials configured in
    the environment, so login/signup pages only offer working options.
    """
    providers = []
    if all(
        os.getenv(key)
        for key in ("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", "SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET")
    ):
        providers.append({"name": "Google", "slug": "google-oauth2"})
    if all(os.getenv(key) for key in ("SOCIAL_AUTH_GITHUB_KEY", "SOCIAL_AUTH_GITHUB_SECRET")):
        providers.append({"name": "GitHub", "slug": "github"})
    return providers


@ensure_csrf_cookie  # always send a fresh csrftoken cookie on the login page
def login(request):
    # Preserve ?next= so protected views (e.g. /analytics/) return users to
    # where they were heading after a successful sign-in.
    next_url = request.GET.get("next") or request.POST.get("next") or ""

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            auth_login(request, user)
            # Only follow ?next= when it points back at this site (no open
            # redirects); otherwise fall back to the homepage.
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("homepage")

        messages.error(request, "Invalid username or password")

    return render(
        request,
        "login.html",
        {
            "oauth_providers": _get_social_providers(),
            "next": next_url,
        },
    )


def signup(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("signup")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("signup")

        user = User.objects.create_user(username=username, email=email, password=password)
        # With multiple AUTHENTICATION_BACKENDS configured (credentials +
        # Google/GitHub OAuth), Django requires an explicit backend when
        # logging in a user that was NOT obtained through authenticate().
        auth_login(
            request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        messages.success(request, "Account created successfully")
        return redirect("onboarding")

    return render(request, "signup.html", {"oauth_providers": _get_social_providers()})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("landing")


# =====================================================
# COLD-START ONBOARDING
# =====================================================


@login_required
def onboarding(request):
    """
    Cold-start onboarding: lets new users select favorite genres
    so the AI can provide personalized recommendations immediately,
    even before they have any watch history.
    """
    if request.method == "POST":
        selected_genres = request.POST.getlist("genres")

        if selected_genres:
            taste_profile, _ = UserTasteProfile.objects.get_or_create(
                user=request.user
            )
            taste_profile.favorite_genres = selected_genres
            taste_profile.personality = "Cinema Explorer"
            taste_profile.watching_style = "Balanced Cinema Explorer"
            taste_profile.preferred_experience = "Classic Cinema Experience"
            taste_profile.save()

            messages.success(
                request,
                "Preferences saved! LuminaRecs AI will personalize your recommendations.",
            )
            return redirect("homepage")

        messages.error(request, "Please select at least one genre.")

    # Common genres for selection
    common_genres = [
        "Action", "Adventure", "Animation", "Comedy", "Crime",
        "Documentary", "Drama", "Family", "Fantasy", "Horror",
        "Mystery", "Romance", "Sci-Fi", "Thriller",
    ]

    return render(
        request,
        "onboarding.html",
        {"common_genres": common_genres},
    )


# =====================================================
# USER FEATURES (WISHLIST & PROFILE)
# =====================================================


@login_required
def wishlist(request):
    """
    Wishlist Page
    - Search wishlist
    - Wishlist statistics
    - AI recommendations
    - User taste profile
    - Dynamic AI model accuracy
    """

    search = request.GET.get("search", "").strip()

    # =====================================================
    # WISHLIST MOVIES
    # =====================================================

    wishlist_qs = (
        Wishlist.objects
        .filter(user=request.user)
        .select_related("movie")
        .order_by("-created_at")
    )

    if search:
        wishlist_qs = wishlist_qs.filter(
            movie__title__icontains=search
        )

    wishlist_count = wishlist_qs.count()

    # Paginate wishlist movies
    paginator = Paginator(wishlist_qs, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    wishlist_movies = [item.movie for item in page_obj]

    # =====================================================
    # WATCH HISTORY STATS
    # =====================================================

    watched_count = (
        WatchHistory.objects
        .filter(
            user=request.user,
            completed=True
        )
        .count()
    )

    watched_movie_ids = (
        WatchHistory.objects
        .filter(
            user=request.user,
            completed=True
        )
        .values_list(
            "movie_id",
            flat=True
        )
    )

    pending_count = (
        Wishlist.objects
        .filter(user=request.user)
        .exclude(movie_id__in=watched_movie_ids)
        .count()
    )

    # =====================================================
    # USER AVERAGE RATING
    # =====================================================

    average_rating = (
        Review.objects
        .filter(user=request.user)
        .aggregate(avg=Avg("rating"))
        .get("avg")
    )

    average_rating = (
        round(average_rating, 1)
        if average_rating
        else 0
    )

    # =====================================================
    # FAVORITE GENRE
    # =====================================================

    genre_data = (
        Wishlist.objects
        .filter(user=request.user)
        .values("movie__genres")
        .annotate(total=Count("id"))
        .order_by("-total")
        .first()
    )

    favorite_genre = (
        genre_data["movie__genres"]
        if genre_data and genre_data["movie__genres"]
        else "Unknown"
    )

    # =====================================================
    # AI RECOMMENDATIONS
    # =====================================================

    recommendation_qs = (
        Recommendation.objects
        .filter(user=request.user)
        .select_related("movie")
        .order_by("-score")
    )

    ai_suggestions = [
        recommendation.movie
        for recommendation in recommendation_qs[:8]
    ]

    # Fallback recommendations
    if not ai_suggestions:

        wishlist_movie_ids = (
            Wishlist.objects
            .filter(user=request.user)
            .values_list("movie_id", flat=True)
        )

        ai_suggestions = (
            Movie.objects
            .exclude(id__in=wishlist_movie_ids)
            .order_by(
                "-vote_average",
                "-popularity_score"
            )[:8]
        )

    # =====================================================
    # USER TASTE PROFILE
    # =====================================================

    taste_profile = (
        UserTasteProfile.objects
        .filter(user=request.user)
        .first()
    )

    # =====================================================
    # ACTIVE AI MODEL
    # =====================================================

    active_model = (
        AIModelVersion.objects
        .filter(is_active=True)
        .first()
    )

    recommendation_accuracy = (
        round(active_model.accuracy, 1)
        if active_model
        else 96
    )

    # =====================================================
    # EXTRA INSIGHTS
    # =====================================================

    most_recent_wishlist = (
        Wishlist.objects
        .filter(user=request.user)
        .select_related("movie")
        .first()
    )

    latest_movie = (
        most_recent_wishlist.movie
        if most_recent_wishlist
        else None
    )
    taste_profile = UserTasteProfile.objects.filter(
        user=request.user
    ).first()

    personality = (
        taste_profile.personality
        if taste_profile
        else "Cinema Explorer"
    )
    watching_style = (
        taste_profile.watching_style if taste_profile else "Balanced Viewer"
    )
    # =====================================================
    # CONTEXT
    # =====================================================

    context = {
        # wishlist
        "wishlist_movies": wishlist_movies,
        "wishlist_count": wishlist_count,

        # stats
        "watched_count": watched_count,
        "pending_count": pending_count,
        "average_rating": average_rating,
        "favorite_genre": favorite_genre,

        # ai
        "ai_suggestions": ai_suggestions,
        "recommendation_accuracy": recommendation_accuracy,

        # profile
        "taste_profile": taste_profile,
        "personality": personality,
        "watching_style": watching_style,

        # extras
        "latest_movie": latest_movie,
    }

    return render(
        request,
        "wishlist.html",
        context
    )
@login_required
@require_POST
def add_to_wishlist(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    Wishlist.objects.get_or_create(user=request.user, movie=movie)
    return redirect("wishlist")


@login_required
@require_POST
def remove_from_wishlist(request, movie_id):
    Wishlist.objects.filter(user=request.user, movie_id=movie_id).delete()
    return redirect("wishlist")


# =====================================================
# PROFILE - AI PROFILE SYSTEM
# =====================================================


@login_required
def profile(request):
    """
    LuminaRecs AI Cinematic Profile Dashboard.

    Displays user statistics, AI personality insights, watch history,
    and personalized analytics with radar chart data.
    """
    user = request.user
    ai_profile=generate_user_ai_profile(user)
    ai_summary=ai_profile.ai_summary

    # User Profiles
    profile, _ = Profile.objects.get_or_create(user=user)
    taste_profile, _ = UserTasteProfile.objects.get_or_create(user=user)

    avatar_url = (
        f"https://api.dicebear.com/9.x/{profile.avatar_style}/svg"
        f"?seed={profile.avatar_seed}"
    )

    # Watch History
    watch_history = (
        WatchHistory.objects.filter(user=request.user)
        .select_related("movie")
        .order_by("-watched_at")
    )

    continue_watching = WatchProgress.objects.filter(
        user=request.user
    ).select_related("movie")
    recent_watch_history = watch_history[:12]

    # Basic Stats
    movies_watched = watch_history.count()
    completed_movies = watch_history.filter(completed=True).count()
    wishlist_count = Wishlist.objects.filter(user=user).count()
    reviews_count = Review.objects.filter(user=user).count()
    recommendations_count = Recommendation.objects.filter(user=user).count()

    average_rating = (
        Review.objects.filter(user=user).aggregate(avg=Avg("rating")).get("avg") or 0
    )
    average_rating = round(average_rating, 1)

    # Favorite Genres
    favorite_genres = [
        {
            "name": genre,
            "movies": Movie.objects.filter(
                genres__icontains=genre, watch_history__user=user
            )
            .distinct()
            .count(),
        }
        for genre in (taste_profile.favorite_genres or [])
    ]

    # Favorite Actors
    favorite_actors = [
        {"name": actor, "match": max(75, 95 - index)}
        for index, actor in enumerate(taste_profile.favorite_actors[:5])
    ]

    # Favorite Directors
    favorite_directors = [
        {"name": director, "match": max(80, 96 - index)}
        for index, director in enumerate(taste_profile.favorite_directors[:5])
    ]

    # Profile Completion Score
    completion_fields = [
        user.username,
        user.first_name,
        user.last_name,
        user.email,
        profile.bio,
        taste_profile.favorite_genres,
        movies_watched > 0,
        reviews_count > 0,
    ]

    completion_weights = [10, 15, 10, 15, 15, 15, 10, 10]
    completion_score = sum(
        weight for field, weight in zip(completion_fields, completion_weights) if field
    )
    profile_completion = min(completion_score, 100)

    # AI Radar Analysis
    radar_scores = {
        "story": 50,
        "visual": 50,
        "emotion": 50,
        "action": 50,
        "complexity": 50,
    }

    watched_movies = Movie.objects.filter(watch_history__user=user).distinct()

    for movie in watched_movies:
        genres = movie.genres.lower() if movie.genres else ""

        if "action" in genres:
            radar_scores["action"] += 4
        if "drama" in genres:
            radar_scores["emotion"] += 4
        if "thriller" in genres:
            radar_scores["complexity"] += 4
        if movie.vote_average >= 8:
            radar_scores["story"] += 4
        if movie.popularity_score >= 100:
            radar_scores["visual"] += 4

    radar_data = {key: min(score, 100) for key, score in radar_scores.items()}

    # AI Taste Score
    taste_score = round(
        (
            profile_completion * 0.30
            + min(movies_watched, 100) * 0.25
            + min(reviews_count * 5, 100) * 0.20
            + min(wishlist_count * 2, 100) * 0.15
            + min(recommendations_count, 100) * 0.10
        ),
        1,
    )

    # Recent Activity
    recent_activities = [f"🎬 Watched {item.movie.title}" for item in recent_watch_history[:5]]

    # Recommendation Accuracy
    recommendation_accuracy = min(70 + reviews_count + wishlist_count, 99)

    # Context
    context = {
        "profile": profile,
        "avatar_url": avatar_url,
        "taste_profile": taste_profile,
        "movies_watched": movies_watched,
        "completed_movies": completed_movies,
        "wishlist_count": wishlist_count,
        "reviews_count": reviews_count,
        "recommendations_count": recommendations_count,
        "average_rating": average_rating,
        "favorite_genres": favorite_genres,
        "favorite_actors": favorite_actors,
        "favorite_directors": favorite_directors,
        "watch_history": recent_watch_history,
        "continue_watching": continue_watching,
        "taste_score": taste_score,
        "movie_personality": ai_profile.personality,
        "watching_style": taste_profile.watching_style,
        "preferred_experience": taste_profile.preferred_experience,
        "profile_completion": profile_completion,
        "radar_data": radar_data,
        "recent_activities": recent_activities,
        "recommendation_accuracy": recommendation_accuracy,
        "ai_summary":ai_summary,
        "movies_analyzed": ai_profile.movie_analyzed,
        "accuracy":ai_profile.accuracy,
    }

    return render(request, "profile.html", context)


@login_required
def edit_profile(request):
    user_profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        request.user.first_name = request.POST.get("first_name", request.user.first_name)
        request.user.last_name = request.POST.get("last_name", request.user.last_name)
        request.user.email = request.POST.get("email", request.user.email)
        request.user.save()

        user_profile.bio = request.POST.get("bio", user_profile.bio)
        user_profile.avatar_style = request.POST.get("avatar_style", user_profile.avatar_style)
        user_profile.avatar_seed = request.POST.get("avatar_seed", user_profile.avatar_seed)
        user_profile.save()

        messages.success(request, "Profile updated successfully")

    return redirect("profile")


# =====================================================
# DISCOVER PAGE
# =====================================================


def discover(request):
    award_winners = Movie.objects.filter(vote_average__gte=8).order_by("-vote_average")[:12]
    trending_movies = Movie.objects.order_by("-popularity_score")[:12]
    recommendations = Movie.objects.order_by("-vote_average")[:12]
    hidden_gems = Movie.objects.filter(
        vote_average__gte=7.5, popularity_score__lt=50
    ).order_by("-vote_average")[:12]
    ai_report = {
        "summary": (
            f"LuminaRecs analyzed {Movie.objects.count()} movies "
            f"across multiple genres and popularity signals to generate "
            f"intelligent discovery recommendations."
        )
    }

    # Curated collections: DB rows first, then CURATED_FALLBACK_COLLECTIONS
    # for slugs with no DB row. Template renders one loop (no hardcoded cards).
    db_collections = list(
        Collection.objects.prefetch_related("movies")
    )
    existing_slugs = {c.slug for c in db_collections}
    fallback_collections = [
        c for c in CURATED_FALLBACK_COLLECTIONS
        if c["slug"] not in existing_slugs
    ]
    collections = db_collections + fallback_collections

    return render(
        request,
        "discover.html",
        {
            "award_winners": award_winners,
            "trending_movies": trending_movies,
            "recommendations": recommendations,
            "hidden_gems": hidden_gems,
            "ai_report": ai_report,
            "collections": collections,
            "confidence": 96,
        },
    )


def trailers(request):
    """Browse movies that include a trailer key in the catalog."""
    movies = Movie.objects.exclude(trailer_key__isnull=True).exclude(trailer_key="")
    return render(
        request,
        "genre_movies.html",
        {
            "movies": movies.order_by("-popularity_score"),
            "title": "Trailers",
            "description": "Watch trailers from the LuminaRecs catalog.",
        },
    )


# =====================================================
# COLLECTION MOVIES
# =====================================================


def collection_movies(request, slug):

    # Try database collection first
    collection = Collection.objects.filter(
        slug=slug
    ).first()


    # Shared curated fallback metadata for this slug (None for unknown slugs).
    fallback_meta = next(
        (c for c in CURATED_FALLBACK_COLLECTIONS if c["slug"] == slug),
        None,
    )


    # If database collection exists
    if collection:

        movies = collection.movies.all().order_by(
            "-vote_average"
        )

        title = collection.name
        description = collection.description


        # Similar collections
        similar_collections = (
            Collection.objects
            .exclude(id=collection.id)
            .prefetch_related("movies")
            [:4]
    )


    # Fallback collections
    elif slug == "hidden-gems":

        movies = Movie.objects.filter(
            popularity_score__lt=50
        ).order_by(
            "-vote_average"
        )

        # Sourced from CURATED_FALLBACK_COLLECTIONS.
        title = fallback_meta["name"]

        description = fallback_meta["description"]

        similar_collections = Collection.objects.all()[:4]


    elif slug == "space-odyssey":

        movies = Movie.objects.filter(
            genres__icontains="Science"
        ).order_by(
            "-vote_average"
        )

        # Sourced from CURATED_FALLBACK_COLLECTIONS.
        title = fallback_meta["name"]

        description = fallback_meta["description"]

        similar_collections = Collection.objects.all()[:4]


    elif slug == "mind-bending":

        movies = Movie.objects.filter(
            Q(genres__icontains="Thriller") |
            Q(genres__icontains="Mystery")
        ).order_by(
            "-vote_average"
        )

        # Sourced from CURATED_FALLBACK_COLLECTIONS.
        title = fallback_meta["name"]

        description = fallback_meta["description"]

        similar_collections = Collection.objects.all()[:4]


    else:

        movies = Movie.objects.none()

        title = "Collection Not Found"

        description = (
            "This collection does not exist."
        )

        similar_collections = Collection.objects.all()[:4]



    # Pagination

    paginator = Paginator(
        movies,
        20
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )


    context = {

        "title": title,

        "description": description,


        "movies": page_obj,

        "page_obj": page_obj,


        "total_movies": paginator.count,

        "total_pages": paginator.num_pages,


        "similar_collections": similar_collections,

    }


    return render(
        request,
        "collection_movies.html",
        context
    )

# =====================================================
# CURATED FALLBACK COLLECTIONS
# =====================================================
# Single source of truth for the "virtual" curated collections that exist
# only as URL slugs (no Collection database row). Reused by `discover`,
# `collection_movies` and `collections_list` so every curated title and
# description lives in exactly one place.
CURATED_FALLBACK_COLLECTIONS = [
    {
        "slug": "hidden-gems",
        "name": "Hidden Gems",
        "description": "Underrated masterpieces waiting to be discovered.",
        "icon": "💎",
    },
    {
        "slug": "space-odyssey",
        "name": "Space Odyssey",
        "description": "Epic adventures beyond Earth and unknown galaxies.",
        "icon": "🚀",
    },
    {
        "slug": "mind-bending",
        "name": "Mind Bending Cinema",
        "description": "Movies that challenge reality and imagination.",
        "icon": "🌀",
    },
]


# =====================================================
# COLLECTIONS LISTING
# =====================================================


def collections_list(request):
    """Browse all curated movie collections."""
    db_collections = (
        Collection.objects
        .prefetch_related("movies")
        .order_by("name")
    )

    # Fallback curated collections that exist only as URL slugs
    # Reuse the single shared curated fallback constant (no inline dup).
    fallback_collections = list(CURATED_FALLBACK_COLLECTIONS)

    existing_slugs = set(db_collections.values_list("slug", flat=True))
    fallback_collections = [
        c for c in fallback_collections if c["slug"] not in existing_slugs
    ]

    context = {
        "db_collections": db_collections,
        "fallback_collections": fallback_collections,
        "total_movies": Movie.objects.count(),
    }

    return render(request, "collections.html", context)


# =====================================================
# OTT / WATCH PROVIDERS (Where To Watch)
# =====================================================

# api.tmdb.org is TMDB's official API mirror; some ISPs (notably in India)
# reset TLS connections to api.themoviedb.org, so both are tried in order.
TMDB_API_HOSTS = (
    "https://api.themoviedb.org/3",
    "https://api.tmdb.org/3",
)
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/"

# Availability categories returned by TMDB watch/providers, mapped to
# display labels. Order matters: subscription first, then rent/buy.
AVAILABILITY_LABELS = (
    ("flatrate", "Subscription"),
    ("rent", "Rent"),
    ("buy", "Buy"),
)

# Direct in-platform search links for well-known OTT services.
# {query} is replaced with the URL-encoded movie title. Providers that
# are not listed fall back to the movie's JustWatch availability page,
# which lists every platform carrying it.
OTT_PLATFORM_LINKS = {
    "netflix": "https://www.netflix.com/search?q={query}",
    "prime video": "https://www.primevideo.com/search/?phrase={query}",
    "amazon prime video": "https://www.primevideo.com/search/?phrase={query}",
    "disney plus": "https://www.disneyplus.com/search?q={query}",
    "hotstar": "https://www.hotstar.com/in/explore?search_query={query}",
    "jiohotstar": "https://www.hotstar.com/in/explore?search_query={query}",
    "jiocinema": "https://www.jiocinema.com/search/{query}",
    "zee5": "https://www.zee5.com/search?q={query}",
    "sony liv": "https://www.sonyliv.com/search?searchTerm={query}",
    "apple tv": "https://tv.apple.com/search?term={query}",
    "apple tv+": "https://tv.apple.com/search?term={query}",
    "apple tv store": "https://tv.apple.com/search?term={query}",
    "google play movies": "https://play.google.com/store/search?q={query}&c=movies",
    "youtube": "https://www.youtube.com/results?search_query={query}+full+movie",
    "mubi": "https://mubi.com/en/search/films?query={query}",
    "mx player": "https://www.mxplayer.in/search?q={query}",
}


def _get_ott_platforms(movie):
    """
    Return the OTT platforms currently streaming this movie using TMDB's
    watch/providers endpoint (JustWatch data) for the configured region.

    Returns a dict:
        {
            "platforms": [
                {"name": ..., "logo": ..., "types": "Subscription",
                 "url": <direct platform link>},
                ...
            ],
            "justwatch_url": <region availability page or "">,
        }

    Results are cached in Redis per (movie, region) so TMDB is not hit on
    every page view. Never raises: on any failure an empty result is
    returned so the movie details page renders normally without the OTT
    section.
    """
    empty = {"platforms": [], "justwatch_url": ""}

    api_key = os.getenv("TMDB_API_KEY", "")
    if not api_key:
        logger.warning("TMDB_API_KEY not set; OTT platform info unavailable.")
        return empty

    region = os.getenv("OTT_REGION", "IN")
    cache_key = f"ott_providers_{movie.tmdb_id}_{region}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    country = None
    for host in TMDB_API_HOSTS:
        try:
            response = requests.get(
                f"{host}/movie/{movie.tmdb_id}/watch/providers",
                params={"api_key": api_key},
                timeout=5,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            logger.warning(
                "TMDB watch providers request failed (%s) for tmdb_id %s: %s",
                host,
                movie.tmdb_id,
                exc,
            )
            continue
        try:
            payload = response.json()
        except ValueError:
            logger.warning(
                "TMDB watch providers returned invalid JSON from %s for tmdb_id %s",
                host,
                movie.tmdb_id,
            )
            continue
        country = payload.get("results", {}).get(region, {})
        break

    if country is None:
        # Every host failed; cache briefly so an outage does not turn
        # into a request storm.
        cache.set(cache_key, empty, 300)
        return empty

    justwatch_url = country.get("link", "")

    # Merge availability types per provider (a service can be both
    # flatrate and rent), preserving first-seen order.
    merged = {}
    for availability, label in AVAILABILITY_LABELS:
        for provider in country.get(availability, []):
            provider_id = provider.get("provider_id")
            name = provider.get("provider_name", "")
            logo_path = provider.get("logo_path", "")
            if not provider_id or not name or not logo_path:
                continue
            if provider_id not in merged:
                merged[provider_id] = {
                    "name": name,
                    "logo_path": logo_path,
                    "labels": [label],
                }
            elif label not in merged[provider_id]["labels"]:
                merged[provider_id]["labels"].append(label)

    query = urllib.parse.quote_plus(movie.title or "")
    platforms = []
    for entry in merged.values():
        url_template = OTT_PLATFORM_LINKS.get(entry["name"].lower().strip())
        platforms.append(
            {
                "name": entry["name"],
                "logo": f"{TMDB_IMAGE_URL}w500{entry['logo_path']}",
                "types": ", ".join(entry["labels"]),
                # Direct platform search page when known, otherwise the
                # JustWatch deep link for this movie.
                "url": url_template.format(query=query)
                if url_template
                else justwatch_url,
            }
        )

    payload = {"platforms": platforms, "justwatch_url": justwatch_url}
    cache.set(cache_key, payload, getattr(settings, "CACHE_TTL", 3600))
    return payload


# =====================================================
# MOVIE DETAILS
# =====================================================


@ensure_csrf_cookie  # guarantee csrftoken cookie for AJAX (like/dislike)
def movie_details(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)

    # Only record watch history on an explicit watch action (POST),
    # not on every page view. This prevents watch history inflation
    # from mere browsing.
    if request.method == "POST" and request.user.is_authenticated:
        WatchHistory.objects.get_or_create(user=request.user, movie=movie)

        try:
            update_user_taste_profile(request.user)
        except Exception:
            pass

    genres = movie.genres.split(",") if movie.genres else []
    primary_genre = genres[0].strip() if genres else ""

    similar_movies = (
        Movie.objects.exclude(id=movie.id)
        .filter(genres__icontains=primary_genre)
        .order_by("-vote_average")[:8]
    )

    reviews = (
        Review.objects.filter(movie=movie)
        .select_related("user")
        .order_by("-created_at")
    )

    average_rating = Review.objects.filter(movie=movie).aggregate(
        Avg("rating")
    )["rating__avg"]

    if request.method == "POST" and request.user.is_authenticated:
        try:
            rating = int(request.POST.get("rating", ""))
            if not 1 <= rating <= 10:
                raise ValueError
        except (TypeError, ValueError):
            messages.error(request, "Rating must be a whole number between 1 and 10.")
            return redirect("movie_details", movie_id=movie.id)
        comment = request.POST.get("comment")

        Review.objects.update_or_create(
            movie=movie,
            user=request.user,
            defaults={"rating": rating, "comment": comment},
        )

        return redirect("movie_details", movie_id=movie.id)

    ott_data = _get_ott_platforms(movie)

    context = {
        "movie": movie,
        "ott_platforms": ott_data["platforms"],
        "ott_justwatch_url": ott_data["justwatch_url"],
        "similar_movies": similar_movies,
        "cast": getattr(movie, "cast_data", None),
        "reviews": reviews,
        "average_rating": average_rating,
        "confidence": 96,
        "audience_match": 96,
        "story_complexity": "High",
        "visual_score": 9.4,
        "emotional_depth": 9.1,
        "genre_popularity": "High",
        "recommendation_reason": "Based on your viewing history and cinematic preferences.",
    }

    return render(request, "movie_details.html", context)


# =====================================================
# WATCH HISTORY
# =====================================================


@login_required
def watch_history(request):
    history = (
        WatchHistory.objects.filter(user=request.user)
        .select_related("movie")
        .order_by("-watched_at")
    )

    paginator = Paginator(history, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "watch_history.html",
        {"history": page_obj, "page_obj": page_obj},
    )


# =====================================================
# CINEMA JOURNAL
# =====================================================


@login_required
def cinema_journal(request, id):
    movie = get_object_or_404(Movie, id=id)
    context = {"movie": movie}
    return render(request, "cinema_journal.html", context)


# =====================================================
# ACTOR PROFILE
# =====================================================


def actor_profile(request, id):
    actor = get_object_or_404(Actor, tmdb_id=id)
    movies = actor.movies.all().order_by("-popularity_score")

    context = {"actor": actor, "movies": movies, "movie_count": movies.count()}

    return render(request, "actor_profile.html", context)


# =====================================================
# AI MOVIE FEEDBACK SYSTEM
# =====================================================


@login_required
def movie_feedback(request, movie_id):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)

    try:
        action = request.POST.get("action")
        movie = get_object_or_404(Movie, id=movie_id)

        UserFeedback.objects.create(user=request.user, movie=movie, feedback_type=action)

        profile = update_user_taste_profile(request.user)

        return JsonResponse(
            {
                "status": "success",
                "message": "Feedback saved. AI updated your taste profile.",
                "personality": profile.personality,
                "taste_score": profile.taste_score,
            }
        )

    except Exception:
        return JsonResponse(
            {"status": "error", "message": "Unable to save feedback."}, status=400
        )


# =====================================================
# AI RECOMMENDATION API
# =====================================================


@login_required
def ai_recommendations_api(request):
    try:
        recommendations = hybrid_recommendations(request.user, limit=20)

        movies = []

        for item in recommendations:
            if isinstance(item, dict):
                movie = item.get("movie")
                score = item.get("score", 0)
            else:
                movie = item
                score = 0

            if movie:
                movies.append(
                    {
                        "id": movie.id,
                        "title": movie.title,
                        "poster": movie.poster_url,
                        "rating": movie.vote_average,
                        "match_score": score,
                    }
                )

        return JsonResponse({"status": "success", "recommendations": movies})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


# =====================================================
# USER AI PROFILE API
# =====================================================


@login_required
def ai_profile_api(request):
    try:
        profile = request.user.taste_profile

        return JsonResponse(
            {
                "username": request.user.username,
                "personality": profile.personality,
                "favorite_genres": profile.favorite_genres,
                "watching_style": profile.watching_style,
                "preferred_experience": profile.preferred_experience,
                "taste_score": profile.taste_score,
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# =====================================================
# USER DASHBOARD DATA API
# =====================================================


@login_required
def dashboard_stats_api(request):
    user = request.user

    watched = WatchHistory.objects.filter(user=user).count()
    wishlist = Wishlist.objects.filter(user=user).count()
    reviews = Review.objects.filter(user=user).count()
    feedback = UserFeedback.objects.filter(user=user).count()

    return JsonResponse(
        {"movies_watched": watched, "wishlist": wishlist, "reviews": reviews, "feedback": feedback}
    )


# =====================================================
# USER SEARCH API
# =====================================================


@api_view(["GET"])
def movie_search_api(request):
    query = request.GET.get("q", "").strip()

    if not query:
        return Response([])

    movies = Movie.objects.filter(
        Q(title__icontains=query)
        | Q(genres__icontains=query)
        | Q(director__icontains=query)
    ).order_by("-popularity_score")[:20]

    data = [
        {
            "id": movie.id,
            "title": movie.title,
            "poster": movie.poster_url,
            "year": movie.release_year,
            "rating": movie.vote_average,
        }
        for movie in movies
    ]

    return Response(data)


# =====================================================
# INTERACTION TELEMETRY API
# =====================================================


@api_view(["POST"])
def interaction_tracking_api(request):
    if not request.user.is_authenticated:
        return Response(
            {"status": "error", "message": "Authentication is required"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        movie_id = request.data.get("movie_id")
        interaction_type = request.data.get("interaction_type", "VIEW")
        duration = request.data.get("watch_duration", 0)

        movie = get_object_or_404(Movie, id=movie_id)

        InteractionTelemetry.objects.create(
            user=request.user,
            movie=movie,
            interaction_type=interaction_type,
            watch_duration=duration,
        )

        try:
            update_user_taste_profile(request.user)
        except Exception:
            pass

        return Response({"status": "success", "message": "Interaction recorded"})

    except Exception as e:
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


# =====================================================
# ADMIN ANALYTICS DASHBOARD
# =====================================================


# Send unauthenticated/non-staff visitors to the site's own login page
# (LOGIN_URL) instead of the Django admin login, and honor ?next= on the way
# back once they sign in.
@staff_member_required(login_url="login")
def analytics_dashboard(request):
    total_movies = Movie.objects.count()
    total_users = User.objects.count()
    total_reviews = Review.objects.count()
    total_watch_history = WatchHistory.objects.count()
    popular_movies = Movie.objects.order_by("-popularity_score")[:10]
    top_rated_movies = Movie.objects.order_by("-vote_average")[:10]

    context = {
        "total_movies": total_movies,
        "total_users": total_users,
        "total_reviews": total_reviews,
        "total_watch_history": total_watch_history,
        "popular_movies": popular_movies,
        "top_rated_movies": top_rated_movies,
    }

    return render(request, "analytics_dashboard.html", context)


# =====================================================
# REFRESH USER AI PROFILE
# =====================================================


@login_required
def refresh_ai_profile(request):
    try:
        profile = update_user_taste_profile(request.user)
        messages.success(request, f"AI Profile Updated: {profile.personality}")

    except Exception as e:
        messages.error(request, str(e))

    return redirect("profile")


# =====================================================
# REMOVE WATCH HISTORY ITEM
# =====================================================


@login_required
def remove_watch_history(request, movie_id):
    WatchHistory.objects.filter(user=request.user, movie_id=movie_id).delete()
    messages.success(request, "Removed from watch history")
    return redirect("watch_history")


# =====================================================
# RATE MOVIE QUICK API
# =====================================================


@login_required
@api_view(["POST"])
def quick_rating_api(request, movie_id):
    movie = get_object_or_404(Movie, id=movie_id)
    rating = request.data.get("rating")

    if not rating:
        return Response(
            {"status": "error", "message": "Rating required"},
            status=400,
        )

    Review.objects.update_or_create(
        user=request.user, movie=movie, defaults={"rating": rating}
    )

    update_user_taste_profile(request.user)

    return Response({"status": "success", "message": "Rating saved"})


# =====================================================
# HEALTH CHECK API
# =====================================================


@api_view(["GET"])
def health_check(request):
    return Response(
        {"application": "LuminaRecs", "status": "running", "version": "9.2"}
    )


# =====================================================
# CUSTOM ERROR HANDLERS
# =====================================================


def custom_404(request, exception):
    return render(request, "404.html", status=404)


def custom_500(request):
    return render(request, "500.html", status=500)
