import time

from django.core.management.base import BaseCommand
from chat.services import publish_pending_events


class Command(BaseCommand):
    help = "Rediffuse les événements WebSocket persistés mais non confirmés."

    def add_arguments(self, parser):
        parser.add_argument("--watch", action="store_true")

    def handle(self, *args, **options):
        while True:
            publish_pending_events()
            if not options["watch"]:
                break
            time.sleep(2)
