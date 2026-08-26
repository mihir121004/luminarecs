import os
import pickle
import faiss
import numpy as np

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from ..models import Movie


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "model_data"
)


FAISS_PATH = os.path.join(
    MODEL_PATH,
    "faiss.index"
)


MOVIE_MAP_PATH = os.path.join(
    MODEL_PATH,
    "movie_mapping.pkl"
)



# ===============================
# LOAD EMBEDDING MODEL
# ===============================

@lru_cache(maxsize=1)
def get_embedding_model():
    """Load the transformer only when semantic recommendations are requested."""
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")



# ===============================
# LOAD FAISS
# ===============================

@lru_cache(maxsize=1)
def load_faiss():

    if not os.path.exists(FAISS_PATH):
        return None

    return faiss.read_index(
        FAISS_PATH
    )



# ===============================
# LOAD MOVIE MAP
# ===============================

@lru_cache(maxsize=1)
def load_movie_mapping():

    if not os.path.exists(
        MOVIE_MAP_PATH
    ):
        return []

    with open(
        MOVIE_MAP_PATH,
        "rb"
    ) as file:

        return pickle.load(file)



# ===============================
# SEMANTIC RECOMMENDATION
# ===============================


def semantic_recommendations(
        movie_id,
        limit=6
):

    index = load_faiss()

    movie_ids = load_movie_mapping()


    if index is None:
        return []


    if movie_id not in movie_ids:

        print(
            f"Movie {movie_id} has no embedding"
        )

        return []



    movie = Movie.objects.get(
        id=movie_id
    )


    text = (
        f"{movie.title} "
        f"{movie.overview or ''} "
        f"{movie.genres or ''} "
        f"{movie.director or ''}"
    )


    embedding = get_embedding_model().encode(
        [text],
        normalize_embeddings=True
    )


    embedding = np.array(
        embedding
    ).astype(
        "float32"
    )


    distances, indices = index.search(
        embedding,
        limit + 1
    )


    results = []


    for idx, score in zip(
        indices[0],
        distances[0]
    ):


        if idx >= len(movie_ids):
            continue


        similar_movie_id = movie_ids[idx]


        if similar_movie_id == movie_id:
            continue



        try:

            similar_movie = Movie.objects.get(
                id=similar_movie_id
            )


            results.append({

                "movie": similar_movie,

                "semantic_score":
                    round(
                        float(score),
                        4
                    ),


                "reason":
                    "Similar story, theme and cinematic style"

            })


        except Movie.DoesNotExist:

            continue



    return results[:limit]
