from platform_engine.models import Recommendation
from .hybrid_engine import hybrid_recommendations


def save_user_recommendations(user, limit=20):
    """
    Generate and save personalized recommendations for a user.
    
    Args:
        user: User object to save recommendations for
        limit: Maximum number of recommendations to generate (default: 20)
        
    Returns:
        Number of recommendations saved
    """
    # Clear previous recommendations
    Recommendation.objects.filter(user=user).delete()

    # Generate hybrid recommendations
    results = hybrid_recommendations(user=user, limit=limit)

    # Build recommendation objects
    recommendations = [
        Recommendation(
            user=user,
            movie=item["movie"],
            score=item["score"],
            reason=item["reason"],
            algorithm="HYBRID",
        )
        for item in results
    ]

    # Bulk create for efficiency
    Recommendation.objects.bulk_create(recommendations)

    return len(recommendations)