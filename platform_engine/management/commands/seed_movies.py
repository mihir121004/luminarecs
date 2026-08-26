import os
import time
import requests
from dotenv import load_dotenv

from django.core.management.base import BaseCommand
from platform_engine.models import Actor, Genre, Movie

load_dotenv()


class Command(BaseCommand):
    help = "Import movies from TMDB"

    TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_URL = "https://image.tmdb.org/t/p/"

    session = requests.Session()
    session.headers.update({"User-Agent": "LuminaRecs Movie Importer"})

    credits_cache = {}
    trailer_cache = {}

    # ==================================================
    # TMDB REQUEST
    # ==================================================

    def fetch_tmdb(self, endpoint: str, params: dict = None):
        url = self.BASE_URL + endpoint
        query = {"api_key": self.TMDB_API_KEY, "language": "en-US"}

        if params:
            query.update(params)

        for attempt in range(5):
            try:
                response = self.session.get(url, params=query, timeout=30)

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 429:
                    self.stdout.write(
                        self.style.WARNING("TMDB rate limit. Waiting...")
                    )
                    time.sleep(10)
                    continue

                if response.status_code == 401:
                    self.stdout.write(
                        self.style.ERROR("Invalid TMDB API KEY")
                    )
                    return None

                self.stdout.write(
                    self.style.WARNING(f"TMDB Error {response.status_code}")
                )

            except requests.exceptions.RequestException as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"Connection retry {attempt + 1}/5 : {e}"
                    )
                )
                time.sleep(5)

        return None

    # ==================================================
    # MOVIE DETAILS
    # ==================================================

    def get_movie_details(self, movie_id: int):
        return self.fetch_tmdb(f"/movie/{movie_id}")

    # ==================================================
    # TRAILER
    # ==================================================

    def get_trailer(self, movie_id: int):
        if movie_id in self.trailer_cache:
            return self.trailer_cache[movie_id]

        data = self.fetch_tmdb(f"/movie/{movie_id}/videos")
        trailer = ""

        if data:
            for video in data.get("results", []):
                if (
                    video.get("site") == "YouTube"
                    and video.get("type") == "Trailer"
                ):
                    trailer = video.get("key", "")
                    break

        self.trailer_cache[movie_id] = trailer
        return trailer

    # ==================================================
    # CREDITS
    # ==================================================

    def get_credits(self, movie_id: int):
        if movie_id in self.credits_cache:
            return self.credits_cache[movie_id]

        data = self.fetch_tmdb(f"/movie/{movie_id}/credits")
        if not data:
            return [], "", ""

        cast = []
        for person in data.get("cast", [])[:10]:
            cast.append(
                {
                    "id": person.get("id"),
                    "name": person.get("name", ""),
                    "character": person.get("character", ""),
                    "photo": (
                        f"{self.IMAGE_URL}w300{person.get('profile_path')}"
                        if person.get("profile_path")
                        else ""
                    ),
                }
            )

        director = ""
        writer = ""

        for crew in data.get("crew", []):
            if crew.get("job") == "Director":
                director = crew.get("name", "")
            if crew.get("job") in ["Writer", "Screenplay"]:
                writer = crew.get("name", "")

        self.credits_cache[movie_id] = (cast, director, writer)
        return cast, director, writer

    # ==================================================
    # SAVE ACTORS
    # ==================================================

    def save_actors(self, cast: list, movie: Movie):
        for item in cast:
            actor_id = item.get("id")
            if not actor_id:
                continue

            details = self.fetch_tmdb(f"/person/{actor_id}")
            if not details:
                continue

            actor, created = Actor.objects.update_or_create(
                tmdb_id=actor_id,
                defaults={
                    "name": details.get("name", ""),
                    "profile_image": (
                        f"{self.IMAGE_URL}w500{details.get('profile_path')}"
                        if details.get("profile_path")
                        else ""
                    ),
                    "biography": details.get("biography", ""),
                    "birthday": details.get("birthday") or None,
                    "place_of_birth": details.get("place_of_birth", ""),
                    "known_for_department": details.get(
                        "known_for_department", ""
                    ),
                    "popularity": details.get("popularity", 0),
                },
            )
            actor.movies.add(movie)

    # ==================================================
    # HANDLE
    # ==================================================

    def handle(self, *args, **kwargs):
        self.stdout.write(
            self.style.SUCCESS("\n====================================")
        )
        self.stdout.write(
            self.style.SUCCESS(" LuminaRecs TMDB Import Started")
        )
        self.stdout.write(
            self.style.SUCCESS("====================================")
        )

        total = 0

        for page in range(1, 51):
            self.stdout.write(f"\nFetching Page {page}/50")

            data = self.fetch_tmdb("/movie/popular", {"page": page})
            if not data:
                continue

            for item in data.get("results", []):
                try:
                    movie_id = item.get("id")

                    details = self.get_movie_details(movie_id)
                    if not details:
                        continue

                    cast, director, writer = self.get_credits(movie_id)
                    trailer = self.get_trailer(movie_id)

                    genres = details.get("genres", [])
                    genre_text = ", ".join([g.get("name") for g in genres])

                    keywords_data = self.fetch_tmdb(
                        f"/movie/{movie_id}/keywords"
                    )
                    keywords = ""
                    if keywords_data:
                        keywords = ", ".join(
                            [
                                k["name"]
                                for k in keywords_data.get("keywords", [])
                            ]
                        )

                    release_date = details.get("release_date")
                    if release_date == "":
                        release_date = None

                    year = None
                    if release_date:
                        year = int(release_date[:4])

                    movie, created = Movie.objects.update_or_create(
                        tmdb_id=movie_id,
                        defaults={
                            "title": details.get("title", ""),
                            "overview": details.get("overview", ""),
                            "genres": genre_text,
                            "keywords": keywords,
                            "poster_url": (
                                f"{self.IMAGE_URL}w500{details.get('poster_path')}"
                                if details.get("poster_path")
                                else ""
                            ),
                            "backdrop_url": (
                                f"{self.IMAGE_URL}original{details.get('backdrop_path')}"
                                if details.get("backdrop_path")
                                else ""
                            ),
                            "release_date": release_date,
                            "release_year": year,
                            "runtime": details.get("runtime"),
                            "tagline": details.get("tagline", ""),
                            "director": director,
                            "writer": writer,
                            "cast_data": cast,
                            "trailer_key": trailer,
                            "vote_average": details.get("vote_average", 0),
                            "popularity_score": details.get("popularity", 0),
                            "budget": details.get("budget", 0),
                            "revenue": details.get("revenue", 0),
                            "status": details.get("status", ""),
                        },
                    )

                    movie.genre.clear()
                    for g in genres:
                        genre, _ = Genre.objects.get_or_create(
                            name=g.get("name")
                        )
                        movie.genre.add(genre)

                    self.save_actors(cast, movie)

                    total += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"Imported: {movie.title}")
                    )

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Skipped {item.get('title')} : {e}")
                    )
                    continue

        self.stdout.write(
            self.style.SUCCESS(f"\nImport Completed. Movies: {total}")
        )