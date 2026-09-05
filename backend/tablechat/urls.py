from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/friends/", include("friends.urls")),
    path("api/games/", include("games.urls")),
    path("api/chat/", include("chat.urls")),
    path("api/chess/", include("chess_game.urls")),
]

