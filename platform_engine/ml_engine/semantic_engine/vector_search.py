from pathlib import Path

import faiss
import joblib
import numpy as np

MODEL_PATH = Path("platform_engine/ml_engine/model_data")


def create_index():
    """Loads movie embeddings, converts them into a contiguous float32 numpy array,

    and builds an inner-product (IndexFlatIP) FAISS index file.
    """
    embeddings_file = MODEL_PATH / "movie_embeddings.pkl"
    index_file = MODEL_PATH / "faiss.index"

    if not embeddings_file.exists():
        print(f"Error: Embeddings file not found at {embeddings_file}")
        return

    # Load raw embeddings list/matrix
    embeddings = joblib.load(embeddings_file)

    # FAISS strictly requires float32 C-contiguous numpy arrays
    vectors = np.ascontiguousarray(np.array(embeddings, dtype="float32"))

    if vectors.ndim != 2 or vectors.shape[0] == 0:
        print("Error: Embeddings must be a non-empty 2D array.")
        return

    dimension = vectors.shape[1]

    # Initialize IndexFlatIP (Inner Product cosine similarity index)
    index = faiss.IndexFlatIP(dimension)
    index.add(vectors)

    # Ensure output directory exists and save index
    MODEL_PATH.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_file))

    print(
        f"FAISS index created successfully with {index.ntotal} vectors "
        f"(dimension={dimension})."
    )