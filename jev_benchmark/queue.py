"""DB-backed missing-work queue. Only the coordinator thread touches Django ORM."""

import hashlib
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import timedelta
from decimal import Decimal
from functools import partial
from itertools import combinations

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .budget import CreditBudget
from .clients import FatalProviderError, ProviderError, generate, judge
from .costs import reported_cost
from .models import (
    Answer,
    BenchmarkModel,
    BudgetState,
    Comparison,
    Question,
    WorkAttempt,
)
from .runner import _call, runner_lease


def ensure_jobs(models, questions):
    existing_answers = set(
        Answer.objects.filter(model__in=models, question__in=questions).values_list(
            "model_id", "question_id"
        )
    )
    existing_pairs = set(
        Comparison.objects.filter(question__in=questions).values_list(
            "left_id", "right_id"
        )
    )
    ids = {m.pk: m.openrouter_id for m in models}
    Answer.objects.bulk_create(
        [
            Answer(model=m, question=q)
            for q in questions
            for m in models
            if (m.pk, q.pk) not in existing_answers
        ],
        ignore_conflicts=True,
    )
    jobs = []
    for q in questions:
        answers = list(
            Answer.objects.filter(
                question=q, model__in=models, status="complete"
            ).order_by("pk")
        )
        for left, right in combinations(answers, 2):
            if (left.pk, right.pk) in existing_pairs:
                continue
            # Same presentation identity as the original runner.
            identity = f"{q.pk}:{ids[left.model_id]}:{ids[right.model_id]}"
            jobs.append(
                Comparison(
                    question=q,
                    left=left,
                    right=right,
                    a_is_left=hashlib.sha256(identity.encode()).digest()[0] % 2 == 0,
                )
            )
    Comparison.objects.bulk_create(jobs, ignore_conflicts=True)


def ready(cls):
    return cls.objects.filter(
        Q(status="pending")
        | Q(status="failed", error_kind__in=["", "transient", "budget"])
    ).filter(Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=timezone.now()))


def recover_interrupted():
    # An expired lease does not prove that an upstream call was not billed.
    for attempt in WorkAttempt.objects.filter(status="started").select_related(
        "answer", "comparison"
    ):
        record = attempt.answer or attempt.comparison
        if record.status != "complete":
            record.status = "failed"
            record.error_kind = "ambiguous"
            record.error = (
                "Interrupted request: upstream outcome unknown. Review before retry."
            )
            record.save(update_fields=["status", "error_kind", "error", "updated_at"])
        attempt.status = "uncertain"
        attempt.error_kind = "ambiguous"
        attempt.finished_at = timezone.now()
        attempt.save(update_fields=["status", "error_kind", "finished_at"])


