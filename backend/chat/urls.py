from django.urls import path
from .views import ConversationListCreateView, MarkReadView, MessageListCreateView

urlpatterns = [
    path("conversations/", ConversationListCreateView.as_view()),
    path("conversations/<uuid:conversation_id>/messages/", MessageListCreateView.as_view()),
    path("conversations/<uuid:conversation_id>/read/", MarkReadView.as_view()),
]
