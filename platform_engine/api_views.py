from rest_framework.decorators import api_view
from rest_framework.response import Response

from django.contrib.auth.models import User
from .models import Recommendation

@api_view(["GET"])
def user_recommendations(request):
    user=request.user
    recommendations = Recommendation.objects.filter(
        user=user
    ).select_related(
        "movie"
    )[:20]

    data =[]

    for item in recommendations:
        data.append({
            "title": item.movie.title,
            "poster": item.movie.poster_url,
            "score": item.score,
            "reason": item.reason
        })

    return Response(data)