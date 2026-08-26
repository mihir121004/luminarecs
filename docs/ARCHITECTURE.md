# LuminaRecs architecture

`core` contains Django project configuration. `platform_engine` is currently the
application boundary for movie data, account features, interactions, and
recommendations.

## Incremental target layout

As the application grows, split `platform_engine` by domain rather than adding
more functions to `views.py` or more models to `models.py`:

- `movies`: catalog, actors, genres, collections, and search.
- `accounts`: authentication, profiles, and account signals.
- `interactions`: reviews, wishlists, watch history, and telemetry.
- `recommendations`: ML services, training commands, APIs, and model storage.

Keep templates grouped by the same domains, and move page-specific inline CSS
and JavaScript into `static/css/` and `static/js/`. Do this feature by feature
so URL names and rendered pages remain stable during the migration.

## Runtime artifacts

Logs, SQLite databases, and generated ML indexes are runtime artifacts. They
are ignored by Git and should be provisioned through the deployment environment
or a dedicated model-artifact store.
