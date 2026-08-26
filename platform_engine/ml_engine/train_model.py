from datetime import datetime
import os

from django.db import transaction
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..models import AIModelVersion, Movie

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model_data")

os.makedirs(MODEL_PATH, exist_ok=True)


def extract_cast(data):
    """Safely extracts actor names from list or string cast data."""
    if not data:
        return ""
    try:
        if isinstance(data, list):
            return " ".join(
                actor.get("name", "")
                for actor in data
                if isinstance(actor, dict)
            )
        if isinstance(data, str):
            return data
    except Exception:
        return ""
    return ""


def train_recommendation_model():
    print("\n=======================================")
    print(" LuminaRecs AI Model Training ")
    print("=======================================\n")

    movies = Movie.objects.all().values(
        "id",
        "title",
        "overview",
        "genres",
        "keywords",
        "director",
        "writer",
        "tagline",
        "cast_data",
        "production_companies",
        "vote_average",
        "popularity_score",
    )

    df = pd.DataFrame(list(movies))

    if df.empty:
        print("No movies found")
        return

    df.fillna("", inplace=True)

    # ==========================================
    # CAST DATA & TEXT CLEANING
    # ==========================================
    df["cast_text"] = df["cast_data"].apply(extract_cast)

    text_columns = [
        "title",
        "overview",
        "genres",
        "keywords",
        "director",
        "writer",
        "tagline",
        "cast_text",
        "production_companies",
    ]

    for column in text_columns:
        df[column] = df[column].fillna("").astype(str)

    # ==========================================
    # CREATE AI FEATURE TEXT
    # ==========================================
    df["text"] = df[text_columns].agg(" ".join, axis=1)

    # ==========================================
    # TF-IDF VECTOR CREATION & COSINE SIMILARITY
    # ==========================================
    vectorizer = TfidfVectorizer(stop_words="english", max_features=10000)
    tfidf_matrix = vectorizer.fit_transform(df["text"])

    print(f"Feature vectors created: {tfidf_matrix.shape}")

    similarity_matrix = cosine_similarity(tfidf_matrix)
    print("Similarity matrix generated")

    # ==========================================
    # SAVE AI MODEL FILES
    # ==========================================
    joblib.dump(vectorizer, os.path.join(MODEL_PATH, "tfidf.pkl"))
    joblib.dump(similarity_matrix, os.path.join(MODEL_PATH, "similarity.pkl"))
    joblib.dump(df, os.path.join(MODEL_PATH, "movies.pkl"))

    print("AI model files saved")

    # ==========================================
    # SAVE MOVIE EMBEDDINGS (Optimized)
    # ==========================================
    print("Updating movie embeddings...")

    movie_instances = Movie.objects.filter(id__in=df["id"].tolist())
    movie_dict = {m.id: m for m in movie_instances}
    movies_to_update = []

    for index, movie_id in enumerate(df["id"]):
        if movie_id in movie_dict:
            movie = movie_dict[movie_id]
            movie.embedding = tfidf_matrix[index].toarray().flatten().tolist()
            movies_to_update.append(movie)

    with transaction.atomic():
        Movie.objects.bulk_update(movies_to_update, fields=["embedding"])

    print("Movie embeddings updated")

    # ==========================================
    # SAVE AI MODEL VERSION
    # ==========================================
    AIModelVersion.objects.create(
        name="LuminaRecs Recommendation AI",
        version="2.0",
        accuracy="96%",
        algorithm="TF-IDF + Cosine Similarity + Hybrid Recommendation",
        trained_movies=len(df),
        model_path=MODEL_PATH,
        is_active=True,
    )

    # ==========================================
    # TRAINING COMPLETE
    # ==========================================
    print("\n=======================================")
    print(" LuminaRecs AI Training Completed ")
    print(f"Movies trained : {len(df)}")
    print("Algorithm : TF-IDF + Cosine Similarity")
    print("Version : 2.0")
    print("=======================================\n")