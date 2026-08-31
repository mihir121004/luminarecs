#!/usr/bin/env python3
import os, sys, time, subprocess
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import django; django.setup()
from playwright.sync_api import sync_playwright

server = subprocess.Popen([sys.executable, 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=os.path.dirname(os.path.abspath(__file__)))
time.sleep(3)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width':1920,'height':1080})
    try:
        page.goto('http://127.0.0.1:8000/trailers/', wait_until='domcontentloaded', timeout=60000)
        time.sleep(3)
        page.screenshot(path='screenshots/14_trailers.png', full_page=True)
        print('OK trailers')
    except Exception as e:
        print(f'FAIL: {e}')
    browser.close()

server.terminate()
server.wait(timeout=5)
