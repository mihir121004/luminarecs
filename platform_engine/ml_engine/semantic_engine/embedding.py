from sentence_transformers import SentenceTransformer

MODEL_NAME = ("all-miniLM-L6-v2")

model = SentenceTransformer(MODEL_NAME)

def generate_embedding(text):
    vector = model.encode(
        text,
        normalize_embeddings=True
    )
    return vector.tolist()