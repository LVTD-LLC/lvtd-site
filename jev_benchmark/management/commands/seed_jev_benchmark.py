from django.core.management.base import BaseCommand
from django.db import transaction

from jev_benchmark.models import BenchmarkModel, Question
from jev_benchmark.seed import MODELS, QUESTIONS


class Command(BaseCommand):
    help = "Seed ten models and three questions; preserve edits and do not call APIs."

    @transaction.atomic
    def handle(self, *args, **options):
        for model_id, name, provider in MODELS:
            BenchmarkModel.objects.get_or_create(
                openrouter_id=model_id, defaults={"name": name, "provider": provider}
            )
        for question in QUESTIONS:
            defaults = {key: value for key, value in question.items() if key != "slug"}
            Question.objects.get_or_create(slug=question["slug"], defaults=defaults)
        self.stdout.write(
            "Initial benchmark entries available. Run run_jev_benchmark --dry-run next."
        )
