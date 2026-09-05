from django.contrib import admin
from .models import Game, GameInvitation, GameParticipant

admin.site.register([Game, GameInvitation, GameParticipant])

