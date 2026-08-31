#!/usr/bin/env python3
"""
Luminarecs — Full Website Screenshot Tool (Desktop Only)
=========================================================
Captures EVERY page at 1920×1080, including authenticated pages.

Usage:
    python scripts/screenshot_all.py

Output:
    screenshots/  (desktop PNGs of every page)
"""

import os
import sys
import time
import subprocess

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from django.contrib.auth import get_user_model
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")
DESKTOP = {"width": 1920, "height": 1080}

# ── Public pages ──────────────────────────────────────────────
PUBLIC_PAGES = [
    ("01_lockscreen", "/"),
    ("02_landing", "/landing/"),
    ("03_login", "/login/"),
    ("04_signup", "/signup/"),
    ("05_forgot_password", "/forgot-password/"),
    ("06_forgot_password_done", "/forgot-password/done/"),
    ("07_reset_complete", "/reset-password/complete/"),
    ("08_search", "/search/"),
    ("09_discover", "/discover/"),
    ("10_collections", "/collections/"),
    ("11_movie_detail", "/movie/1284/"),
    ("12_genre", "/genre/Action/"),
    ("13_actor_profile", "/actor/1/"),
    ("14_trailers", "/trailers/"),
    ("15_onboarding", "/onboarding/"),
]

# ── Authenticated pages (captured after login) ────────────────
AUTH_PAGES = [
    ("16_homepage", "/homepage/"),
    ("17_wishlist", "/wishlist/"),
    ("18_profile", "/profile/"),
    ("19_recommendations", "/recommendations/"),
    ("20_watch_history", "/watch_history/"),
    ("21_discover_auth", "/discover/"),
    ("22_collections_auth", "/collections/"),
    ("23_search_auth", "/search/"),
    ("24_change_password", "/change-password/"),
    ("25_analytics", "/analytics/"),
    ("26_edit_profile", "/edit-profile/"),
    ("27_movie_feedback", "/feedback/1284/"),
    ("28_cinema_journal", "/cinema_journal/1/"),
    ("29_add_wishlist", "/add_to_wishlist/1284/"),
    ("30_collection_movies", "/discover/collection/marvel/"),
    ("31_director", "/director/Christopher%20Nolan/"),
]


def wait_for_server(url, timeout=30):
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def ensure_test_user():
    """Create a superuser so we can log in and capture auth pages."""
    User = get_user_model()
    username = "screenshot_user"
    email = "screenshot@test.com"
    password = "TestPass123!"
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, email, password)
        print(f"  ✅ Created test user: {username}")
    else:
        print(f"  ℹ️  Test user already exists: {username}")
    return username, password


def capture():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Start server
    print("🚀 Starting Django dev server...")
    server = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    if not wait_for_server(BASE_URL):
        print("❌ Server failed to start")
        server.terminate()
        return False

    username, password = ensure_test_user()
    print("✅ Server running. Capturing screenshots...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=DESKTOP)
        page = ctx.new_page()

        # ── Public pages ──
        for name, path in PUBLIC_PAGES:
            url = f"{BASE_URL}{path}"
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                time.sleep(1.5)
                page.add_style_tag(content="*{animation:none!important;transition:none!important}")
                filepath = os.path.join(OUTPUT_DIR, f"{name}.png")
                page.screenshot(path=filepath, full_page=True)
                print(f"  ✅ {name}.png")
            except Exception as e:
                print(f"  ❌ {name}: {e}")

        # ── Login ──
        print("\n🔐 Logging in to capture authenticated pages...")
        try:
            page.goto(f"{BASE_URL}/login/", wait_until="networkidle")
            page.fill('input[name="username"]', username)
            page.fill('input[name="password"]', password)
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            print("  ✅ Logged in successfully\n")
        except Exception as e:
            print(f"  ❌ Login failed: {e}\n")

        # ── Authenticated pages ──
        for name, path in AUTH_PAGES:
            url = f"{BASE_URL}{path}"
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                time.sleep(1.5)
                page.add_style_tag(content="*{animation:none!important;transition:none!important}")
                filepath = os.path.join(OUTPUT_DIR, f"{name}.png")
                page.screenshot(path=filepath, full_page=True)
                print(f"  ✅ {name}.png")
            except Exception as e:
                print(f"  ❌ {name}: {e}")

        browser.close()

    server.terminate()
    server.wait(timeout=5)

    count = len(PUBLIC_PAGES) + len(AUTH_PAGES)
    print(f"\n🎉 Done! {count} desktop screenshots → {OUTPUT_DIR}/")
    return True


if __name__ == "__main__":
    try:
        sys.exit(0 if capture() else 1)
    except KeyboardInterrupt:
        print("\n⛔ Cancelled.")
        sys.exit(1)
