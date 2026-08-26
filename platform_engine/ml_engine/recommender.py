from functools import lru_cache
import os

from django.db import transaction
from django.db.models import Avg, Count
import joblib

from ..models import (
    InteractionTelemetry,
    Movie,
    Review,
    UserGenrePreference,
    WatchHistory,
    Wishlist,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model_data")


# ==========================================
# LOAD AI MODEL ONCE
# ==========================================

@lru_cache(maxsize=1)
def load_ai_model():
    """Loads and caches the AI model and movie dataset from disk."""
    try:
        similarity = joblib.load(os.path.join(MODEL_PATH, "similarity.pkl"))
        movies_df = joblib.load(os.path.join(MODEL_PATH, "movies.pkl"))
        return similarity, movies_df
    except Exception:
        return None, None


# ==========================================
# AI EXPLANATION GENERATOR
# ==========================================

def generate_reason(movie, similarity):
    """Generates a human-readable reason based on similarity score percentage."""
    if similarity >= 90:
        return "Highly similar storyline, genre and characters"
    if similarity >= 75:
        return "Similar cinematic style and audience preference"
    if similarity >= 60:
        return "Matches your movie taste and genre interests"
    return "Recommended because of similar movie patterns"


# ==========================================
# CONTENT BASED RECOMMENDATION
# ==========================================

def get_recommendations(movie_id, limit=6):
    """Retrieves content-based movie recommendations using cosine similarity."""
    similarity, movies_df = load_ai_model()

    if similarity is None or movies_df is None:
        return []

    # Check movie exists in dataset
    if movie_id not in movies_df["id"].values:
        return []

    movie_index = movies_df[movies_df["id"] == movie_id].index[0]

    # Get similarity scores and sort descending
    scores = sorted(
        enumerate(similarity[movie_index]),
        key=lambda x: x[1],
        reverse=True,
    )

    recommendations = []
    used_movies = set()

    for index, similarity_score in scores:
        if len(recommendations) >= limit:
            break

        recommended_movie_id = int(movies_df.iloc[index]["id"])

        # Skip base movie and duplicates
        if recommended_movie_id == movie_id or recommended_movie_id in used_movies:
            continue

        used_movies.add(recommended_movie_id)

        try:
            movie = Movie.objects.get(id=recommended_movie_id)
        except Movie.DoesNotExist:
            continue

        # AI Score Calculation
        sim_percentage = similarity_score * 100
        popularity_score = movie.popularity_score
        rating_score = movie.vote_average * 10

        final_score = (
            (sim_percentage * 0.6)
            + (popularity_score * 0.2)
            + (rating_score * 0.2)
        )

        recommendations.append({
            "movie": movie,
            "similarity": round(sim_percentage, 2),
            "score": round(final_score, 2),
            "reason": generate_reason(movie, sim_percentage),
        })

    return recommendations


# ==========================================
# PERSONALIZED USER RECOMMENDATION HELPERS
# ==========================================

def _apply_genre_weights(genre_str, weight, preferences):
    """Parses comma-separated genres and accumulates preference weights."""
    if not genre_str:
        return
    for genre in genre_str.split(","):
        clean_genre = genre.strip()
        if clean_genre:
            preferences[clean_genre] = preferences.get(clean_genre, 0) + weight


# ==========================================
# PERSONALIZED USER RECOMMENDATION
# ==========================================

def get_user_recommendations(user, limit=12):
    """Calculates user preference scores across activities and returns recommendations."""
    preferences = {}

    # 1. Watch History Learning (Weight: +5)
    watched = WatchHistory.objects.filter(user=user).select_related("movie")
    for item in watched:
        _apply_genre_weights(item.movie.genres, 5, preferences)

    # 2. Wishlist Learning (Weight: +8)
    wishlist = Wishlist.objects.filter(user=user).select_related("movie")
    for item in wishlist:
        _apply_genre_weights(item.movie.genres, 8, preferences)

    # 3. Review Learning (Weight: +10 if rating >= 8)
    reviews = Review.objects.filter(user=user, rating__gte=8).select_related("movie")
    for review in reviews:
        _apply_genre_weights(review.movie.genres, 10, preferences)

    # 4. Interaction Telemetry Learning
    interaction_weights = {
        "CLICK": 2,
        "VIEW": 3,
        "TRAILER": 5,
        "WATCH": 8,
        "RATING": 10,
    }
    interactions = InteractionTelemetry.objects.filter(user=user).select_related("movie")
    for interaction in interactions:
        weight = interaction_weights.get(interaction.interaction_type, 1)
        _apply_genre_weights(interaction.movie.genres, weight, preferences)

    # 5. Save/Update User Preference via Bulk Database Operations
    pref_objects = [
        UserGenrePreference(user=user, genre=genre, score=score)
        for genre, score in preferences.items()
    ]
    if pref_objects:
        UserGenrePreference.objects.bulk_create(
            pref_objects,
            update_conflicts=True,
            unique_fields=["user", "genre"],
            update_fields=["score"],
        )

    # 6. Find Top Recommendations
    top_genre = max(preferences, key=preferences.get, default="") if preferences else ""

    recommended_movies = (
        Movie.objects.filter(genres__icontains=top_genre)
        .exclude(watch_history__user=user)
        .order_by("-popularity_score", "-vote_average")[:limit]
    )

    results = []
    for movie in recommended_movies:
        # Calculate matching score based on user's top genre affinity
        movie_first_genre = movie.genres.split(",")[0].strip() if movie.genres else ""
        calculated_score = preferences.get(movie_first_genre, 50)

        results.append({
            "movie": movie,
            "score": calculated_score,
            "reason": "Based on your watching history, ratings and interests",
        })

    return results