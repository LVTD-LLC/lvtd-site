import hashlib
import uuid
from contextlib import contextmanager
from datetime import timedelta
from functools import partial
from itertools import combinations

from django.utils import timezone

from .clients import FatalProviderError, ProviderError, generate, judge
from .models import Answer, BenchmarkModel, Comparison, Question, RunnerLease


@contextmanager
def runner_lease():
    token = str(uuid.uuid4())
    RunnerLease.objects.get_or_create(pk=1, defaults={"expires_at": timezone.now()})
    claimed = RunnerLease.objects.filter(pk=1, expires_at__lte=timezone.now()).update(
        owner=token, expires_at=timezone.now() + timedelta(minutes=20)
    )
    if not claimed:
        raise RuntimeError(
            "Benchmark already running; wait for the active runner or its lease expiry."
        )

    def renew():
        if not RunnerLease.objects.filter(
            pk=1, owner=token, expires_at__gt=timezone.now()
        ).update(expires_at=timezone.now() + timedelta(minutes=20)):
            raise RuntimeError(
                "Runner lease lost; stopped before additional paid work."
            )

    try:
        yield renew
    finally:
        RunnerLease.objects.filter(pk=1, owner=token).update(
            owner="", expires_at=timezone.now()
        )


def pending_counts():
    models = BenchmarkModel.objects.filter(active=True)
    questions = Question.objects.filter(active=True)
    model_count, question_count = models.count(), questions.count()
    answers = Answer.objects.filter(
        model__in=models, question__in=questions, status="complete"
    ).count()
    matches = Comparison.objects.filter(
        question__in=questions,
        left__model__in=models,
        right__model__in=models,
        status="complete",
    ).count()
    return {
        "answers": model_count * question_count - answers,
        "comparisons": question_count * model_count * (model_count - 1) // 2 - matches,
    }


def run_benchmark(
    *, max_requests=None, retry_max_tokens=None, report=lambda message: None
):
    if retry_max_tokens is not None and not 1024 <= retry_max_tokens <= 65536:
        raise ValueError("Retry output budget must be between 1024 and 65536.")
    stats = {"answers": 0, "comparisons": 0, "failed": 0}
    requests = 0
    with runner_lease() as renew:
        models = list(BenchmarkModel.objects.filter(active=True).order_by("pk"))
        questions = list(Question.objects.filter(active=True))
        for question in questions:
            for model in models:
                if max_requests is not None and requests >= max_requests:
                    return stats
                answer, _ = Answer.objects.get_or_create(model=model, question=question)
                if answer.status == "complete":
                    continue
                renew()
                requests += 1
                generation_options = {}
                previous_choices = answer.response.get("choices", [])
                truncated = (
                    answer.status == "failed"
                    and isinstance(previous_choices, list)
                    and previous_choices
                    and isinstance(previous_choices[0], dict)
                    and previous_choices[0].get("finish_reason") == "length"
                )
                if truncated and retry_max_tokens is not None:
                    generation_options["max_tokens"] = max(
                        model.max_tokens,
                        retry_max_tokens,
                        answer.request.get("max_tokens", model.max_tokens),
                    )
                _perform(
                    answer,
                    partial(generate, model, question, **generation_options),
                    stats,
                    "answers",
                    report,
                )
            answers = list(
                Answer.objects.filter(
                    question=question, model__in=models, status="complete"
                )
                .select_related("model")
                .order_by("pk")
            )
            for left, right in combinations(answers, 2):
                if max_requests is not None and requests >= max_requests:
                    return stats
                # Canonical storage is independent of presentation order.
                identity = (
                    f"{question.pk}:{left.model.openrouter_id}:"
                    f"{right.model.openrouter_id}"
                )
                a_is_left = hashlib.sha256(identity.encode()).digest()[0] % 2 == 0
                match, _ = Comparison.objects.get_or_create(
                    question=question,
                    left=left,
                    right=right,
                    defaults={"a_is_left": a_is_left},
                )
                if match.status == "complete":
                    continue
                renew()
                requests += 1
                _perform(match, partial(judge, match), stats, "comparisons", report)
    return stats


def _perform(record, operation, stats, kind, report):
    record.attempts += 1
    record.save(update_fields=["attempts", "updated_at"])
    try:
        result = operation()
    except ProviderError as error:
        for field, value in error.audit.items():
            setattr(record, field, value)
        record.status = "failed"
        record.error = str(error)[:200]
        record.save()
        stats["failed"] += 1
        report(f"{kind} #{record.pk}: {record.error}")
        if isinstance(error, FatalProviderError):
            raise RuntimeError(record.error) from error
        return
    for field, value in result.items():
        setattr(record, field, value)
    record.status = "complete"
    record.error = ""
    record.completed_at = timezone.now()
    record.save()
    stats[kind] += 1
    report(f"{kind} #{record.pk}: complete")