def run_queue(
    *, workers=8, max_requests=5000, report=print, stop_requested=lambda: False
):
    if not 1 <= workers <= 8 or max_requests < 1:
        raise ValueError("Use 1-8 workers and a positive request limit.")
    stats = {"answers": 0, "comparisons": 0, "failed": 0}
    with runner_lease() as renew:
        recover_interrupted()
        models = list(BenchmarkModel.objects.filter(active=True))
        questions = list(Question.objects.filter(active=True))
        ensure_jobs(models, questions)
        budget = None
        generation_paused = Answer.objects.filter(
            error_kind="auth", status="failed"
        ).exists()
        judging_paused = Comparison.objects.filter(
            error_kind="auth", status="failed"
        ).exists()
        if ready(Answer).filter(model__in=models, question__in=questions).exists():
            try:
                budget = CreditBudget()
            except ProviderError as error:
                generation_paused = True
                BudgetState.objects.update_or_create(
                    pk=1, defaults={"alert": str(error)}
                )
                report(str(error))
        reservation_wait = False
        submitted = 0
        pending = {}
        fatal = None
        lease_active = True
        with ThreadPoolExecutor(max_workers=workers) as pool:
            while True:
                if lease_active:
                    try:
                        renew()
                    except RuntimeError as error:
                        fatal = error
                        lease_active = False
                while (
                    fatal is None
                    and not stop_requested()
                    and len(pending) < workers
                    and submitted < max_requests
                ):
                    answer_ids = [
                        r.pk for r, _, _ in pending.values() if isinstance(r, Answer)
                    ]
                    comparison_ids = [
                        r.pk
                        for r, _, _ in pending.values()
                        if isinstance(r, Comparison)
                    ]
                    record = (
                        ready(Comparison)
                        .filter(
                            question__in=questions,
                            left__model__in=models,
                            right__model__in=models,
                        )
                        .exclude(pk__in=comparison_ids)
                        .select_related("left__model", "right__model", "question")
                        .order_by("pk")
                        .first()
                    )
                    if judging_paused:
                        record = None
                    estimate = Decimal(0)
                    if record is not None:
                        operation = partial(judge, record)
                    elif not generation_paused:
                        reserved = sum(
                            e for r, _, e in pending.values() if isinstance(r, Answer)
                        )
                        record = None
                        for candidate in (
                            ready(Answer)
                            .filter(model__in=models, question__in=questions)
                            .exclude(pk__in=answer_ids)
                            .select_related("model", "question")
                            .order_by("pk")
                        ):
                            tokens = candidate.request.get(
                                "max_tokens", candidate.model.max_tokens
                            )
                            if candidate.question.generation_max_tokens:
                                tokens = min(
                                    tokens, candidate.question.generation_max_tokens
                                )
                            cost = (
                                budget.estimate(
                                    candidate.model, candidate.question, tokens
                                )
                                if budget
                                else Decimal(0)
                            )
                            if budget and not budget.fits(cost, reserved):
                                reservation_wait = True
                                continue
                            record = candidate
                            estimate = cost
                            operation = partial(
                                generate,
                                record.model,
                                record.question,
                                max_tokens=tokens,
                            )
                            break
                    if record is None:
                        break
                    with transaction.atomic():
                        record.attempts += 1
                        record.save(update_fields=["attempts", "updated_at"])
                        attempt = WorkAttempt.objects.create(
                            **{
                                "answer"
                                if isinstance(record, Answer)
                                else "comparison": record
                            },
                            number=record.attempts,
                        )
                    pending[pool.submit(_call, operation)] = (record, attempt, estimate)
                    submitted += 1
                if not pending:
                    break
                done, _ = wait(pending, timeout=15, return_when=FIRST_COMPLETED)
                changed_answers = False
                for future in done:
                    record, attempt, estimate = pending.pop(future)
                    result, error, duration = future.result()
                    kind = "answers" if isinstance(record, Answer) else "comparisons"
                    record.duration_ms = duration
                    audit = result or (
                        error.audit if isinstance(error, ProviderError) else {}
                    )
                    # Clear stale per-result audit on a failed new attempt; its old
                    # snapshot lives in WorkAttempt (backfill before enabling queue).
                    for field in ("request", "response"):
                        setattr(record, field, audit.get(field, {}))
                    attempt.request = record.request
                    attempt.response = record.response
                    attempt.cost_usd = reported_cost(record.response)
                    attempt.duration_ms = duration
                    attempt.finished_at = timezone.now()
                    if error:
                        record.status = "failed"
                        record.retry_count += 1
                        record.error_kind = (
                            error.kind
                            if isinstance(error, ProviderError)
                            else "invalid"
                        )
                        record.error = (
                            str(error)[:200]
                            if isinstance(error, ProviderError)
                            else "Unexpected provider error"
                        )
                        record.next_attempt_at = None
                        if record.error_kind in ("transient", "budget"):
                            if record.retry_count >= 3:
                                record.error_kind = "exhausted"
                            else:
                                record.next_attempt_at = timezone.now() + timedelta(
                                    seconds=max(
                                        error.retry_after,
                                        60 * 2 ** (record.retry_count - 1),
                                    )
                                )
                        if kind == "answers" and record.error_kind == "blocked":
                            Answer.objects.filter(model=record.model).exclude(
                                status="complete"
                            ).exclude(pk=record.pk).update(
                                status="failed",
                                error_kind="blocked",
                                error=record.error,
                            )
                        if kind == "answers" and getattr(error, "kind", "") == "budget":
                            generation_paused = True
                        if isinstance(error, FatalProviderError) or not isinstance(
                            error, ProviderError
                        ):
                            fatal = RuntimeError(record.error)
                        attempt.status = "failed"
                        attempt.error_kind = record.error_kind
                        stats["failed"] += 1
                    else:
                        for field, value in result.items():
                            setattr(record, field, value)
                        record.status = "complete"
                        record.error = ""
                        record.error_kind = ""
                        record.next_attempt_at = None
                        record.completed_at = timezone.now()
                        attempt.status = "complete"
                        stats[kind] += 1
                        changed_answers |= kind == "answers"
                    with transaction.atomic():
                        record.save()
                        attempt.save()
                    if budget and kind == "answers":
                        budget.settle(attempt.cost_usd, estimate)
                    report(
                        f"{timezone.now().isoformat()} {kind} #{record.pk}: "
                        f"{record.error or 'complete'} ({duration / 1000:.2f}s)"
                    )
                if changed_answers:
                    ensure_jobs(models, questions)
        if fatal:
            raise fatal
        if (
            budget
            and reservation_wait
            and ready(Answer).filter(model__in=models, question__in=questions).exists()
        ):
            message = "Generation waiting for affordable credit reservation."
            if budget.usage >= budget.limit or budget.threshold_blocked:
                message = (
                    f"SPEND ALERT: OpenRouter usage ${budget.usage:.2f}; "
                    "next reservation approaches alert threshold; generation paused."
                )
            BudgetState.objects.update_or_create(pk=1, defaults={"alert": message})
            report(message)
    return stats
