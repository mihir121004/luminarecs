from django.core.management.base import BaseCommand

from platform_engine.ml_engine.train_model import (
    train_recommendation_model
)

class Command(BaseCommand):

    help = "Train LuminaRecs recommendation AI"

    def handle(
            self,
            *args,
            **kwargs
    ):

        train_recommendation_model()
        