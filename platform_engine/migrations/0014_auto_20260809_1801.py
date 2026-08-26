from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('platform_engine', '0012_genre_alter_interactiontelemetry_options_and_more'),
    ]

    operations = [
        # `slug` was already added in migration 0012. This migration belongs to
        # a merged branch, so it must alter that field instead of adding the
        # column a second time on a clean database.
        migrations.AlterField(
            model_name='movie',
            name='slug',
            field=models.SlugField(
                blank=True,
                max_length=255,
                unique=True,
                null=True
            ),
        ),
    ]
