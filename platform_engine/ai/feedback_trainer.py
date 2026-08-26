from platform_engine.models import (
    UserFeedback,
    Movie
)

from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def train_from_feedback():

    feedbacks = (
        UserFeedback.objects.all()
    )

    positive_movies = []

    for feedback in feedbacks:
        if feedback.feedback_type=="like":
            positive_movies.append(
                feedback.movie.embedding
            )

    if not positive_movies:
        return None

    user_vector = np.mean(
        positive_movies,
        axis=0
    )

    return user_vector