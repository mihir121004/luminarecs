from django.db import migrations


def create_movie_genre_table(apps, schema_editor):
    """Create the implicit M2M table only if a legacy database lacks it."""
    Movie = apps.get_model("platform_engine", "Movie")
    through_model = Movie._meta.get_field("genre").remote_field.through
    if through_model._meta.db_table not in schema_editor.connection.introspection.table_names():
        schema_editor.create_model(through_model)


def drop_movie_genre_table(apps, schema_editor):
    Movie = apps.get_model("platform_engine", "Movie")
    through_model = Movie._meta.get_field("genre").remote_field.through
    if through_model._meta.db_table in schema_editor.connection.introspection.table_names():
        schema_editor.delete_model(through_model)


class Migration(migrations.Migration):
    dependencies = [
        ("platform_engine", "0017_actor"),
    ]

    operations = [
        migrations.RunPython(create_movie_genre_table, drop_movie_genre_table),
    ]
