from django.contrib import admin

from .models import (
    Movie,
    Genre,
    Actor,
    Wishlist,
    Review,
    WatchHistory,
    InteractionTelemetry,
    Profile,
    Recommendation,
    RecommendationLog,
    UserGenrePreference,
    SearchHistory,
    Collection,
    AIModelVersion,
)


# =====================================================
# MOVIE ADMIN
# =====================================================

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "release_year",
        "vote_average",
        "popularity_score",
        "status",
        "created_at",
    )
    search_fields = (
        "title",
        "overview",
        "director",
        "writer",
        "genres",
        "keywords",
    )
    list_filter = (
        "release_year",
        "status",
        "language",
        "vote_average",
    )
    ordering = ("-popularity_score",)
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("genre",)


# =====================================================
# GENRE ADMIN
# =====================================================

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "slug",
    )
    search_fields = ("name",)
    ordering = ("name",)


# =====================================================
# ACTOR ADMIN
# =====================================================

@admin.register(Actor)
class ActorAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "known_for_department",
        "popularity",
    )
    search_fields = (
        "name",
        "place_of_birth",
    )
    list_filter = ("known_for_department",)
    autocomplete_fields = ("movies",)


# =====================================================
# REVIEW ADMIN
# =====================================================

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "movie",
        "user",
        "rating",
        "created_at",
    )
    search_fields = (
        "movie__title",
        "user__username",
        "comment",
    )
    list_filter = (
        "rating",
        "created_at",
    )
    readonly_fields = ("created_at",)


# =====================================================
# WATCH HISTORY ADMIN
# =====================================================

@admin.register(WatchHistory)
class WatchHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "movie",
        "progress",
        "completed",
        "watched_at",
    )
    search_fields = (
        "user__username",
        "movie__title",
    )
    list_filter = (
        "completed",
        "watched_at",
    )
    ordering = ("-watched_at",)
    readonly_fields = ("watched_at",)


# =====================================================
# WISHLIST ADMIN
# =====================================================

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "movie",
        "created_at",
    )
    search_fields = (
        "user__username",
        "movie__title",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


# =====================================================
# INTERACTION TELEMETRY ADMIN
# =====================================================

@admin.register(InteractionTelemetry)
class InteractionTelemetryAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "movie",
        "interaction_type",
        "watch_duration",
        "timestamp",
    )
    search_fields = (
        "user__username",
        "movie__title",
    )
    list_filter = (
        "interaction_type",
        "timestamp",
    )
    ordering = ("-timestamp",)
    readonly_fields = ("timestamp",)


# =====================================================
# PROFILE ADMIN
# =====================================================

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "avatar_style",
        "avatar_seed",
    )
    search_fields = (
        "user__username",
        "user__email",
    )


# =====================================================
# AI RECOMMENDATION ADMIN
# =====================================================

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "movie",
        "score",
        "algorithm",
        "created_at",
    )
    search_fields = (
        "user__username",
        "movie__title",
    )
    list_filter = (
        "algorithm",
        "created_at",
    )
    ordering = ("-score",)
    readonly_fields = ("created_at",)


# =====================================================
# USER GENRE PREFERENCE ADMIN
# =====================================================

@admin.register(UserGenrePreference)
class UserGenrePreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "genre",
        "score",
        "updated_at",
    )
    search_fields = (
        "user__username",
        "genre",
    )
    list_filter = ("genre",)
    ordering = ("-score",)
    readonly_fields = ("updated_at",)


# =====================================================
# SEARCH HISTORY ADMIN
# =====================================================

@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "query",
        "searched_at",
    )
    search_fields = (
        "query",
        "user__username",
    )
    list_filter = ("searched_at",)
    ordering = ("-searched_at",)
    readonly_fields = ("searched_at",)


# =====================================================
# COLLECTION ADMIN
# =====================================================

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "created_at",
    )
    search_fields = (
        "name",
        "description",
    )
    filter_horizontal = ("movies",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


# =====================================================
# AI MODEL VERSION ADMIN
# =====================================================

@admin.register(AIModelVersion)
class AIModelVersionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "version",
        "algorithm",
        "accuracy",
        "trained_movies",
        "is_active",
        "created_at",
    )
    search_fields = (
        "name",
        "algorithm",
        "version",
    )
    list_filter = (
        "is_active",
        "algorithm",
        "created_at",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "created_at",
        "updated_at",
    )

@admin.register(RecommendationLog)
class RecommendationLogAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "movie",
        "algorithm",
        "score",
        "clicked",
        "created_at",
    )
    list_filter=(
        "algorithm",
        "clicked",
    )