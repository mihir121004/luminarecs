from pathlib import Path

import faiss
import joblib
import numpy as np

from ...models import Movie

MODEL_PATH = Path("platform_engine/ml_engine/model_data")

# Lazy/Global index loading with safe Path construction
INDEX_FILE = MODEL_PATH / "faiss.index"
METADATA_FILE = MODEL_PATH / "movie_metadata.pkl"

index = faiss.read_index(str(INDEX_FILE)) if INDEX_FILE.exists() else None
movies_metadata = joblib.load(METADATA_FILE) if METADATA_FILE.exists() else []


def semantic_recommend(movie_id, limit=10):
    """Retrieves semantic movie recommendations using FAISS vector search."""
    if index is None or not movies_metadata:
        return []

    try:
        target_movie = Movie.objects.get(id=movie_id)
    except Movie.DoesNotExist:
        return []

    if not target_movie.embedding:
        return []

    # Ensure FAISS input array is C-contiguous float32
    query_vector = np.ascontiguousarray(
        np.array([target_movie.embedding], dtype="float32")
    )

    # Perform FAISS similarity search
    scores, indices = index.search(query_vector, limit + 1)

    matched_movie_ids = []
    score_map = {}

    for idx, score in zip(indices[0], scores[0]):
        # Ignore invalid/padding indices or out-of-bound metadata indices
        if idx < 0 or idx >= len(movies_metadata):
            continue

        candidate_id = movies_metadata[idx].get("id")

        # Skip self-recommendation
        if candidate_id == movie_id or candidate_id is None:
            continue

        matched_movie_ids.append(candidate_id)
        score_map[candidate_id] = round(float(score) * 100, 2)

        if len(matched_movie_ids) >= limit:
            break

    # Efficient batch database fetch to eliminate N+1 queries
    movie_objects_dict = Movie.objects.in_bulk(matched_movie_ids)

    # Reconstruct array maintaining FAISS rank ordering
    results = [
        {
            "movie": movie_objects_dict[m_id],
            "similarity": score_map[m_id],
            "algorithm": "Semantic AI",
        }
        for m_id in matched_movie_ids
        if m_id in movie_objects_dict
    ]

    return results