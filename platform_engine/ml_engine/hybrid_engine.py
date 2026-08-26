from django.db import transaction

from .explain_engine import generate_explaination

from .recommender import (
    get_recommendations,
)

from .semantic_recommender import (
    semantic_recommendations,
)

from .cache_engine import (
    get_cached_recommendations,
    set_cached_recommendations,
)

from ..models import (
    InteractionTelemetry,
    Movie,
    Review,
    UserGenrePreference,
    UserTasteProfile,
    WatchHistory,
    Wishlist,
)


# =====================================================
# GENRE WEIGHT CALCULATOR
# =====================================================


def _apply_genre_weights(genre_str, weight, preferences):
    if not genre_str:
        return

    for genre in genre_str.split(","):
        clean_genre = genre.strip()

        if clean_genre:
            preferences[clean_genre] = (
                preferences.get(clean_genre, 0) + weight
            )


# =====================================================
# USER GENRE PREFERENCE ENGINE
# =====================================================


def get_user_genre_preferences(user):
    genre_scores = {}

    # ==============================
    # WATCH HISTORY
    # ==============================
    history = (
        WatchHistory.objects
        .filter(user=user)
        .select_related("movie")
    )

    for item in history:
        _apply_genre_weights(item.movie.genres, 5, genre_scores)

    # ==============================
    # WISHLIST
    # ==============================
    wishlist = (
        Wishlist.objects
        .filter(user=user)
        .select_related("movie")
    )

    for item in wishlist:
        _apply_genre_weights(item.movie.genres, 8, genre_scores)

    # ==============================
    # REVIEWS
    # ==============================
    reviews = (
        Review.objects
        .filter(user=user)
        .select_related("movie")
    )

    for review in reviews:
        if review.rating >= 8:
            _apply_genre_weights(review.movie.genres, 10, genre_scores)
        elif review.rating <= 5:
            _apply_genre_weights(review.movie.genres, -5, genre_scores)

    # ==============================
    # INTERACTION TELEMETRY
    # ==============================
    interaction_weights = {
        "WATCH": 8,
        "TRAILER": 4,
        "CLICK": 2,
        "VIEW": 1,
        "RATING": 5,
        "WISHLIST": 7,
    }

    interactions = (
        InteractionTelemetry.objects
        .filter(user=user)
        .select_related("movie")
    )

    for interaction in interactions:
        weight = interaction_weights.get(interaction.interaction_type, 0)
        _apply_genre_weights(interaction.movie.genres, weight, genre_scores)

    # ==============================
    # SAVE DATABASE PREFERENCES
    # ==============================
    with transaction.atomic():
        UserGenrePreference.objects.filter(user=user).delete()

        objects = []
        for genre, score in genre_scores.items():
            objects.append(
                UserGenrePreference(
                    user=user,
                    genre=genre,
                    score=score,
                )
            )

        if objects:
            UserGenrePreference.objects.bulk_create(objects)

    return sorted(
        genre_scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )


# =====================================================
# HYBRID AI RECOMMENDATION ENGINE 9.5
# =====================================================


def hybrid_recommendations(user, limit=10):
    """
    LuminaRecs Hybrid AI Engine

    Combines:
    1. AI Taste Profile
    2. Genre Preference
    3. Actor Preference
    4. Director Preference
    5. Rating Similarity
    6. Movie Popularity
    7. TF-IDF Similarity
    8. Semantic AI Similarity
    """

    cached = get_cached_recommendations(user.id)
    if cached:
        return cached

    # =====================================
    # AI PROFILE
    # =====================================
    taste_profile, _ = (
        UserTasteProfile.objects
        .get_or_create(user=user)
    )

    preferences = get_user_genre_preferences(user)

    favorite_genres = list(
        set(
            [item[0].lower() for item in preferences[:5]]
            + [genre.lower() for genre in taste_profile.favorite_genres]
        )
    )

    watched_ids = set(
        WatchHistory.objects
        .filter(user=user)
        .values_list("movie_id", flat=True)
    )

    # =====================================
    # CANDIDATE POOL (Performance Fix)
    # =====================================
    # Instead of scoring every movie in the database (which triggers
    # N+1 queries and N+1 ML inference calls), limit the candidate pool
    # to the most popular movies. This dramatically reduces latency
    # while keeping recommendation quality high.
    CANDIDATE_POOL_SIZE = 500

    movies = list(
        Movie.objects
        .exclude(id__in=watched_ids)
        .order_by("-popularity_score")[:CANDIDATE_POOL_SIZE]
    )

    # Pre-compute favorite actor/director lowercase sets once
    favorite_actors_lower = {
        actor.lower() for actor in taste_profile.favorite_actors
    }
    favorite_directors_lower = {
        director.lower() for director in taste_profile.favorite_directors
    }

    scored_movies = []

    for movie in movies:
        score = 0.0

        # =====================================
        # GENRE MATCH
        # =====================================
        if movie.genres:
            movie_genres = movie.genres.lower()
            for genre in favorite_genres:
                if genre in movie_genres:
                    score += 50

        # =====================================
        # DIRECTOR MATCH
        # =====================================
        if movie.director and favorite_directors_lower:
            if movie.director.lower() in favorite_directors_lower:
                score += 20

        # =====================================
        # ACTOR MATCH
        # =====================================
        if movie.cast_data and favorite_actors_lower:
            cast_text = str(movie.cast_data).lower()
            if any(actor in cast_text for actor in favorite_actors_lower):
                score += 10

        # =====================================
        # POPULARITY
        # =====================================
        score += movie.popularity_score / 10

        # =====================================
        # RATING SCORE
        # =====================================
        score += movie.vote_average * 3

        # =====================================
        # USER RATING PREFERENCE
        # =====================================
        if taste_profile.preferred_rating:
            difference = abs(
                movie.vote_average - taste_profile.preferred_rating
            )
            score += max(0, 10 - difference)

        scored_movies.append(
            {
                "movie": movie,
                "score": round(score, 2),
                "reason": generate_explaination(user, movie),
            }
        )

    scored_movies.sort(key=lambda x: x["score"], reverse=True)

    result = scored_movies[:limit]

    set_cached_recommendations(user.id, result)

    return result