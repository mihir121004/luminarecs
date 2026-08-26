from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import WatchHistory
from .ai_engine import generate_user_ai_profile

@receiver(post_save, sender=WatchHistory)
def update_ai(sender, instance, **kwargs):
    generate_user_ai_profile(instance.user)
