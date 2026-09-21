from django.contrib import admin
from .models import Conversation, DeliveryOutbox, Message

admin.site.register(Conversation)
admin.site.register(Message)
admin.site.register(DeliveryOutbox)

