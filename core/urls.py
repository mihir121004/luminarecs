# filepath: core/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("platform_engine.frontend_urls")),
    path("api/", include('platform_engine.urls')),
    # OAuth2 login flow (Google / GitHub) - /social/login/<backend>/ etc.
    path("social/", include("social_django.urls")),
]

# Custom error pages (cinematic 404 / 500 templates)
handler404 = 'platform_engine.views.custom_404'
handler500 = 'platform_engine.views.custom_500'