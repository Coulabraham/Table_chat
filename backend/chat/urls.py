from django.urls import path

from .views import (
    ConversationDetailView,
    ConversationListCreateView,
    ConversationPreferencesView,
    GroupCreateView,
    GroupInvitationCollectionView,
    GroupLeaveView,
    GroupMemberDetailView,
    GroupMemberListView,
    GroupTransferOwnerView,
    InvitationCancelView,
    InvitationInboxView,
    InvitationResponseView,
    MessageListCreateView,
    ReadCursorView,
)

urlpatterns = [
    path("conversations/", ConversationListCreateView.as_view()),
    path("groups/", GroupCreateView.as_view()),
    path("group-invitations/", InvitationInboxView.as_view()),
    path("group-invitations/<uuid:invitation_id>/<str:action>/", InvitationResponseView.as_view()),
    path("group-invitations/<uuid:invitation_id>/", InvitationCancelView.as_view()),
    path("conversations/<uuid:conversation_id>/", ConversationDetailView.as_view()),
    path("conversations/<uuid:conversation_id>/messages/", MessageListCreateView.as_view()),
    path("conversations/<uuid:conversation_id>/invitations/", GroupInvitationCollectionView.as_view()),
    path("conversations/<uuid:conversation_id>/members/", GroupMemberListView.as_view()),
    path("conversations/<uuid:conversation_id>/members/<int:user_id>/", GroupMemberDetailView.as_view()),
    path("conversations/<uuid:conversation_id>/transfer-owner/", GroupTransferOwnerView.as_view()),
    path("conversations/<uuid:conversation_id>/leave/", GroupLeaveView.as_view()),
    path("conversations/<uuid:conversation_id>/read/", ReadCursorView.as_view()),
    path("conversations/<uuid:conversation_id>/preferences/", ConversationPreferencesView.as_view()),
]
