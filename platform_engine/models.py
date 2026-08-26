from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify
from django.core.validators import MaxValueValidator, MinValueValidator


# =====================================================
# GENRE
# =====================================================

class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            while Genre.objects.filter(slug=slug).exclude(id=self.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# =====================================================
# MOVIE
# =====================================================

class Movie(models.Model):
    tmdb_id = models.IntegerField(unique=True)
    title = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True)
    overview = models.TextField(blank=True, null=True)
    genres = models.CharField(max_length=500, blank=True, null=True)
    genre = models.ManyToManyField(Genre, related_name="movies", blank=True)
    keywords = models.TextField(blank=True, null=True)
    poster_url = models.URLField(blank=True, null=True)
    backdrop_url = models.URLField(blank=True, null=True)
    release_date = models.DateField(blank=True, null=True)
    release_year = models.IntegerField(blank=True, null=True)
    runtime = models.IntegerField(blank=True, null=True)
    tagline = models.CharField(max_length=500, blank=True, null=True)
    language = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    director = models.CharField(max_length=255, blank=True, null=True)
    writer = models.CharField(max_length=255, blank=True, null=True)
    cast_data = models.JSONField(default=list, blank=True)
    trailer_key = models.CharField(max_length=255, blank=True, null=True)
    vote_average = models.FloatField(default=0, db_index=True)
    popularity_score = models.FloatField(default=0, db_index=True)
    budget = models.BigIntegerField(default=0)
    revenue = models.BigIntegerField(default=0)
    status = models.CharField(max_length=100, blank=True, null=True)
    production_companies = models.TextField(blank=True, null=True)

    # ==============================
    # AI VECTOR DATA
    # ==============================
    embedding = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["vote_average", "popularity_score"]),
            models.Index(fields=["release_year"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    @property
    def average_rating(self):
        ratings = self.reviews.all()
        if ratings.exists():
            return round(sum(r.rating for r in ratings) / ratings.count(), 1)
        return 0

    def __str__(self):
        return self.title


# =====================================================
# WISHLIST
# =====================================================

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "movie")
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.movie.title}"


# =====================================================
# ACTOR
# =====================================================

class Actor(models.Model):
    tmdb_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255, db_index=True)
    profile_image = models.URLField(blank=True, null=True)
    biography = models.TextField(blank=True, null=True)
    birthday = models.DateField(blank=True, null=True)
    place_of_birth = models.CharField(max_length=255, blank=True, null=True)
    known_for_department = models.CharField(max_length=255, blank=True, null=True)
    popularity = models.FloatField(default=0, db_index=True)
    movies = models.ManyToManyField(Movie, related_name="actors", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["name", "popularity"]),
        ]

    def __str__(self):
        return self.name


# =====================================================
# REVIEW
# =====================================================

