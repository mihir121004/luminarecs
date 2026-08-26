import os
import joblib
import pandas as pd
from .embedding import generate_embedding
from ...models import Movie

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "../model_data")

os.makedirs(MODEL_PATH, exist_ok=True)

def train_embeddings():
    movies=Movie.objects.all()
    data=[]
    embeddings=[]
    for movie in movies:
        text = f"""
        
        Title:{movie.title}

        Genre:{movie.genres}

        Overview:{movie.overview}

        Director:{movie.director}

        Cast:{movie.cast_data}

        """

        vector = generate_embedding(text)

        embeddings.append(vector)
        data.append(
            {
                "id":movie.id,
                "title":movie.title
            }
        )

        movie.embedding = vector
        movie.save(update_fields=[
            "embedding"
        ])

        joblib.dump(
            embeddings,
            f"{MODEL_PATH}/movie_embeddings.pkl"
        )

        joblib.dump(
            data,
            f"{MODEL_PATH}/movie_metadata.pkl"
        )

        print("Semantic AI training completed")