"""
Movie embedding generation using TF-IDF vectorization.

This module generates embeddings for all movies in a single efficient pass,
avoiding the O(n²) complexity bug in the original implementation.
"""

import logging
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from django.db import transaction

from ..models import Movie
from ..utils.logging import log_ml_operation, log_execution

logger = logging.getLogger(__name__)


@log_execution
def generate_movie_embeddings(batch_size: int = 100, save_to_db: bool = True) -> dict:
    """
    Generate TF-IDF embeddings for all movies efficiently.
    
    This function:
    1. Collects all movie documents once
    2. Trains a single TF-IDF vectorizer
    3. Generates embeddings for all movies
    4. Saves embeddings to database in batches
    
    Args:
        batch_size: Number of movies to save per batch transaction
        save_to_db: Whether to save embeddings to database
        
    Returns:
        Dictionary with statistics about the embedding generation
    """
    import time
    start_time = time.time()
    
    try:
        # Fetch all movies
        movies = Movie.objects.all().order_by('id')
        movie_count = movies.count()
        
        if movie_count == 0:
            logger.warning("No movies found to generate embeddings for")
            return {
                'success': True,
                'movies_processed': 0,
                'duration_seconds': time.time() - start_time,
                'message': 'No movies to process',
            }
        
        logger.info(f"Starting embedding generation for {movie_count} movies")
        
        # Prepare documents: Collect all text once
        documents = []
        movie_objects = []
        
        for movie in movies:
            # Combine all text fields for embedding
            text = " ".join(filter(None, [
                movie.title or "",
                movie.overview or "",
                movie.genres or "",
                movie.director or "",
                movie.tagline or "",
                getattr(movie, 'writer', "") or "",
            ]))
            
            if not text.strip():
                # Skip movies with no text
                logger.warning(f"Skipping movie {movie.id} - no text content")
                continue
            
            documents.append(text)
            movie_objects.append(movie)
        
        if not documents:
            logger.warning("No documents with text content found")
            return {
                'success': True,
                'movies_processed': 0,
                'duration_seconds': time.time() - start_time,
                'message': 'No movies with text content',
            }
        
        # Train vectorizer ONCE on all documents
        logger.info(f"Training TF-IDF vectorizer on {len(documents)} documents")
        vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=300,
            min_df=1,
            max_df=0.95,
        )
        
        # Fit and transform in one operation
        vectors = vectorizer.fit_transform(documents)
        
        logger.info(f"Generated embeddings with shape: {vectors.shape}")
        
        # Convert to dense array for storage
        embeddings_array = vectors.toarray()
        
        # Save embeddings in batches
        if save_to_db:
            saved_count = _save_embeddings_to_db(movie_objects, embeddings_array, batch_size)
        else:
            saved_count = len(movie_objects)
        
        duration = time.time() - start_time
        
        # Log performance metric
        log_ml_operation(
            operation='embedding_generation',
            model='TF-IDF',
            duration_ms=duration * 1000,
            success=True,
        )
        
        logger.info(
            f"Embedding generation completed: "
            f"processed={saved_count}, duration={duration:.2f}s"
        )
        
        return {
            'success': True,
            'movies_processed': saved_count,
            'duration_seconds': duration,
            'embedding_dimension': vectors.shape[1],
            'message': f'Successfully generated embeddings for {saved_count} movies',
        }
        
    except Exception as e:
        duration = time.time() - start_time
        logger.exception(f"Error generating embeddings: {e}")
        
        log_ml_operation(
            operation='embedding_generation',
            model='TF-IDF',
            duration_ms=duration * 1000,
            success=False,
        )
        
        return {
            'success': False,
            'duration_seconds': duration,
            'error': str(e),
            'message': f'Error generating embeddings: {str(e)}',
        }


def _save_embeddings_to_db(movie_objects: list, embeddings_array: np.ndarray, batch_size: int = 100) -> int:
    """
    Save embeddings to database in batches.
    
    Args:
        movie_objects: List of Movie objects
        embeddings_array: Numpy array of embeddings (rows: movies, cols: features)
        batch_size: Number of movies to save per transaction
        
    Returns:
        Number of movies successfully saved
    """
    saved_count = 0
    
    for batch_start in range(0, len(movie_objects), batch_size):
        batch_end = min(batch_start + batch_size, len(movie_objects))
        batch_movies = movie_objects[batch_start:batch_end]
        batch_embeddings = embeddings_array[batch_start:batch_end]
        
        try:
            # Use transaction for each batch
            with transaction.atomic():
                for i, movie in enumerate(batch_movies):
                    # Convert embedding to list for JSONField storage
                    embedding_list = batch_embeddings[i].tolist()
                    movie.embedding = embedding_list
                    movie.save(update_fields=['embedding'])
                    saved_count += 1
            
            logger.debug(f"Saved embedding batch: {batch_start}-{batch_end}")
            
        except Exception as e:
            logger.error(f"Error saving embedding batch {batch_start}-{batch_end}: {e}")
    
    return saved_count


def get_movie_embedding(movie_id: int) -> np.ndarray:
    """
    Retrieve embedding for a specific movie.
    
    Args:
        movie_id: Movie ID
        
    Returns:
        Numpy array of the movie's embedding
        
    Raises:
        Movie.DoesNotExist: If movie not found
    """
    movie = Movie.objects.get(id=movie_id)
    
    if not movie.embedding:
        logger.warning(f"Movie {movie_id} has no embedding")
        return np.array([])
    
    return np.array(movie.embedding)