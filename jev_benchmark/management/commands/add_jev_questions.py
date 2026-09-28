import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from jev_benchmark.models import Question


class Command(BaseCommand):
    help = "Add two versioned practical questions. Existing results are untouched."

    @transaction.atomic
    def handle(self, *args, **options):
        specs = json.loads(
            (
                Path(__file__).resolve().parents[2]
                / "data/practical_questions_20260928.json"
            ).read_text()
        )
        added = 0
        for spec in specs:
            row, created = Question.objects.get_or_create(
                slug=spec["slug"], defaults=spec
            )
            if not created and any(getattr(row, k) != v for k, v in spec.items()):
                raise CommandError(
                    "Existing question differs; refusing to change used inputs"
                )
            added += created
        self.stdout.write(
            f"Added {added} questions. The worker will discover missing work."
        )
