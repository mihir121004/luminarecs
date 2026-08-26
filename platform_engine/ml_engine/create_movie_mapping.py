import os
import sys
import pickle
import django


# =====================================================
# DJANGO INITIALIZATION
# =====================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

sys.path.insert(
    0,
    BASE_DIR
)


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "core.settings"
)


django.setup()


# =====================================================
# IMPORT MODELS
# =====================================================

from platform_engine.models import Movie


# =====================================================
# PATH CONFIGURATION
# =====================================================

MODEL_DIR = os.path.join(
    BASE_DIR,
    "platform_engine",
    "ml_engine",
    "model_data"
)


MOVIE_MAP_PATH = os.path.join(
    MODEL_DIR,
    "movie_mapping.pkl"
)


# Create directory if missing
os.makedirs(
    MODEL_DIR,
    exist_ok=True
)


# =====================================================
# CREATE MOVIE MAPPING
# =====================================================


def create_movie_mapping():

    print("\n🎬 Loading movies from database...\n")


    movies = (
        Movie.objects
        .all()
        .values_list(
            "id",
            flat=True
        )
    )


    movie_ids = list(movies)


    print(
        f"✅ Total movies found: {len(movie_ids)}"
    )


    if not movie_ids:
        print(
            "❌ No movies found in database"
        )
        return


    print(
        "\n🧠 Creating movie mapping..."
    )


    with open(
        MOVIE_MAP_PATH,
        "wb"
    ) as file:

        pickle.dump(
            movie_ids,
            file
        )


    print(
        "\n✅ movie_mapping.pkl created successfully"
    )


    print(
        f"📁 Location: {MOVIE_MAP_PATH}"
    )


# =====================================================
# RUN SCRIPT
# =====================================================

if __name__ == "__main__":

    create_movie_mapping()