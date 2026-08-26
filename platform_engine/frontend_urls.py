from django.urls import path
from django.views.generic import RedirectView
from django.templatetags.static import static as static_url

from django.conf import settings
from django.contrib.auth import views as auth_views
from . import views


# When a fixed reset-link domain is configured, pass it (and the protocol)
# into the email context so the reset link in the email is always reachable
# regardless of which host the user submitted /forgot-password/ from.
def _password_reset_email_context():
    if settings.PASSWORD_RESET_LINK_DOMAIN:
        return {
            "domain": settings.PASSWORD_RESET_LINK_DOMAIN,
            "protocol": settings.PASSWORD_RESET_LINK_PROTOCOL or "https",
        }
    return None

urlpatterns = [
    # Legacy favicon paths browsers auto-request -> serve the brand SVG.
    # Stops the recurring 404 noise in logs.
    path(
        "favicon.ico",
        RedirectView.as_view(url=static_url("images/favicon.svg"), permanent=True),
    ),
    path(
        "apple-touch-icon.png",
        RedirectView.as_view(url=static_url("images/favicon.svg"), permanent=True),
    ),
    path(
        "apple-touch-icon-precomposed.png",
        RedirectView.as_view(url=static_url("images/favicon.svg"), permanent=True),
    ),

    path("", views.lockscreen, name="lockscreen"),
    path("landing/", views.landing, name="landing"),
    path("actor/<int:id>/", views.actor_profile, name="actor_profile"),
    path("login/", views.login, name="login"),
    path("signup/", views.signup, name="signup"),
    path("homepage/", views.homepage, name="homepage"),
    path("logout/", views.logout_view, name="logout"),
    path("wishlist/", views.wishlist, name="wishlist"),
    path("wishlist/remove/<int:movie_id>/", views.remove_from_wishlist, name="remove_from_wishlist"),
    path("profile/", views.profile, name="profile"),
    path("discover/", views.discover, name="discover"),
    path("trailers/", views.trailers, name="trailers"),
    path("movie/<int:movie_id>/", views.movie_details, name="movie_details"),
    path("watch_history/", views.watch_history, name="watch_history"),
    path("cinema_journal/<int:id>/", views.cinema_journal, name="cinema_journal"),
    path("search/", views.search_movies_page, name="search_movies_page"),
    path("add_to_wishlist/<int:movie_id>/", views.add_to_wishlist, name="add_to_wishlist"),
    path("discover/collection/<slug:slug>/", views.collection_movies, name="collection_movies"),
    path("genre/<str:genre_name>/", views.genre_movies, name="genre_movies"),
    path("actor/<str:actor_name>/", views.actor_movies, name="actor_movies"),
    path("director/<str:director_name>/", views.director_movies, name="director_movies"),
    path("edit-profile/", views.edit_profile, name="edit_profile"),
    path("recommendations/", views.personalized_recommendations, name="recommendations"),
    path("feedback/<int:movie_id>/", views.movie_feedback, name="movie_feedback"),
    path("onboarding/", views.onboarding, name="onboarding"),

    # =====================================================
    # CHANGE PASSWORD (LOGGED-IN USERS)
    # =====================================================
    path(
        "change-password/",
        auth_views.PasswordChangeView.as_view(
            template_name="change_password.html",
            success_url="/change-password/done/",
        ),
        name="change_password",
    ),
    path(
        "change-password/done/",
        auth_views.PasswordChangeDoneView.as_view(
            template_name="change_password_done.html"
        ),
        name="password_change_done",
    ),

    # =====================================================
    # COLLECTIONS & ANALYTICS
    # =====================================================
    path("collections/", views.collections_list, name="collections_list"),
    path("analytics/", views.analytics_dashboard, name="analytics_dashboard"),

    # =====================================================
    # PASSWORD RESET (FORGOT PASSWORD)
    # =====================================================
    path(
        "forgot-password/",
        auth_views.PasswordResetView.as_view(
            template_name="forgot_password.html",
            email_template_name="emails/password_reset_email.html",
            subject_template_name="emails/password_reset_subject.txt",
            success_url="/forgot-password/done/",
            extra_email_context=_password_reset_email_context(),
        ),
        name="password_reset",
    ),
    path(
        "forgot-password/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="forgot_password_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset-password/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="reset_password.html",
            success_url="/reset-password/complete/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset-password/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="reset_password_complete.html"
        ),
        name="password_reset_complete",
    ),

]
