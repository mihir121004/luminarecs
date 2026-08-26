#!/usr/bin/env python
"""
LuminaRecs full-site page & styling audit.

Crawls every public + authenticated page with Django's test client,
verifies HTTP status of each page AND of every /static/ + /media/ asset
referenced in the rendered HTML. Lists external (CDN) hosts so CSP can
be compared against what pages actually load.

Run from project root:
    PYTHONPATH=. venv/bin/python scripts/site_audit.py
"""
import os
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django  # noqa: E402

django.setup()

# Runtime-only patch so Django's standalone test client (host "testserver")
# passes ALLOWED_HOSTS. The dev/prod .env is NOT modified.
from django.conf import settings  # noqa: E402

if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']

# Audit-only patch (process memory, no files touched): stop rate limiter
# from throttling the hundreds of requests this crawl makes.
from platform_engine.utils.security import RateLimitMiddleware  # noqa: E402

RateLimitMiddleware._check_rate_limit = lambda self, request: True

from django.test import Client  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from platform_engine.models import Movie  # noqa: E402

User = get_user_model()
AUDIT_USER = 'audit_crawler'


def make_sample_kwargs():
    movie = Movie.objects.first()
    movie_id = movie.id if movie else 1
    genres_raw = (movie.genres if movie and movie.genres else '') or 'Action'
    genre_name = [g.strip() for g in genres_raw.split(',') if g.strip()][0]
    actor_id = movie_id  # actor_profile falls back gracefully on bad ids
    slug = getattr(movie, 'slug', None)
    return movie_id, genre_name, actor_id, slug


def main():
    movie_id, genre_name, actor_id, slug = make_sample_kwargs()
    print(f'sample data -> movie={movie_id} genre={genre_name!r} '
          f'actor={actor_id} slug={slug}')
    PAGES = build_pages(movie_id, genre_name, actor_id, slug)
    ASSET_RE = re.compile(
        r'(?:src|href)=["\'](/static/[^"\'#?]+|/media/[^"\'#?]+)', re.I)
    CDN_RE = re.compile(r'https?://([a-z0-9.-]+)', re.I)
    report, seen_assets, cdns = [], {}, set()
    crawl(PAGES, report, seen_assets, cdns, ASSET_RE, CDN_RE)
    summarize(report, seen_assets, cdns)


def build_pages(movie_id, genre_name, actor_id, slug):
    """(name, path, needs_auth) list covering every GET route."""
    PAGES = [
        ('lockscreen(root)', '/', False),
        ('landing', '/landing/', False),
        ('login', '/login/', False),
        ('signup', '/signup/', False),
        ('forgot-password', '/forgot-password/', False),
        ('forgot-done', '/forgot-password/done/', False),
        ('reset-complete', '/reset-password/complete/', False),
        ('search', '/search/?q=act', False),
        ('trailers', '/trailers/', False),
        ('404page', '/definitely-not-a-page/', False),
        ('homepage', '/homepage/', True),
        ('discover', '/discover/', True),
        ('wishlist', '/wishlist/', True),
        ('profile', '/profile/', True),
        ('edit-profile', '/edit-profile/', True),
        ('watch_history', '/watch_history/', True),
        ('collections', '/collections/', True),
        ('analytics', '/analytics/', True),
        ('recommendations', '/recommendations/', True),
        ('onboarding', '/onboarding/', True),
        ('change-password', '/change-password/', True),
        ('pw-change-done', '/change-password/done/', True),
        ('movie-details', f'/movie/{movie_id}/', True),
        ('genre', f'/genre/{genre_name}/', True),
        ('cinema-journal', f'/cinema_journal/{movie_id}/', True),
        ('actor-profile', f'/actor/{actor_id}/', True),
    ]
    if slug:
        PAGES.append(('collection',
                      f'/discover/collection/{slug}/', True))
    return PAGES


def crawl(PAGES, report, seen_assets, cdns, ASSET_RE, CDN_RE):
    for name, path, needs_auth in PAGES:
        c = Client()
        if needs_auth:
            u, _ = User.objects.get_or_create(
                username=AUDIT_USER, defaults={'email': 'audit@local'})
            u.set_password('audit-pass-123!')
            u.is_active = True
            u.save()
            c.force_login(u)
        try:
            r = c.get(path, follow=True)
        except Exception as e:  # TemplateSyntaxError etc.
            report.append((name, path, 'EXC',
                           f'{type(e).__name__}: {e}'.replace('\n', ' ')[:90]))
            continue

        body = r.content.decode('utf-8', 'ignore')
        note_parts = []
        if name == '404page':
            note_parts.append('custom404-ok' if r.status_code == 404
                              else f'EXPECTED404-got-{r.status_code}')
        elif r.status_code != 200:
            note_parts.append(f'NON-200 final={r.status_code}')

        broken = []
        for asset in set(ASSET_RE.findall(body)):
            ar = c.get(asset)
            seen_assets[asset] = ar.status_code
            if ar.status_code != 200:
                broken.append(f'{asset}->{ar.status_code}')
        cdns.update(m.replace('\\/', '/') for m in CDN_RE.findall(body))

        if '<style' in body:
            note_parts.append('style-inline')
        if broken:
            note_parts.append('BROKEN-ASSETS: ' + '; '.join(broken))
        report.append((name, path, r.status_code,
                       ' | '.join(note_parts)))


def summarize(report, seen_assets, cdns):
    width = max(len(n) for n, _, _, _ in report)
    print('\n================ PAGE REPORT ================')
    problems = 0
    for name, path, code, note in report:
        bad = (('BROKEN-ASSETS' in note) or code == 'EXC'
               or ('NON-200' in note and name != '404page')
               or ('EXPECTED404' in note))
        if bad:
            problems += 1
        marker = '   <<<<< PROBLEM' if bad else ''
        print(f'{name:<{width}} {code} {path:<40}{note}{marker}')

    broken_assets = {a: s for a, s in seen_assets.items() if s != 200}
    print('\n================ ASSETS ================')
    print(f'unique local assets referenced: {len(seen_assets)}; '
          f'broken: {len(broken_assets)}')
    for a, s in sorted(broken_assets.items()):
        print(f'  BROKEN [{s}] {a}')

    print('\n================ EXTERNAL HOSTS ================')
    skip = {'fonts.googleapis.com', 'fonts.gstatic.com'}
    for h in sorted(cdns):
        tag = '' if h in skip or h == 'testserver' else '   <-- check CSP!'
        print(f'  {h}{tag}')

    print(f'\nSUMMARY: pages={len(report)} problem_pages={problems} '
          f'broken_assets={len(broken_assets)}')


if __name__ == '__main__':
    main()

