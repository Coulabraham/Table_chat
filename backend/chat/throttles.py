from rest_framework.throttling import UserRateThrottle


class MessageRateThrottle(UserRateThrottle):
    scope = "message"

