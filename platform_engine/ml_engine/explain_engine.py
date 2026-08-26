from ..models import Review, WatchHistory


def generate_explaination(user, movie):
    """Generates personalized human-readable reason strings explaining why a movie was recommended to a user."""
    reasons = []

    # ==================================
    # USER GENRE PREFERENCE
    # ==================================
    watched_genres_raw = WatchHistory.objects.filter(user=user).values_list(
        "movie__genres", flat=True
    )

    user_genres = {
        genre.strip()
        for genres in watched_genres_raw
        if genres
        for genre in genres.split(",")
    }

    if movie.genres:
        movie_genres = [g.strip() for g in movie.genres.split(",")]
        matching_genres = [g for g in movie_genres if g in user_genres]

        for genre in matching_genres:
            reasons.append(f"You enjoy {genre} movies")

    # ==================================
    # DIRECTOR MATCH
    # ==================================
    if movie.director:
        reasons.append(
            f"Directed by {movie.director}, matching your cinematic taste"
        )

    # ==================================
    # RATINGS & POPULARITY
    # ==================================
    if movie.vote_average >= 8:
        reasons.append("Highly rated by audiences")

    if movie.popularity_score > 100:
        reasons.append("Trending among movie lovers")

    # ==================================
    # USER RATING BEHAVIOR
    # ==================================
    positive_reviews_count = Review.objects.filter(
        user=user, rating__gte=8
    ).count()

    if positive_reviews_count > 5:
        reasons.append("Matches your high-rated movie preferences")

    # ==================================
    # DEFAULT MESSAGE
    # ==================================
    if not reasons:
        reasons.append("Recommended based on AI analysis of movie patterns")

    return reasons[:4]