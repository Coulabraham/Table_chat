from django.urls import path

from .views import ConversationDetailView, ConversationListCreateView, MessageListCreateView

urlpatterns = [
    path("conversations/", ConversationListCreateView.as_view()),
    path("conversations/<uuid:conversation_id>/", ConversationDetailView.as_view()),
    path("conversations/<uuid:conversation_id>/messages/", MessageListCreateView.as_view()),
]

