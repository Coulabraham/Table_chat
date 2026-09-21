from django.utils import timezone

from .services import track_request_session


class AccountSessionActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(request, "user", None) and request.user.is_authenticated:
            record = track_request_session(request)
            if record and record.last_activity_at < timezone.now() - timezone.timedelta(minutes=1):
                record.last_activity_at = timezone.now()
                record.save(update_fields=("last_activity_at",))
        return self.get_response(request)
