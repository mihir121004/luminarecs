#!/usr/bin/env python3
"""
Luminarecs Website Screenshot Tool
===================================
Captures screenshots of every public page using Playwright + Django dev server.

Usage:
    python scripts/screenshot_site.py

Output:
    screenshots/ folder with PNG images of each page
"""

import os
import sys
import time
import subprocess
import signal

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
django.setup()

from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")

# Pages to screenshot (public, no login required)
PAGES = [
    ("lockscreen", "/"),
    ("landing", "/landing/"),
    ("login", "/login/"),
    ("signup", "/signup/"),
    ("forgot_password", "/forgot-password/"),
    ("forgot_password_done", "/forgot-password/done/"),
    ("search", "/search/"),
    ("discover", "/discover/"),
    ("collections", "/collections/"),
    ("movie_detail", "/movie/1284/"),
    ("genre_action", "/genre/Action/"),
    ("actor_profile", "/actor/1/"),
]

# Viewport sizes for responsive screenshots
VIEWPORTS = {
    "desktop": {"width": 1920, "height": 1080},
    "tablet": {"width": 768, "height": 1024},
    "mobile": {"width": 375, "height": 812},
}


def wait_for_server(url, timeout=30):
    """Wait until the Django server is responding."""
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def capture_screenshots():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Start Django dev server
    print("🚀 Starting Django development server...")
    server_proc = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )

    if not wait_for_server(BASE_URL):
        print("❌ Server failed to start!")
        server_proc.terminate()
        return False

    print("✅ Server running. Capturing screenshots...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for name, path in PAGES:
            for vp_name, vp_size in VIEWPORTS.items():
                page = browser.new_page(viewport=vp_size)
                url = f"{BASE_URL}{path}"

                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    # Let any animations/transitions settle
                    time.sleep(1.5)

                    # Hide any dynamic elements that might cause inconsistency
                    page.add_style_tag(content="""
                        * { animation: none !important; transition: none !important; }
                    """)

                    filename = f"{name}_{vp_name}.png"
                    filepath = os.path.join(OUTPUT_DIR, filename)
                    page.screenshot(path=filepath, full_page=True)
                    print(f"  ✅ {filename}")

                except Exception as e:
                    print(f"  ❌ {name}_{vp_name}: {e}")

                page.close()

        browser.close()

    # Stop server
    server_proc.terminate()
    server_proc.wait(timeout=5)

    total = len(PAGES) * len(VIEWPORTS)
    print(f"\n🎉 Done! {total} screenshots saved to: {OUTPUT_DIR}/")
    print("   Use these for GitHub README, LinkedIn, and your portfolio.")
    return True


if __name__ == "__main__":
    try:
        success = capture_screenshots()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⛔ Cancelled.")
        sys.exit(1)
