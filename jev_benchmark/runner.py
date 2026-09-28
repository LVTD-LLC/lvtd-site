import hashlib
import time
import uuid
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import contextmanager
from datetime import timedelta
from functools import partial
from itertools import combinations

from django.utils import timezone

from .clients import FatalProviderError, ProviderError, generate, judge
from .costs import reported_cost
from .models import (
    Answer,
    BenchmarkModel,
    Comparison,
    Question,
    RunnerLease,
    WorkAttempt,
)


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
    *,
    max_requests=None,
    retry_max_tokens=None,
    workers=1,
    initial_budgets=None,
    report=lambda message: None,
):
    if retry_max_tokens is not None and not 1024 <= retry_max_tokens <= 65536:
        raise ValueError("Retry output budget must be between 1024 and 65536.")
    if type(workers) is not int or not 1 <= workers <= 8:
        raise ValueError("Workers must be between 1 and 8.")
    if max_requests is not None and max_requests < 1:
        raise ValueError("Request limit must be positive.")
    initial_budgets = {} if initial_budgets is None else initial_budgets
    if not isinstance(initial_budgets, dict) or any(
        not isinstance(k, str) or type(v) is not int or not 1024 <= v <= 65536
        for k, v in initial_budgets.items()
    ):
        raise ValueError("Initial budgets must map model IDs to 1024-65536 tokens.")
    stats = {"answers": 0, "comparisons": 0, "failed": 0}
    models = list(BenchmarkModel.objects.filter(active=True).order_by("pk"))
    questions = list(Question.objects.filter(active=True))
    if set(initial_budgets) - {m.openrouter_id for m in models}:
        raise ValueError("Initial budget references an unknown or inactive model.")

    def answer_jobs():
        for question in questions:
            for model in models:
                answer, _ = Answer.objects.get_or_create(model=model, question=question)
                if answer.status == "complete":
                    continue
                options = {}
                if answer.attempts == 0 and model.openrouter_id in initial_budgets:
                    options["max_tokens"] = initial_budgets[model.openrouter_id]
                choices = answer.response.get("choices", [])
                truncated = (
                    answer.status == "failed"
                    and isinstance(choices, list)
                    and choices
                    and isinstance(choices[0], dict)
                    and choices[0].get("finish_reason") == "length"
                )
                if truncated and retry_max_tokens is not None:
                    default_budget = min(
                        model.max_tokens,
                        question.generation_max_tokens or model.max_tokens,
                    )
                    options["max_tokens"] = max(
                        default_budget,
                        retry_max_tokens,
                        answer.request.get("max_tokens", default_budget),
                    )
                    if question.generation_max_tokens:
                        options["allow_budget_override"] = True
                yield answer, partial(generate, model, question, **options)

    def comparison_jobs():
        for question in questions:
            answers = list(
                Answer.objects.filter(
                    question=question, model__in=models, status="complete"
                )
                .select_related("model")
                .order_by("pk")
            )
            for left, right in combinations(answers, 2):
                identity = (
                    f"{question.pk}:{left.model.openrouter_id}:"
                    f"{right.model.openrouter_id}"
                )
                match, _ = Comparison.objects.get_or_create(
                    question=question,
                    left=left,
                    right=right,
                    defaults={
                        "a_is_left": hashlib.sha256(identity.encode()).digest()[0] % 2
                        == 0
                    },
                )
                if match.status == "complete":
                    continue
                # Fully populate relation caches before handing HTTP work to a thread.
                match.left, match.right, match.question = left, right, question
                yield match, partial(judge, match)

    with runner_lease() as renew:
        sent = _run_stage(
            answer_jobs(), workers, max_requests, renew, stats, "answers", report
        )
        remaining = None if max_requests is None else max_requests - sent
        _run_stage(
            comparison_jobs(), workers, remaining, renew, stats, "comparisons", report
        )
    return stats


def _call(operation):
    start = time.monotonic()
    try:
        return operation(), None, int((time.monotonic() - start) * 1000)
    except Exception as error:
        return None, error, int((time.monotonic() - start) * 1000)


def _run_stage(jobs, workers, limit, renew, stats, kind, report):
    """Only HTTP/parsing runs in threads. All ORM access stays in the main thread.

    A bounded in-flight window prevents eager paid work. Heartbeat while waiting;
    on fatal error stop submitting, drain/save already-paid requests, then fail.
    """
    sent, pending, exhausted, fatal = 0, {}, False, None
    lease_active = True
    with ThreadPoolExecutor(max_workers=workers) as pool:
        while True:
            if lease_active:
                try:
                    renew()
                except Exception as error:
                    fatal, lease_active = error, False
            if fatal is None:
                try:
                    while (
                        not exhausted
                        and len(pending) < workers
                        and (limit is None or sent < limit)
                    ):
                        job = next(jobs, None)
                        if job is None:
                            exhausted = True
                            break
                        record, operation = job
                        record.attempts += 1
                        record.save(update_fields=["attempts", "updated_at"])
                        record._work_attempt = WorkAttempt.objects.create(
                            **{
                                "answer"
                                if isinstance(record, Answer)
                                else "comparison": record
                            },
                            number=record.attempts,
                        )
                        pending[pool.submit(_call, operation)] = record
                        sent += 1
                except Exception as error:
                    fatal = error
            if not pending:
                break
            done, _ = wait(pending, timeout=15, return_when=FIRST_COMPLETED)
            for future in done:
                record = pending.pop(future)
                result, error, duration = future.result()
                record.duration_ms = duration
                if error is not None:
                    if isinstance(error, ProviderError):
                        for field, value in error.audit.items():
                            setattr(record, field, value)
                        record.error = str(error)[:200]
                    else:
                        record.error = "Unexpected provider execution error"
                    record.status = "failed"
                    stats["failed"] += 1
                    if isinstance(error, FatalProviderError) or not isinstance(
                        error, ProviderError
                    ):
                        fatal = RuntimeError(record.error)
                else:
                    for field, value in result.items():
                        setattr(record, field, value)
                    record.status, record.error = "complete", ""
                    record.error_kind, record.next_attempt_at = "", None
                    record.completed_at = timezone.now()
                    stats[kind] += 1
                record.save()
                attempt = record._work_attempt
                attempt.status = record.status
                evidence = result or (
                    error.audit if isinstance(error, ProviderError) else {}
                )
                attempt.request = evidence.get("request", {})
                attempt.response = evidence.get("response", {})
                attempt.cost_usd = reported_cost(attempt.response)
                attempt.duration_ms = duration
                attempt.finished_at = timezone.now()
                attempt.error_kind = getattr(error, "kind", "") if error else ""
                attempt.save()
                report(
                    f"{timezone.now().isoformat()} {kind} #{record.pk}: "
                    f"{record.error or 'complete'} ({duration / 1000:.2f}s)"
                )
    if fatal is not None:
        raise fatal
    return sent
