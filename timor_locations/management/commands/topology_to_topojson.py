from django.db import connection
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Create or update topology entries in the database"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("(1) Fetching features"))

        with connection.cursor() as c:
            c.execute("")