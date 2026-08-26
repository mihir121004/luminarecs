"""Find local accounts that share an email (blocks social linking)."""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from collections import Counter

from django.contrib.auth.models import User

emails = Counter(u.email.lower() for u in User.objects.all() if u.email)
dups = {e: n for e, n in emails.items() if n > 1}

if not dups:
    print("No duplicate emails — social linking will work smoothly.")
else:
    print("DUPLICATE EMAILS FOUND (associate_by_email will refuse these):")
    for e, n in dups.items():
        print(f"  {e}  ({n} accounts):")
        for u in User.objects.filter(email__iexact=e):
            socials = [f"{s.provider}" for s in u.social_auth.all()]
            print(
                f"    pk={u.pk:<5} username={u.username!r:<15} "
                f"joined={u.date_joined:%d %b %Y}  social=[{','.join(socials)}]"
            )