class Review(models.Model):
    movie = models.ForeignKey(
        Movie, related_name="reviews", on_delete=models.CASCADE
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("movie", "user")
        indexes = [
            models.Index(fields=["movie", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.movie.title}"


# =====================================================
# WATCH HISTORY
# =====================================================

class WatchHistory(models.Model):
    user = models.ForeignKey(
        User, related_name="watch_history", on_delete=models.CASCADE
    )
    movie = models.ForeignKey(
        Movie, related_name="watch_history", on_delete=models.CASCADE
    )
    progress = models.PositiveIntegerField(default=0)
    last_position = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    watched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "movie")
        indexes = [
            models.Index(fields=["user", "-watched_at"]),
            models.Index(fields=["movie", "-watched_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} watched {self.movie.title}"


# =====================================================
# USER INTERACTION TELEMETRY
# =====================================================

class InteractionTelemetry(models.Model):
    TYPES = (
        ("CLICK", "CLICK"),
        ("WATCH", "WATCH"),
        ("TRAILER", "TRAILER"),
        ("RATING", "RATING"),
        ("VIEW", "VIEW"),
        ("WISHLIST", "WISHLIST"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    interaction_type = models.CharField(max_length=50, choices=TYPES)
    watch_duration = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "interaction_type"]),
            models.Index(fields=["movie", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.interaction_type}"


# =====================================================
# PROFILE
# =====================================================

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar_style = models.CharField(max_length=50, default="adventurer")
    avatar_seed = models.CharField(max_length=100, default="default")
    bio = models.TextField(blank=True, null=True)
    favorite_quote = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username


# =====================================================
# SEARCH HISTORY
# =====================================================

class SearchHistory(models.Model):
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.CASCADE
    )
    query = models.CharField(max_length=255)
    searched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-searched_at"]),
        ]

    def __str__(self):
        return self.query


# =====================================================
# AI RECOMMENDATION
# =====================================================

class Recommendation(models.Model):
    ALGORITHM_CHOICES = (
        ("TF-IDF", "TF-IDF Content Based"),
        ("COLLABORATIVE", "Collaborative Filtering"),
        ("HYBRID", "Hybrid AI Model"),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="recommendations"
    )
    movie = models.ForeignKey(
        Movie, on_delete=models.CASCADE, related_name="recommendations"
    )
    score = models.FloatField(default=0)
    reason = models.CharField(max_length=500, blank=True)
    algorithm = models.CharField(
        max_length=100, choices=ALGORITHM_CHOICES, default="HYBRID"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-score"]),
            models.Index(fields=["movie", "-score"]),
        ]

    def __str__(self):
        return f"{self.user.username} → {self.movie.title}"


# =====================================================
# USER GENRE PREFERENCE
# =====================================================

class UserGenrePreference(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="genre_preferences"
    )
    genre = models.CharField(max_length=100)
    score = models.FloatField(default=0)
    reason = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "genre")
        indexes = [
            models.Index(fields=["user", "-score"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.genre}"


# =====================================================
# USER MOVIE PREFERENCE
# =====================================================

class UserMoviePreference(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="movie_preferences"
    )
    movie = models.ForeignKey(
        Movie, on_delete=models.CASCADE, related_name="user_preferences"
    )
    preference_score = models.FloatField(default=0)
    interaction_count = models.IntegerField(default=0)
    liked = models.BooleanField(default=False)
    last_interaction = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "movie")
        indexes = [
            models.Index(fields=["user", "-preference_score"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.movie.title}"


# =====================================================
# AI MODEL VERSION TRACKING
# =====================================================

class AIModelVersion(models.Model):

    MODEL_TYPES = (

        (
            "CONTENT",
            "Content Based"
        ),

        (
            "SEMANTIC",
            "Semantic AI"
        ),

        (
            "HYBRID",
            "Hybrid Recommendation"
        ),

        (
            "COLLABORATIVE",
            "Collaborative Filtering"
        ),

    )


    name = models.CharField(
        max_length=255
    )


    version = models.CharField(
        max_length=50,
        default="1.0"
    )


    model_type = models.CharField(
        max_length=50,
        choices=MODEL_TYPES,
        default="CONTENT"
    )


    algorithm = models.CharField(
        max_length=255,
        default="TF-IDF + Cosine Similarity"
    )


    framework = models.CharField(
        max_length=100,
        default="Scikit-Learn"
    )


    embedding_model = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )


    accuracy = models.FloatField(
        default=0.0
    )


    trained_movies = models.IntegerField(
        default=0
    )


    training_time = models.FloatField(
        default=0,
        help_text="Training duration in seconds"
    )


    model_path = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )


    vector_dimension = models.IntegerField(
        default=0,
        help_text="Embedding vector size"
    )


    is_active = models.BooleanField(
        default=True
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    updated_at = models.DateTimeField(
        auto_now=True
    )



    class Meta:

        indexes = [

            models.Index(
                fields=[
                    "is_active"
                ]
            ),

            models.Index(
                fields=[
                    "model_type"
                ]
            )

        ]



    def __str__(self):

        return (
            f"{self.name} v{self.version}"
        )

# =====================================================
# COLLECTION
# =====================================================

class Collection(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)
    movies = models.ManyToManyField(Movie, related_name="collections")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# =====================================================
# AI TRAINING LOG
# =====================================================

class AITrainingLog(models.Model):
    STATUS = (
        ("SUCCESS", "SUCCESS"),
        ("FAILED", "FAILED"),
        ("RUNNING", "RUNNING"),
    )

    model_name = models.CharField(max_length=255)
    algorithm = models.CharField(max_length=255)
    movies_processed = models.IntegerField(default=0)
    accuracy = models.FloatField(default=0)
    status = models.CharField(max_length=50, choices=STATUS, default="RUNNING")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.model_name} - {self.status}"


# =====================================================
# AI USER TASTE PROFILE
# =====================================================

class UserTasteProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="taste_profile"
    )
    personality = models.CharField(max_length=255, default="Cinema Explorer")
    favorite_genres = models.JSONField(default=list)
    favorite_directors = models.JSONField(default=list)
    favorite_actors = models.JSONField(default=list)
    preferred_rating = models.FloatField(default=0)
    taste_score = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    watching_style = models.CharField(max_length=150, default="Balanced Cinema Explorer")
    preferred_experience = models.CharField(max_length=150, default="Immersive World Building")

    def __str__(self):
        return self.user.username


# =====================================================
# DJANGO SIGNALS: AUTO CREATE PROFILE + AI PROFILE
# =====================================================

@receiver(post_save, sender=User)
def create_user_profiles(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        UserTasteProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profiles(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        instance.profile.save()

    if hasattr(instance, "taste_profile"):
        instance.taste_profile.save()


class RecommendationLog(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE
    )

    algorithm=models.CharField(
        max_length=100,
        default="Hybrid AI"
    )

    score=models.FloatField(
        default=0
    )

    clicked=models.BooleanField(
        default=False
    )

    created_at=models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        indexes = [

            models.Index(
                fields=[
                    "user",
                    "created_at"
                ]
            )
        ]

    def __str__(self):
        return(f"{self.user.username} - {self.movie.title}")


class UserFeedback(models.Model):

    FEEDBACK_CHOICES = (
        ("like", "Like"),
        ("dislike", "Dislike"),
        ("rating", "Rating"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE
    )

    feedback_type = models.CharField(
        max_length=20,
        choices=FEEDBACK_CHOICES
    )

    rating = models.FloatField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user} - {self.movie} - {self.feedback_type}"

class AIUserInsight(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )
    personality = models.CharField(
        max_length=100,
        default="Cinema Explorer"
    )
    ai_summary = models.TextField(
        blank=True
    )
    taste_score = models.IntegerField(
        default=50
    )
    story_score = models.IntegerField(
        default=50
    )
    visual_score = models.IntegerField(
        default=50
    )
    emotion_score = models.IntegerField(
        default=50
    )
    action_score = models.IntegerField(
        default=50
    )
    complexity_score = models.IntegerField(
        default=50
    )
    movie_analyzed = models.IntegerField(
        default=0
    )
    accuracy = models.IntegerField(
        default=0
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.user.username

class WatchProgress(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE
    )

    progress = models.FloatField(default=0)

    updated_at = models.DateTimeField(
        auto_now=True
    )
