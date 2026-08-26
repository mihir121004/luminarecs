from django.core.cache import cache

CACHE_TIME = 60 * 60

def get_cached_recommendations(user_id):
    key = (f"user_recommendations_{user_id}")
    return cache.get(key)

def set_cached_recommendations(user_id, data):
    key=(f"user_recommendations_{user_id}")

    cache.set(key, data, CACHE_TIME)

def clear_recommendation_cache(user_id):
    key=(f"user_recommendations_{user_id}")

    cache.delete(key)