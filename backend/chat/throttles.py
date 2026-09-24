from rest_framework.throttling import UserRateThrottle


class MessageRateThrottle(UserRateThrottle):
    scope = "message"


class GroupCreateRateThrottle(UserRateThrottle):
    scope = "group_create"


class GroupInviteRateThrottle(UserRateThrottle):
    scope = "group_invite"
