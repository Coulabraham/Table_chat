from django.contrib import admin
from .models import Conversation, ConversationParticipant, Message

admin.site.register([Conversation, ConversationParticipant, Message])

