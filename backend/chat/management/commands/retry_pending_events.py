import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from chat.models import DeliveryOutbox
from chat.services import publish_message


class Command(BaseCommand):
    help = "Rediffuse les événements WebSocket persistés mais non confirmés."

    def add_arguments(self, parser):
        parser.add_argument("--watch", action="store_true")

    def handle(self, *args, **options):
        while True:
            ids = list(DeliveryOutbox.objects.filter(delivered_at__isnull=True, next_attempt_at__lte=timezone.now()).values_list("message_id", flat=True)[:100])
            for message_id in ids:
                publish_message(message_id)
            if not options["watch"]:
                break
            time.sleep(2)
