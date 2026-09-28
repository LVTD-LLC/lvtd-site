from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

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

    def handle(self, *args, **options):
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
            )
        except RuntimeError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            f"Generated: {stats['answers']}; judged: {stats['comparisons']}; "
            f"failed: {stats['failed']}"
        )
        if stats["failed"]:
            raise CommandError(
                "Some requests failed. Inspect results in admin, "
                "then rerun to retry missing work."
            )
