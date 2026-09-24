from django.contrib import admin
from .models import Conversation, ConversationMembership, DeliveryOutbox, GroupInvitation, Message

admin.site.register(Conversation)
admin.site.register(Message)
admin.site.register(DeliveryOutbox)
admin.site.register(ConversationMembership)
admin.site.register(GroupInvitation)
