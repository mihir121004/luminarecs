from django.core.management import call_command
from django.core.management.base import BaseCommand

from platform_engine.models import Movie


class Command(BaseCommand):
    help = (
        "Seed the demo database from the committed fixture "
        "(platform_engine/fixtures/demo_movies.json). Idempotent: skips "
        "seeding when movies already exist."
    )

    def handle(self, *args, **options):
        if Movie.objects.exists():
            self.stdout.write(
                f"Movies already present ({Movie.objects.count()}) — skipping demo seed."
            )
            return

        self.stdout.write("Loading demo fixture (genres + movies)...")
        call_command("loaddata", "demo_movies", verbosity=1)

        self.stdout.write(
            self.style.SUCCESS(f"Demo seed complete: {Movie.objects.count()} movies.")
        )
