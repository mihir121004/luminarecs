# Generated manually to keep feedback validation aligned with the model.

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("platform_engine", "0027_review_rating_validation"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userfeedback",
            name="rating",
            field=models.FloatField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(10),
                ],
            ),
        ),
    ]
