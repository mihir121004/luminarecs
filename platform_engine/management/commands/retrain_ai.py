from django.core.management.base import BaseCommand
from platform_engine.ai.feedback_trainer import (
    train_from_feedback
)

class Command(BaseCommand):
    help="Retrain recommendation AI"

    def handle(self, *args, **kwargs):
        model =train_from_feedback()

        if model is not None:
            self.stdout.write("AI model updated successfully")
        else:
            self.stdout.write("Not enough feedback")