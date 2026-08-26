from django.core.management.base import BaseCommand

from platform_engine.ml_engine.embedding_engine import (
    generate_movie_embeddings
)

class Command(BaseCommand):
    help ="Generate movie AI embeddings"

    def handle(
            self,
            *args,
            **kwargs
    ):

        print(
            """
====================================
LuminaRecs Embedding Training
====================================            
"""
        )

        generate_movie_embeddings()

        print("Movie embeddings generated successfully")