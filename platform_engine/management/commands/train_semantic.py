from django.core.management.base import BaseCommand

from platform_engine.ml_engine.semantic_engine.train_embeddings import (
    train_embeddings,
)
from platform_engine.ml_engine.semantic_engine.vector_search import (
    create_index,
)


class Command(BaseCommand):

    help = "Train Semantic AI"

    def handle(
        self,
        *args,
        **kwargs,
    ):

        train_embeddings()

        create_index()

        self.stdout.write("Semantic AI completed")