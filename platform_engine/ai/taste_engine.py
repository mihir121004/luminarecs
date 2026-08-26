from collections import Counter

from platform_engine.models import (
    UserFeedback,
    UserTasteProfile,
    WatchHistory,
    Review,
    Wishlist,
)


# =====================================================
# AI USER TASTE PROFILE ENGINE 9.2
# =====================================================


def extract_movie_data(movie):
    """Extract genres, actors, and directors from a movie."""
    genres = []
    actors = []
    directors = []

    # Genres
    if movie.genres:
        if isinstance(movie.genres, str):
            genres.extend([g.strip() for g in movie.genres.split(",")])
        elif isinstance(movie.genres, list):
            genres.extend(movie.genres)

    # Director
    if movie.director:
        directors.append(movie.director.strip())

    # Actors
    if movie.cast_data:
        for actor in movie.cast_data:
            if isinstance(actor, dict):
                name = actor.get("name")
                if name:
                    actors.append(name)
            else:
                actors.append(str(actor))

    return genres, actors, directors


def normalize_genre(name):
    """Normalize genre names to standard format."""
    name = name.lower()

    mapping = {
        "science fiction": "Sci-Fi",
        "sci-fi": "Sci-Fi",
        "science-fiction": "Sci-Fi",
        "thriller": "Thriller",
        "action": "Action",
        "adventure": "Adventure",
        "drama": "Drama",
        "comedy": "Comedy",
        "horror": "Horror",
        "romance": "Romance",
    }

    return mapping.get(name, name.title())


def calculate_personality(genres):
    """Determine user personality based on favorite genres."""
    genres = [g.lower() for g in genres]

    if "sci-fi" in genres:
        return "Future Visionary Explorer"
    if "action" in genres:
        return "Adrenaline Cinema Hunter"
    if "thriller" in genres:
        return "Mystery Mind Explorer"
    if "drama" in genres:
        return "Emotional Story Lover"
    if "horror" in genres:
        return "Dark Universe Explorer"
    if "comedy" in genres:
        return "Entertainment Seeker"

    return "Cinema Explorer"


def calculate_style(genres):
    """Determine watching style based on genres."""
    genres = [g.lower() for g in genres]

    if "action" in genres or "thriller" in genres:
        return "High Intensity Viewer"
    if "drama" in genres:
        return "Story Driven Viewer"
    if "sci-fi" in genres:
        return "World Building Explorer"
    if "comedy" in genres:
        return "Light Entertainment Viewer"

    return "Balanced Cinema Explorer"


def calculate_experience(genres):
    """Determine preferred viewing experience."""
    genres = [g.lower() for g in genres]

    if "sci-fi" in genres:
        return "Immersive Future Worlds"
    if "drama" in genres:
        return "Deep Emotional Storytelling"
    if "action" in genres:
        return "High Energy Cinematic Experience"

    return "Classic Cinema Experience"


def update_user_taste_profile(user):
    """
    Update user's AI taste profile based on watch history,
    feedback, reviews, and wishlist.
    """
    profile, created = UserTasteProfile.objects.get_or_create(user=user)

    genres = []
    actors = []
    directors = []
    rating_scores = []

    # Watch History Learning
    history = WatchHistory.objects.filter(user=user).select_related("movie")
    for item in history:
        g, a, d = extract_movie_data(item.movie)
        genres.extend(g)
        actors.extend(a)
        directors.extend(d)

    # User Feedback Learning
    feedbacks = UserFeedback.objects.filter(user=user).select_related("movie")
    for feedback in feedbacks:
        g, a, d = extract_movie_data(feedback.movie)
        genres.extend(g)
        actors.extend(a)
        directors.extend(d)

        if feedback.feedback_type == "like":
            rating_scores.append(9)
        elif feedback.feedback_type == "dislike":
            rating_scores.append(3)
        elif feedback.rating:
            rating_scores.append(feedback.rating)

    # Review Learning
    reviews = Review.objects.filter(user=user).select_related("movie")
    for review in reviews:
        g, a, d = extract_movie_data(review.movie)
        genres.extend(g)
        actors.extend(a)
        directors.extend(d)
        rating_scores.append(review.rating)

    # Wishlist Learning
    wishlist = Wishlist.objects.filter(user=user).select_related("movie")
    for item in wishlist:
        g, a, d = extract_movie_data(item.movie)
        genres.extend(g)
        actors.extend(a)
        directors.extend(d)

    # Normalize genres
    genres = [normalize_genre(g) for g in genres]

    # Update profile with favorite content
    profile.favorite_genres = [item[0] for item in Counter(genres).most_common(5)]
    profile.favorite_actors = [item[0] for item in Counter(actors).most_common(5)]
    profile.favorite_directors = [item[0] for item in Counter(directors).most_common(5)]

    # Calculate average rating
    if rating_scores:
        profile.preferred_rating = round(sum(rating_scores) / len(rating_scores), 2)

    # Calculate AI-driven attributes
    profile.personality = calculate_personality(profile.favorite_genres)
    profile.watching_style = calculate_style(profile.favorite_genres)
    profile.preferred_experience = calculate_experience(profile.favorite_genres)

    # Calculate advanced taste score
    watch_score = history.count() * 1.5
    feedback_score = feedbacks.count() * 4
    review_score = reviews.count() * 5
    wishlist_score = wishlist.count() * 1

    total = watch_score + feedback_score + review_score + wishlist_score
    profile.taste_score = min(round(total), 100)

    profile.save()

    return profile