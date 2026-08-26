"""
TMDB bulk importer.

Usage
-----
    # Fast bulk import straight from TMDB list endpoints (~5 min for 10k)
    python manage.py seed_movies --count 10000

    # Bulk import + deep-enrich most popular (details/cast/trailer) -
    # ONE api call per enriched movie
    python manage.py seed_movies --count 10000 --enrich --enrich-limit 1000

    # Enrich already-imported movies without importing more
    python manage.py seed_movies --enrich-only --enrich-limit 500

Design notes
------------
* List endpoints already carry title/overview/posters/release/votes, so
  the bulk phase needs ZERO per-movie api calls.
* Deep enrichment collapses 4 former calls into one via
  append_to_response=credits,videos,keywords.
* Actor biographies are intentionally NOT fetched during bulk import
  (that used to cost 10 extra calls/movie); actors are created from
  credits data instead.
"""

import os
import time

import requests
from dotenv import load_dotenv

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from platform_engine.models import Actor, Genre, Movie

load_dotenv()

# Official TMDB movie genre-id -> name mapping (stable for years).
TMDB_GENRES = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
}


class Command(BaseCommand):
    help = "Bulk-import movies from TMDB (supports tens of thousands)."

    TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_URL = "https://image.tmdb.org/t/p/"

    # Fields owned by the BULK phase (available in list payloads).
    BULK_FIELDS = [
        "title", "slug", "overview", "genres", "poster_url", "backdrop_url",
        "release_date", "release_year", "language", "vote_average",
        "popularity_score", "updated_at",
    ]
    # Extra fields only the ENRICH phase may touch.
    DETAIL_FIELDS = [
        "keywords", "runtime", "tagline", "director", "writer",
        "cast_data", "trailer_key", "budget", "revenue", "status",
        "production_companies",
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--count", type=int, default=10000,
            help="Target total movies in DB (default 10000)",
        )
        parser.add_argument(
            "--batch-size", type=int, default=500,
            help="Rows per DB upsert batch (default 500)",
        )
        parser.add_argument(
            "--delay", type=float, default=0.15,
            help="Seconds between API requests (default 0.15 ~= 6 req/s)",
        )
        parser.add_argument(
            "--enrich", action="store_true",
            help="Deep-enrich most popular imported movies afterwards",
        )
        parser.add_argument(
            "--enrich-limit", type=int, default=500,
            help="How many movies to deep-enrich when --enrich is set",
        )
        parser.add_argument(
            "--enrich-only", action="store_true",
            help="Skip importing; only enrich what is already in the DB",
        )

    # ==================================================
    # TMDB HTTP
    # ==================================================

    def fetch(self, endpoint, params=None):
        query = {"api_key": self.TMDB_API_KEY, "language": "en-US"}
        if params:
            query.update(params)

        for attempt in range(6):
            try:
                response = self.session.get(
                    self.BASE_URL + endpoint, params=query, timeout=30
                )
                if response.status_code == 200:
                    time.sleep(self.delay)
                    return response.json()

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 10))
                    self.stdout.write(
                        self.style.WARNING(f"Rate limited - sleep {retry_after}s")
                    )
                    time.sleep(retry_after)
                    continue

                if response.status_code == 401:
                    self.stdout.write(self.style.ERROR("Invalid TMDB API key"))
                    return None

                self.stdout.write(
                    self.style.WARNING(f"TMDB error {response.status_code}")
                )
                time.sleep(2 * (attempt + 1))

            except requests.exceptions.RequestException as exc:
                self.stdout.write(
                    self.style.WARNING(f"Network retry {attempt + 1}/6: {exc}")
                )
                time.sleep(3)

        return None

    # ==================================================
    # PHASE 1 - COLLECT LIST PAYLOADS
    # ==================================================

    def collect_items(self, target):
        """Pull list pages from several endpoints until `target` unique ids."""
        sources = [
            ("/movie/popular", {}),
            ("/movie/top_rated", {}),
            ("/discover/movie", {"sort_by": "popularity.desc",
                                 "vote_count.gte": 50}),
            ("/discover/movie", {"sort_by": "primary_release_date.desc",
                                 "vote_count.gte": 10,
                                 "primary_release_date.lte": "2024-12-31"}),
        ]
        items = {}
        requests_made = 0

        for endpoint, extra in sources:
            if len(items) >= target:
                break

            for page in range(1, 501):  # TMDB hard cap: page 500
                if len(items) >= target:
                    break

                data = self.fetch(endpoint, {**extra, "page": page})
                requests_made += 1
                if not data:
                    break  # dead source - try next one

                results = data.get("results", [])
                for item in results:
                    if item.get("id"):
                        items[item["id"]] = item

                if page % 25 == 0 or len(items) >= target:
                    self.stdout.write(
                        f"  {endpoint} p.{page} -> "
                        f"{len(items)} unique movies collected"
                    )
                if len(results) < 20:
                    break  # source exhausted

        self.stdout.write(
            self.style.SUCCESS(
                f"Collected {len(items)} unique movies "
                f"in {requests_made} requests"
            )
        )
        return items

    # ==================================================
    # PHASE 2 - BULK WRITE
    # ==================================================

    @staticmethod
    def _genre_names(genre_ids):
        names = [TMDB_GENRES.get(gid) for gid in genre_ids or []]
        return ", ".join(n for n in names if n)

    def _unique_slug(self, title, tmdb_id):
        """Deterministic + collision-proof: title + tmdb id.

        At 10k+ scale duplicate titles are guaranteed ('Scary Movie'...),
        and slug uniqueness is DB-enforced - so always suffix the tmdb id
        instead of racing availability checks.
        """
        base = slugify(title)[:235] or "movie"
        return f"{base}-{tmdb_id}"

    def bulk_write(self, items):
        """Upsert list-payload rows; enrich-only fields stay untouched."""
        now = timezone.now()
        rows = []

        for tmdb_id, item in items.items():
            release_date = item.get("release_date") or None
            year = int(release_date[:4]) if release_date else None

            movie = Movie(
                tmdb_id=tmdb_id,
                title=item.get("title") or "",
                slug=self._unique_slug(item.get("title"), tmdb_id),
                overview=item.get("overview") or "",
                genres=self._genre_names(item.get("genre_ids")),
                poster_url=(
                    f"{self.IMAGE_URL}w500{item['poster_path']}"
                    if item.get("poster_path") else ""
                ),
                backdrop_url=(
                    f"{self.IMAGE_URL}original{item['backdrop_path']}"
                    if item.get("backdrop_path") else ""
                ),
                release_date=release_date,
                release_year=year,
                language=(item.get("original_language") or "").upper(),
                vote_average=item.get("vote_average") or 0,
                popularity_score=item.get("popularity") or 0,
                updated_at=now,
            )
            movie._genre_ids = item.get("genre_ids") or []
            rows.append(movie)

        written = 0
        from django.db import connection
        from django.db.utils import IntegrityError

        for start in range(0, len(rows), self.batch_size):
            batch = rows[start:start + self.batch_size]
            kwargs = {
                "batch_size": min(self.batch_size, 500),
                "update_conflicts": True,
                "update_fields": self.BULK_FIELDS,
            }
            # MySQL infers the conflict target from the table's unique keys;
            # Postgres/SQLite require it explicitly.
            if connection.vendor != "mysql":
                kwargs["unique_fields"] = ["tmdb_id"]
            try:
                Movie.objects.bulk_create(batch, **kwargs)
            except IntegrityError as exc:
                # Never let one bad batch kill a multi-hour import.
                self.stdout.write(
                    self.style.ERROR(f"Batch @{start} skipped: {exc}")
                )
                continue
            self._sync_genres(batch)
            written += len(batch)
            self.stdout.write(f"  upserted {written}/{len(rows)}")

        return written

    def _sync_genres(self, batch):
        """Bulk-attach Genre M2M links for one upserted batch."""
        wanted_names = {
            TMDB_GENRES[g]
            for row in batch for g in row._genre_ids
            if g in TMDB_GENRES
        }
        if not wanted_names:
            return

        genre_objs = dict(
            Genre.objects.filter(name__in=wanted_names).values_list(
                "name", "pk"
            )
        )
        for name in wanted_names - set(genre_objs):
            obj = Genre.objects.create(name=name)
            genre_objs[name] = obj.pk

        pk_map = dict(
            Movie.objects.filter(tmdb_id__in=[r.tmdb_id for r in batch])
            .values_list("tmdb_id", "pk")
        )

        Through = Movie.genre.through
        links = []
        for row in batch:
            movie_pk = pk_map.get(row.tmdb_id)
            if not movie_pk:
                continue
            for gid in row._genre_ids:
                name = TMDB_GENRES.get(gid)
                if name and name in genre_objs:
                    links.append(
                        Through(movie_id=movie_pk, genre_id=genre_objs[name])
                    )
        if links:
            Through.objects.bulk_create(links, ignore_conflicts=True)

    # ==================================================
    # PHASE 3 - DEEP ENRICHMENT (ONE request per movie)
    # ==================================================

    def enrich(self, queryset, limit):
        targets = list(
            queryset.order_by("-popularity_score")
            .values_list("tmdb_id", flat=True)[:limit]
        )
        done = 0
        for tmdb_id in targets:
            data = self.fetch(
                f"/movie/{tmdb_id}",
                {"append_to_response": "credits,videos,keywords"},
            )
            if not data:
                continue

            credits = data.get("credits", {})
            cast = [
                {
                    "id": person.get("id"),
                    "name": person.get("name", ""),
                    "character": person.get("character", ""),
                    "photo": (
                        f"{self.IMAGE_URL}w300{person['profile_path']}"
                        if person.get("profile_path") else ""
                    ),
                }
                for person in credits.get("cast", [])[:10]
            ]

            director = writer = ""
            for crew in credits.get("crew", []):
                if crew.get("job") == "Director" and not director:
                    director = crew.get("name", "")
                if crew.get("job") in ("Writer", "Screenplay"):
                    writer = crew.get("name", "")

            trailer = ""
            for video in data.get("videos", {}).get("results", []):
                if video.get("site") == "YouTube" \
                        and video.get("type") == "Trailer":
                    trailer = video.get("key", "")
                    break

            keywords = ", ".join(
                k.get("name", "")
                for k in data.get("keywords", {}).get("keywords", [])
                if k.get("name")
            )

            Movie.objects.filter(tmdb_id=tmdb_id).update(
                runtime=data.get("runtime"),
                tagline=data.get("tagline") or "",
                director=director,
                writer=writer,
                cast_data=cast,
                trailer_key=trailer,
                keywords=keywords,
                budget=data.get("budget") or 0,
                revenue=data.get("revenue") or 0,
                status=data.get("status") or "",
                production_companies=", ".join(
                    c.get("name", "")
                    for c in data.get("production_companies", [])[:6]
                ),
            )
            self._upsert_actors(cast, tmdb_id)

            done += 1
            if done % 50 == 0:
                self.stdout.write(f"  enriched {done}/{len(targets)}")

        self.stdout.write(self.style.SUCCESS(f"Enriched {done} movies"))

    def _upsert_actors(self, cast, movie_tmdb_id):
        """Create/link actors straight from credits - NO /person lookups."""
        by_tmdb = {c["id"]: c for c in cast if c.get("id")}
        if not by_tmdb:
            return

        existing = {
            a.tmdb_id: a
            for a in Actor.objects.filter(tmdb_id__in=by_tmdb.keys())
        }
        new_actors = [
            Actor(
                tmdb_id=aid,
                name=c.get("name", ""),
                profile_image=(
                    f"{self.IMAGE_URL}w500{c['profile_path']}"
                    if c.get("profile_path") else ""
                ),
            )
            for aid, c in by_tmdb.items() if aid not in existing
        ]
        if new_actors:
            Actor.objects.bulk_create(new_actors, batch_size=500)
            for actor in new_actors:
                existing[actor.tmdb_id] = actor

        movie_pk = Movie.objects.filter(
            tmdb_id=movie_tmdb_id
        ).values_list("pk", flat=True).first()
        if not movie_pk:
            return

        Through = Actor.movies.through
        Through.objects.bulk_create(
            [
                Through(actor_id=a.pk, movie_id=movie_pk)
                for a in existing.values()
            ],
            ignore_conflicts=True,
        )

    # ==================================================
    # ENTRY POINT
    # ==================================================

    def handle(self, *args, **options):
        self.batch_size = options["batch_size"]
        self.delay = options["delay"]
        count = options["count"]
        enrich_limit = options["enrich_limit"]

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "LuminaRecs Importer/2.0"})

        if not self.TMDB_API_KEY:
            self.stdout.write(self.style.ERROR("TMDB_API_KEY missing in .env"))
            return

        self.stdout.write(self.style.SUCCESS("\n=== LuminaRecs TMDB Import ==="))

        before = Movie.objects.count()

        if not options["enrich_only"]:
            need = max(count - before, 0)
            if need == 0:
                self.stdout.write(
                    f"Already have {before} movies (target {count}) - "
                    f"bulk phase skipped."
                )
            else:
                self.stdout.write(f"Bulk phase: importing {need} movies...")
                items = self.collect_items(need)
                if items:
                    self.bulk_write(items)

        if options["enrich"] or options["enrich_only"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nEnrichment phase: top {enrich_limit} by popularity"
                )
            )
            self.enrich(Movie.objects.all(), enrich_limit)

        after = Movie.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Movies in DB: {before} -> {after} (+{after - before})"
            )
        )