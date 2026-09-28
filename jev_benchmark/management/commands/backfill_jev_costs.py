from django.core.management.base import BaseCommand

from jev_benchmark.costs import reported_cost
from jev_benchmark.models import Answer, Comparison, WorkAttempt


class Command(BaseCommand):
    help = "Snapshot retained costs. Earlier overwritten attempts remain unknown."

    def handle(self, *args, **options):
        count = 0
        for cls, field in ((Answer, "answer"), (Comparison, "comparison")):
            for row in cls.objects.filter(attempts__gt=0).iterator():
                _, created = WorkAttempt.objects.get_or_create(
                    **{field: row, "number": row.attempts},
                    defaults={
                        "source": "retained_response",
                        "status": row.status,
                        "request": row.request,
                        "response": row.response,
                        "duration_ms": row.duration_ms,
                        "finished_at": row.completed_at or row.updated_at,
                        "cost_usd": reported_cost(row.response),
                        "error_kind": row.error_kind,
                    },
                )
                count += created
        self.stdout.write(
            f"Snapshotted {count} retained attempts. "
            "Missing historical attempts remain unknown."
        )
