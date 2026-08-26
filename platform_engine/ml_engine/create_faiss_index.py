import os
import sys
import django
import numpy as np
import faiss
import pickle


# ==========================================
# DJANGO SETUP
# ==========================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

sys.path.append(BASE_DIR)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "core.settings"
)

django.setup()


# ==========================================
# IMPORT MODELS
# ==========================================

from platform_engine.models import Movie


# ==========================================
# PATHS
# ==========================================

CURRENT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

MODEL_DIR = os.path.join(
    CURRENT_DIR,
    "model_data"
)


FAISS_PATH = os.path.join(
    MODEL_DIR,
    "faiss.index"
)


MAP_PATH = os.path.join(
    MODEL_DIR,
    "movie_mapping.pkl"
)


os.makedirs(
    MODEL_DIR,
    exist_ok=True
)


# ==========================================
# LOAD MOVIES
# ==========================================

movies = (
    Movie.objects
    .exclude(
        embedding=[]
    )
)


print(
    "Movies with embeddings:",
    movies.count()
)


vectors = []
movie_ids = []


# ==========================================
# BUILD VECTOR DATA
# ==========================================

for movie in movies:

    embedding = movie.embedding


    if not embedding:
        continue


    if len(embedding) != 384:
        print(
            "Skipping:",
            movie.title,
            len(embedding)
        )
        continue


    vectors.append(
        embedding
    )

    movie_ids.append(
        movie.id
    )


# ==========================================
# NUMPY ARRAY
# ==========================================

vectors = np.array(
    vectors,
    dtype="float32"
)


print(
    "Vector shape:",
    vectors.shape
)


# ==========================================
# NORMALIZE
# ==========================================

faiss.normalize_L2(
    vectors
)


# ==========================================
# CREATE INDEX
# ==========================================

dimension = vectors.shape[1]


index = faiss.IndexFlatIP(
    dimension
)


index.add(
    vectors
)


# ==========================================
# SAVE FILES
# ==========================================

faiss.write_index(
    index,
    FAISS_PATH
)


with open(
    MAP_PATH,
    "wb"
) as f:

    pickle.dump(
        movie_ids,
        f
    )


print(
    "FAISS created successfully"
)


print(
    "Index size:",
    index.ntotal
)


print(
    "Mapping size:",
    len(movie_ids)
)