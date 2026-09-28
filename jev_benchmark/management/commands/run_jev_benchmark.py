import json
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from jev_benchmark.runner import pending_counts, run_benchmark


class Command(BaseCommand):
    help = "Resume missing answers and pairwise judgments (incurs API usage)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show remaining logical requests without writing or calling APIs.",
        )
        parser.add_argument(
            "--max-requests",
            type=int,
            help="Limit logical requests; excludes rate-limit retries.",
        )

        parser.add_argument(
            "--retry-max-tokens",
            type=int,
            help=(
                "Retry budget (1024-65536) for failed truncated answers only; "
                "never below the model default or previous recorded allowance."
            ),
        )

        parser.add_argument(
            "--workers", type=int, default=1, help="Concurrent HTTP requests (1-8)."
        )
        parser.add_argument(
            "--budget-file",
            help="JSON model-ID to token-budget mapping for first attempts only.",
        )

    def handle(self, *args, **options):
        started = time.monotonic()
        self.stdout.write(f"Started: {timezone.now().isoformat()}")
        budgets = None
        if options["budget_file"]:
            try:
                budgets = json.loads(Path(options["budget_file"]).read_text())
            except (OSError, ValueError) as error:
                raise CommandError("Cannot read initial budget JSON") from error
        pending = pending_counts()
        self.stdout.write(
            f"Missing answers: {pending['answers']}; "
            f"missing comparisons: {pending['comparisons']}"
        )
        if options["dry_run"]:
            return
        retry_budget = options["retry_max_tokens"]
        if retry_budget is not None and not 1024 <= retry_budget <= 65536:
            raise CommandError("--retry-max-tokens must be between 1024 and 65536")
        limit = options["max_requests"]
        if limit is not None and limit < 1:
            raise CommandError("--max-requests must be positive")
        if not pending["answers"] and not pending["comparisons"]:
            return
        if (
            not settings.OPENROUTER_JEVBENCHMARK_AI_API_KEY
            or not settings.TYPESAFE_API_KEY
        ):
            raise CommandError(
                "Configure OPENROUTER_JEVBENCHMARK_AI_API_KEY and TYPESAFE_API_KEY."
            )
        try:
            stats = run_benchmark(
                max_requests=limit,
                retry_max_tokens=retry_budget,
                report=self.stdout.write,
                workers=options["workers"],
                initial_budgets=budgets,
            )
        except (RuntimeError, ValueError) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            f"Generated: {stats['answers']}; judged: {stats['comparisons']}; "
            f"failed: {stats['failed']}"
        )
        self.stdout.write(
            f"Finished: {timezone.now().isoformat()}; "
            f"elapsed: {time.monotonic() - started:.2f}s"
        )
        if stats["failed"]:
            raise CommandError(
                "Some requests failed. Inspect results in admin, "
                "then rerun to retry missing work."
            )
