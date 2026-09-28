import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from jev_benchmark.models import BenchmarkModel, Question


class Command(BaseCommand):
    help = "Add the 2026-09-28 cohort and personal-advice question; no API calls."

    @transaction.atomic
    def handle(self, *args, **options):
        data = json.loads(
            (
                Path(__file__).resolve().parents[2] / "data/expansion_20260928.json"
            ).read_text()
        )
        for spec in data["models"]:
            model, created = BenchmarkModel.objects.get_or_create(
                openrouter_id=spec["openrouter_id"], defaults=spec
            )
            if not created and any(getattr(model, k) != v for k, v in spec.items()):
                raise CommandError("Existing model differs from expansion manifest")
        spec = data["question"]
        question, created = Question.objects.get_or_create(
            slug=spec["slug"], defaults=spec
        )
        if not created and any(getattr(question, k) != v for k, v in spec.items()):
            raise CommandError("Existing question differs from expansion manifest")
        self.stdout.write(
            "Expansion ready: 19 model entries and one personal question."
        )
