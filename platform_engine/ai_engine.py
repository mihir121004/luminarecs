from .models import (
    AIUserInsight,
    WatchHistory
)

def generate_user_ai_profile(user):
    movies = WatchHistory.objects.filter(
        user=user
    ).select_related("movie")

    total = movies.count()

    if total == 0:
        insight, _ = AIUserInsight.objects.get_or_create(user=user)
        insight.personality = "Cinema Beginner"
        insight.taste_score = 50
        insight.movie_analyzed = 0
        insight.ai_summary = (
            "Start watching movies to help LuminaRecs learn your cinematic preferences."
        )
        insight.save()
        return insight
    else:
        genres = []
        for item in movies:
            if item.movie.genres:
                genres.append(item.movie.genres)

        genre_text=" ".join(genres).lower()

        personality = "Cinema Explorer"
        if "action" in genre_text:
            personality="The Action Explorer"
        elif "drama" in genre_text:
            personality="The Emotional Storyteller"
        elif "thriller" in genre_text:
            personality="The visionary Explorer"

        taste_score=min(50+(total*2),100)

        insight, created=AIUserInsight.objects.get_or_create(user=user)

        insight.personality=personality
        insight.taste_score=taste_score
        insight.movie_analyzed=total

        insight.ai_summary=f"""
You are {personality}.

You have watched {total} movies.

LuminaRecs AI understands your cinematic preferences
and continuously improves your recommendations.
"""
        insight.save()
        return insight

def actor_intelligent(user):
    movies = WatchHistory.objects.filter(
        user=user
    )
    actors={}
    for item in movies:
        for actor in item.movie.cast.split(","):
            actors[actor]=actors.get(actor, 0)+1


    result=[]

    for actor,count in actors.items():
        result.append({
            "name":actor,
            "match":min(
                count*10,100
            )
        })

    return sorted(
        result,
        key=lambda x:x["match"],
        reverse=True
    )[:5]

def director_intelligence(user):
    movies=WatchHistory.objects.filter(
        user=user
    )
    directors={}
    for item in movies:
        director=item.movie.director
        directors[director]=(
            directors.get(director,0)+1
        )

    data = []
    for director,count in directors.items():
        data.append({
            "name":director,
            "match":min(count*12,100)
        })

    return sorted(data,
                  key=lambda x:x["match"],
                  reverse=True)[:5]
