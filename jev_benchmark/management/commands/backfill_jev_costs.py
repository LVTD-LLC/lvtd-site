import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime

from jev_benchmark.costs import reported_cost
from jev_benchmark.models import Answer, Comparison, WorkAttempt


class Command(BaseCommand):
    help = (
        "Snapshot retained costs; optionally recover actual historical backup evidence."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--snapshot",
            action="append",
            default=[],
            help="Trusted Django dumpdata JSON from this same benchmark database.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count = 0
        for cls, field in ((Answer, "answer"), (Comparison, "comparison")):
            for row in cls.objects.filter(attempts__gt=0).iterator():
                _, created = WorkAttempt.objects.get_or_create(
                    **{field: row, "number": row.attempts},
                    defaults={
                        "source": "retained_response",
                        "status": row.status
                        if row.status != "pending"
                        else "uncertain",
                        "request": row.request,
                        "response": row.response,
                        "duration_ms": row.duration_ms,
                        "finished_at": row.completed_at or row.updated_at,
                        "cost_usd": reported_cost(row.response),
                        "error_kind": row.error_kind,
                    },
                )
                if row.status == "pending":
                    cls.objects.filter(pk=row.pk, status="pending").update(
                        status="failed",
                        error_kind="ambiguous",
                        error="Historical outcome unknown; review before retry.",
                    )
                count += created
        for path in options["snapshot"]:
            try:
                rows = json.loads(Path(path).read_text())
            except (OSError, ValueError):
                raise CommandError("Cannot read snapshot JSON") from None
            if not isinstance(rows, list):
                raise CommandError("Expected Django dumpdata list")
            for entry in rows:
                if entry.get("model") not in (
                    "jev_benchmark.answer",
                    "jev_benchmark.comparison",
                ):
                    continue
                cls, field, identities = (
                    (Answer, "answer", ("model_id", "question_id"))
                    if entry["model"] == "jev_benchmark.answer"
                    else (
                        Comparison,
                        "comparison",
                        ("left_id", "right_id", "question_id"),
                    )
                )
                data = entry["fields"]
                number = data.get("attempts", 0)
                if not number:
                    continue
                row = cls.objects.get(pk=entry["pk"])
                if number > row.attempts or any(
                    getattr(row, key) != data[key.removesuffix("_id")]
                    for key in identities
                ):
                    raise CommandError(
                        "Snapshot identity does not match current benchmark"
                    )
                response = data.get("response") or {}
                provider_id = response.get("id")
                if (
                    provider_id
                    and WorkAttempt.objects.filter(
                        **{field: row, "response__id": provider_id}
                    ).exists()
                ):
                    continue  # Same provider generation is never counted twice.
                attempt, created = WorkAttempt.objects.get_or_create(
                    **{field: row, "number": number},
                    defaults={
                        "source": "historical_snapshot",
                        "status": data["status"],
                        "request": data.get("request") or {},
                        "response": response,
                        "duration_ms": data.get("duration_ms"),
                        "finished_at": parse_datetime(
                            data.get("completed_at") or data["updated_at"]
                        ),
                        "cost_usd": reported_cost(response),
                    },
                )
                if not created and attempt.response != response:
                    raise CommandError(
                        "Conflicting attempt evidence; refusing overwrite"
                    )
                count += created
        self.stdout.write(
            f"Snapshotted {count} retained attempts. "
            "Costs absent from evidence remain unknown."
        )
